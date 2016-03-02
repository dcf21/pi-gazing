#!../../virtual-env/bin/python
# daytimeJobs.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# This script is a very generic file processor. It looks for files in
# directories with given extensions, works out the time associated with each
# file from its filename, and performs predefined shell-commands on them if
# they are newer than a given high-water mark. The list of tasks to be
# performed is defined in <mod_daytimejobs>.

import glob
import math
import operator
import os
import sys
import time
import json
import traceback

import meteorpi_db

import daytimeJobsClean
import dbImport
import exportData
import installation_info
import mod_astro
import mod_daytimejobs
import mod_log
import mod_settings
import orientationCalc
from mod_log import log_txt, get_utc

pid = os.getpid()
db = meteorpi_db.MeteorDatabase(mod_settings.settings['dbFilestore'])

# User should supply unix time on commandline at which we are to stop work
if len(sys.argv) != 3:
    print "Need to call daytimeJobs.py with clock offset, and an end time to tell it when it needs to quit by."
    sys.exit(1)

utc_offset = float(sys.argv[1])
quit_time = float(sys.argv[2])
mod_log.set_utc_offset(utc_offset)

log_txt("Running daytimeJobs. Need to quit at %s." % mod_astro.time_print(quit_time))

# Clean up any output files which are ahead of high water marks
log_txt("Cleaning up any output files which are ahead of high water marks")
daytimeJobsClean.day_time_jobs_clean(db)

# Change into the directory where data files are kept
cwd = os.getcwd()
os.chdir(mod_settings.settings['dataPath'])


# Run a list of shell commands in parallel
# Pass a list of job descriptor dictionaries, each having a cmd template, and a dictionary of params to substitute
def run_job_group(job_group):
    if len(job_group) < 1:
        return

    # Run shell commands associated with this group of jobs
    shell_cmds = [" ".join((job['cmd'] % job['params']).split()) for job in job_group]
    for cmd in shell_cmds:
        print "Running command: %s" % cmd
    if len(shell_cmds) == 1:
        cmd = shell_cmds[0]
    else:
        cmd = " & ".join(shell_cmds) + " & wait"
    os.system(cmd)

    # Cascade metadata from input files to output files
    for job in job_group:
        m = job['params']  # Dictionary of metadata
        products = glob.glob("%(filename_out)s*%(outExt)s" % m)
        for product in products:
            stub = product[:-len(m['outExt'])]
            metadata = m['metadata']  # Metadata that was associated with input file
            metadata.update(mod_daytimejobs.file_to_dict(in_filename="%stxt" % stub))
            mod_daytimejobs.dict_to_file(out_filename="%stxt" % stub, in_dict=metadata)


# Create a custom exception which we raise if we pass the time when we've been told we need to hand execution back
class TimeOut(Exception):
    pass


# Count the number of jobs we have done
job_counter = 0

# Look up old high-water mark for each task group, which may be different for different observatories
all_obstories_seen = []
obstory_list = db.get_obstory_ids()
obstory_infos = {}
hwm_old = {}
hwm_new = {}
for obstory_id in obstory_list:
    obstory_infos[obstory_id] = db.get_obstory_from_id(obstory_id)
    hwm_old[obstory_id] = {}
    hwm_new[obstory_id] = {}

try:
    # Loop over task groups, e.g. PNG encoding timelapse images, or encoding trigger videos to MP4
    for task_group in mod_daytimejobs.dayTimeTasks:
        [hwm_output, n_max, task_list] = task_group
        log_txt("Working on task group <%s>" % hwm_output)

        # Look up old high-water marks for each observatory
        for obstory_id in obstory_list:
            hwm_old[obstory_id][hwm_output] = db.get_high_water_mark(obstory_name=obstory_infos[obstory_id]['name'],
                                                                     mark_type=hwm_output)
            if hwm_old[obstory_id][hwm_output] is None:
                hwm_old[obstory_id][hwm_output] = 0
            hwm_new[obstory_id][hwm_output] = hwm_old[obstory_id][hwm_output]

        # Some tasks produce output files with different timestamps to the input file. Specifically, non-live
        # observing produces output over the entire length of a video. hwm_margin is the maximum size of this span
        hwm_margin = ((mod_settings.settings['videoMaxRecordTime'] - 5) if hwm_output == "rawvideo" else 0.1)
        job_list = []

        # Loop over each of the input file search patterns that this task group is to be applied to
        for task in task_list:
            [in_dir, out_dirs, in_ext, out_ext, cmd] = task

            # Loop recursively over all files in the input directory
            for dir_name, subdir_list, file_list in os.walk(in_dir):
                for f in file_list:
                    if quit_time and (get_utc() > quit_time):
                        raise TimeOut
                    input_file = os.path.join(dir_name, f)

                    # Input files must have correct extension and non-zero size to be processed
                    if f.endswith(".%s" % in_ext) and (os.path.getsize(input_file) > 0):

                        # Extract observation time from image filename. If this fails, reject the file.
                        utc = mod_log.filename_to_utc(f)
                        if utc < 0:
                            continue

                        # Add this job to our list of things to do
                        job_counter += 1
                        mask_file = "/tmp/triggermask_%d_%d.txt" % (os.getpid(), job_counter)

                        # Fix to stop floating point jitter creating lots of files with timestamps like 23:59:59
                        utc += 0.1

                        # Job will be run as a shell command taken from mod_daytimejobs. Each shell command
                        # template has variables substituted into it. These are some default values, many of which
                        # will be overwritten with metadata associated with the input file.
                        params = {'binary_path': mod_settings.settings['binaryPath'],
                                  'input': input_file,
                                  'outdir': out_dirs[0],
                                  'filename': f[:-(len(in_ext) + 1)],
                                  'inExt': in_ext,
                                  'outExt': out_ext,
                                  'date': mod_log.fetch_day_name_from_filename(f),
                                  'tstamp': utc,
                                  'obstoryId': installation_info.local_conf['observatoryId'],
                                  'pid': pid,
                                  'triggermask': mask_file,
                                  'opm': ('_openmax' if mod_settings.settings['i_am_a_rpi'] else ''),

                                  # Produce non-lens-corrected images once every 2 mins
                                  'produceFilesWithoutLC': int(math.floor(utc % 120) < 24),
                                  }
                        params['filename_out'] = "%(outdir)s/%(date)s/%(filename)s" % params

                        # Overwrite the default parameters above with those output from the videoAnalysis C code
                        # Store a copy of the input file's metadata as params['params']
                        params['metadata'] = mod_daytimejobs.file_to_dict(
                                in_filename="%s.txt" % os.path.join(dir_name, params['filename']))
                        params.update(params['metadata'])

                        # Fetch the status of the observatory which made this observation
                        obstory_id = params['obstoryId']
                        if obstory_id not in obstory_infos:
                            print "Error: No observatory status set for id <%s>" % obstory_id
                            continue
                        obstory_info = obstory_infos[obstory_id]
                        obstory_name = obstory_info['name']
                        obstory_status = db.get_obstory_status(obstory_name=obstory_name, time=utc)

                        if 'latitude' not in obstory_status:
                            obstory_status['latitude'] = installation_info.local_conf['latitude']
                        if 'longitude' not in obstory_status:
                            obstory_status['longitude'] = installation_info.local_conf['longitude']

                        if 'fps' not in params:
                            params['fps'] = obstory_status["sensor_fps"]

                        # Only operate on input files which are newer than HWM
                        if utc < hwm_old[obstory_id][hwm_output]:
                            continue

                        # Read barrel-correction parameters
                        params['barrel_a'] = obstory_status["lens_barrel_a"]
                        params['barrel_b'] = obstory_status["lens_barrel_b"]
                        params['barrel_c'] = obstory_status["lens_barrel_c"]

                        # Create clipping region mask file
                        open(mask_file, "w").write(
                                "\n\n".join(
                                        ["\n".join([("%d %d" % p) for p in pointList])
                                         for pointList in json.loads(obstory_status['clippingRegion'])]
                                )
                        )

                        # Calculate metadata about the position of Sun at the time of observation
                        sunPos = mod_astro.sun_pos(utc)
                        sunAltAz = mod_astro.alt_az(sunPos[0], sunPos[1], utc,
                                                    obstory_status['latitude'], obstory_status['longitude'])
                        params['metadata']['sunRA'] = sunPos[0]
                        params['metadata']['sunDecl'] = sunPos[1]
                        params['metadata']['sunAlt'] = sunAltAz[0]
                        params['metadata']['sunAz'] = sunAltAz[1]

                        # Apply a metadata tag 'highlight' to a few images, which will get shown by the
                        # 'show fewer results' option in the web interface. Select roughly one image every
                        # ten minutes
                        params['metadata']['highlight'] = int((math.floor(utc % 600) < 24) or ('outExt' == 'mp4'))

                        # Make sure that output directory exists
                        for out_dir in out_dirs:
                            os.system("mkdir -p %s" % (os.path.join(out_dir, params['date'])))

                        # Add job to list, but don't do it yet as we want to do jobs in time order
                        # Do jobs in time order means we can stop part way and be able to record where we
                        # got up to.
                        job_list.append({'utc': utc, 'cmd': cmd, 'params': params})

        # Sort jobs in order of timestamp
        job_list.sort(key=operator.itemgetter('utc'))

        # Reset high water marks in the database to just before the first job we need to do for each observatory
        # Delete any output products that are newer than that time
        obstories_seen = []
        for job in job_list:
            obstory_id = job['params']['obstoryId']

            # Make a complete list of all of the observatories we have seen data from
            if obstory_id not in all_obstories_seen:
                all_obstories_seen.append(obstory_id)

            # If this is the first time we've seen this observatory within this job group, delete any newer data
            if obstory_id not in obstories_seen:
                if obstory_id not in obstory_infos:
                    print "Error: No observatory status set for id <%s>" % obstory_id
                    continue
                obstory_info = obstory_infos[obstory_id]
                obstory_name = obstory_info['name']
                db.set_high_water_mark(mark_type='observing', time=job['utc'], obstory_name=obstory_name)
                db.clear_database(obstory_names=[obstory_name], tmin=job['utc'] - 0.1, tmax=job['utc'] + 3600 * 12)
                obstories_seen.append(obstory_id)

        # Now do jobs in order, raising local high level water mark as we do each job
        job_group = []
        job_list_len = len(job_list)
        if job_list_len:
            for i in range(job_list_len):
                job = job_list[i]
                if quit_time and (get_utc() > quit_time):
                    raise TimeOut
                job_group.append(job)
                if len(job_group) >= n_max:
                    run_job_group(job_group)
                    job_group = []

                    # Set HWM so that next job is marked as not yet done (it may have the same timestamp as present job)
                    for job_done in job_group:
                        obstory_id = job_done['params']['obstoryId']
                        hwm_new[obstory_id][hwm_output] = job_list[i]['utc'] - 0.1

            run_job_group(job_group)
            for obstory_id in obstories_seen:
                hwm_new[obstory_id][hwm_output] = job_list[job_list_len - 1]['utc'] + hwm_margin
            log_txt("Completed %d jobs" % len(job_list))

            # Delete trigger masks that we've finished with
            os.system("rm -f /tmp/triggermask_%d_*" % (os.getpid()))

except TimeOut:
    log_txt("Interrupting processing as we've run out of time")

# Commit new high-water marks to the database
for obstory_id in all_obstories_seen:
    if obstory_id in hwm_new:
        for hwm_output in hwm_new[obstory_id].keys():
            obstory_info = obstory_infos[obstory_id]
            db.set_high_water_mark(mark_type=hwm_output,
                                   obstory_name=obstory_info['name'],
                                   time=hwm_new[obstory_id][hwm_output]
                                   )

# Commit changes to database
db.commit()

# Import events into database (unless we need to start observing again within next five minutes)
os.chdir(cwd)
try:
    if (not quit_time) or (quit_time - get_utc() > 300):
        log_txt("Importing events into database")
        dbImport.database_import(db)
        log_txt("Finished importing events into database")
except:
    log_txt("Unexpected error while trying to import data into database")
    traceback.print_exc()

# Export data to remote server(s)
try:
    if (not quit_time) or (quit_time - get_utc() > 3600):
        log_txt("Exporting data to remote servers")
        exportData.export_data(db=db,
                               utc_now=get_utc(),
                               utc_must_stop=quit_time)
except:
    log_txt("Unexpected error while trying to export data")
    traceback.print_exc()

# Figure out orientation of camera -- this may take 5 hours!
try:
    for obstory_id in all_obstories_seen:
        if (not quit_time) or (quit_time - get_utc() > 3600 * 5):
            log_txt("Trying to determine orientation of camera <%s>" % obstory_id)
            obstory_name = obstory_infos[obstory_id]['name']
            orientationCalc.orientation_calc(obstory_name=obstory_name,
                                             utc_to_study=get_utc(),
                                             utc_now=get_utc(),
                                             utc_must_stop=quit_time)
except:
    log_txt("Unexpected error while determining camera orientation")
    traceback.print_exc()

# Clean up temporary files
os.system("rm -Rf /tmp/tmp.* /tmp/dcf21_orientationCalc_*")

# This deletes all data not imported into the database.
# Should be uncommented on production systems where unattended operation needed.
os.system("rm -Rf %s/t*" % (mod_settings.settings['dataPath']))

# Twiddle our thumbs
if quit_time:
    time_left = quit_time - get_utc()
    if time_left > 0:
        log_txt("Finished daytimeJobs. Now twiddling our thumbs for %d seconds." % time_left)
        time.sleep(time_left)
    log_txt("Finished daytimeJobs and also finished twiddling thumbs.")
