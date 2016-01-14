#!../../virtual-env/bin/python
# daytimeJobs.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# This script is a very generic file processor. It looks for files in
# directories with given extensions, works out the time associated with each
# file from its filename, and performs predefined shell-commands on them if
# they are newer than a given high-water mark. The list of tasks to be
# performed is defined in <mod_daytimejobs>.

import os, time, sys, glob, datetime, operator
import math

import mod_log
from mod_log import log_txt, get_utc
import mod_settings
import mod_daytimejobs
import mod_astro
import orientationCalc
import exportData
import daytimeJobsClean

import meteorpi_db

import dbImport

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

# Cleaning up any output files which are ahead of high water marks
log_txt("Cleaning up any output files which are ahead of high water marks")
daytimeJobsClean.day_time_jobs_clean(db)

# Read our high water mark, and only analyse more recently-created data
cwd = os.getcwd()
os.chdir(mod_settings.settings['dataPath'])


def run_job_group(job_group):
    if (len(job_group) < 1):
        return

    # Run shell commands associated with this group of jobs
    shell_cmds = [" ".join((job['cmd'] % job['params']).split()) for job in job_group]
    for cmd in shell_cmds:
        log_txt("Running command: %s" % cmd)
    if (len(shell_cmds) == 1):
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
            metadata.update(mod_hwm.fileToDB("%stxt" % stub))
            mod_hwm.DBtoFile("%stxt" % stub, metadata)


# We raise this exception if we pass the time when we've been told we need to hand execution back
class TimeOut(Exception):
    pass


job_counter = 0

try:
    for task_group in mod_daytimejobs.dayTimeTasks:
        [hwm_output, n_max, task_list] = task_group
        if hwm_output not in highWaterMarks:
            highWaterMarks[hwm_output] = 0
        log_txt("Working on task group <%s>" % hwm_output)
        hwm_margin = ((mod_settings.settings['videoMaxRecordTime'] - 5) if hwm_output == "rawvideo" else 0.1)
        job_list = []
        for task in task_list:
            [in_dir, out_dirs, in_ext, out_ext, cmd] = task

            # Operate on any input files which are newer than HWM
            for dir_name, subdir_list, file_list in os.walk(in_dir):
                for f in file_list:
                    if quit_time and (get_utc() > quit_time):
                        raise TimeOut
                    input_file = os.path.join(dir_name, f)

                    # File must have correct extension and non-zero size
                    if (f.endswith(".%s" % in_ext) and (os.path.getsize(input_file) > 0)):
                        utc = mod_hwm.filenameToUTC(f)
                        if (utc < 0): continue
                        if (utc > highWaterMarks[hwm_output]):

                            job_counter += 1
                            mask_file = "/tmp/triggermask_%d_%d.txt" % (os.getpid(), job_counter)

                            # Fix to stop floating point jitter creating lots of files with timestamps like 23:59:59
                            utc += 0.1

                            # Make dictionary of information about this job
                            params = {'binary_path': mod_settings.settings['binaryPath'],
                                      'input': input_file,
                                      'outdir': out_dirs[0],
                                      'filename': f[:-(len(in_ext) + 1)],
                                      'inExt': in_ext,
                                      'outExt': out_ext,
                                      'date': mod_log.fetch_day_name_from_filename(f),
                                      'tstamp': utc,
                                      'cameraId': CAMERA_ID,
                                      'pid': pid,
                                      'triggermask': mask_file,
                                      'opm': ('_openmax' if I_AM_A_RPI else ''),

                                      # Produce non-lens-corrected images once every 2 mins
                                      'produceFilesWithoutLC': int(math.floor(utc % 120) < 24),
                                      }
                            params['filename_out'] = "%(outdir)s/%(date)s/%(filename)s" % params
                            params['metadata'] = mod_hwm.fileToDB("%s.txt" % os.path.join(dir_name, params['filename']))
                            params.update(params['metadata'])
                            if 'fps' not in params:
                                params['fps'] = mod_hardwareProps.fetchSensorData(db, hw_handle, params['cameraId'],
                                                                                  utc).fps

                            # Read barrel-correction parameters
                            lensData = mod_hardwareProps.fetchLensData(db, hw_handle, params['cameraId'], utc)
                            params['barrel_a'] = lensData.barrel_a
                            params['barrel_b'] = lensData.barrel_b
                            params['barrel_c'] = lensData.barrel_c

                            # Fetch the status of the camera which made this observation
                            cameraStatus = db.get_camera_status(camera_id=params['cameraId'], time=utc)

                            # Create clipping region mask file
                            open(mask_file, "w").write(
                                    "\n\n".join(
                                            ["\n".join(["%(x)d %(y)d" % p for p in pointList])
                                             for pointList in cameraStatus.regions]
                                    )
                            )

                            # Insert metadata about position of Sun
                            sunPos = mod_astro.sun_pos(utc)
                            sunAltAz = mod_astro.alt_az(sunPos[0], sunPos[1], utc, cameraStatus.location.latitude,
                                                        cameraStatus.location.longitude)
                            params['metadata']['sunRA'] = sunPos[0]
                            params['metadata']['sunDecl'] = sunPos[1]
                            params['metadata']['sunAlt'] = sunAltAz[0]
                            params['metadata']['sunAz'] = sunAltAz[1]

                            # Select some images to be shown in the highlights-only view
                            params['metadata']['highlight'] = int((math.floor(utc % 600) < 24) or ('outExt' == 'mp4'))

                            for out_dir in out_dirs:
                                os.system("mkdir -p %s" % (os.path.join(out_dir, params['date'])))
                            job_list.append({'utc': utc, 'cmd': cmd, 'params': params})

        # Sort jobs in order of timestamp
        job_list.sort(key=operator.itemgetter('utc'))

        # Reset database high water marks
        obstories_seen = []
        for job in job_list:
            cameraId = job['params']['cameraId']
            if cameraId not in obstories_seen:
                db.set_high_water_mark(datetime.datetime.fromtimestamp(job['utc']), cameraId)
                obstories_seen.append(cameraId)

        # Now do jobs in order, raising local high level water mark as we do each job
        jobGrp = []
        jobListLen = len(job_list)
        if jobListLen:
            for i in range(jobListLen):
                job = job_list[i]
                if quit_time and (get_utc() > quit_time): raise TimeOut
                jobGrp.append(job)
                if len(jobGrp) >= n_max:
                    run_job_group(jobGrp)
                    jobGrp = []

                    # Set HWM so that next job is marked as not yet done (it may have the same timestamp as present job)
                    if (i < jobListLen - 1):
                        highWaterMarks[hwm_output] = job_list[i + 1]['utc'] - 0.1

                    # Set HWM so it's just past the job we've just done (0.1 sec)
                    else:
                        highWaterMarks[hwm_output] = job['utc'] + hwm_margin

            run_job_group(jobGrp)
            highWaterMarks[hwm_output] = job_list[jobListLen - 1]['utc'] + hwm_margin
            log_txt("Completed %d jobs" % len(job_list))
            os.system("rm -f /tmp/triggermask_%d_*" % (os.getpid()))  # Delete trigger masks that we've finished with

except TimeOut:
    log_txt("Interrupting processing as we've run out of time")

# Import events into database (unless we need to start observing again within next five minutes)
os.chdir(cwd)
if (not quit_time) or (quit_time - get_utc() > 300):
    log_txt("Importing events into firebird db")
    hwm_new = dbImport.database_import()

# Figure out orientation of camera -- this may take 5 hours!
try:
    if (not quit_time) or (quit_time - get_utc() > 3600 * 5):
        log_txt("Trying to determine orientation of camera")
        orientationCalc.orientationCalc(CAMERA_ID, get_utc(), quit_time)
except:
    log_txt("Unexpected error while determining camera orientation")

# Update database hwm
for cameraId, utc in hwm_new.iteritems():
    log_txt("Updating high water mark of camera <%s> to UTC %d (%s)" % (cameraId, utc, UTC2datetime(utc)))
    db.set_high_water_mark(utc, cameraId)

# Export data to remote server(s)
try:
    if (not quit_time) or (quit_time - get_utc() > 3600):
        log_txt("Exporting data to remote servers")
        exportData.export_data(get_utc(), quit_time)
except:
    log_txt("Unexpected error while trying to export data")

# Clean up temporary files
os.system("rm -Rf /tmp/tmp.* /tmp/dcf21_orientationCalc_*")

# This deletes all data not imported into the database.
# Should be uncommented on production systems where unattended operation needed.
os.system("rm -Rf %s/t*" % (mod_settings.settings['dataPath']))

# Twiddle our thumbs
if quit_time:
    time_left = quit_time - get_utc()
    if (time_left > 0):
        log_txt("Finished daytimeJobs. Now twiddling our thumbs for %d seconds." % time_left)
        time.sleep(time_left)
    log_txt("Finished daytimeJobs and also finished twiddling thumbs.")
