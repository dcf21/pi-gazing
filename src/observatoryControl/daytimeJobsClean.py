#!../../virtual-env/bin/python
# daytimeJobsClean.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import os
import sys
import time

import meteorpi_db

import mod_log
import mod_settings
import mod_daytimejobs
from mod_log import log_txt


def day_time_jobs_clean(db):
    log_txt("Running daytimeJobsClean")
    cwd = os.getcwd()
    os.chdir(mod_settings.settings['dataPath'])

    # Clean up any file products which are newer than high water mark
    # Work on each task in turn
    for taskGroup in mod_daytimejobs.dayTimeTasks:
        hwm_output = taskGroup[0]
        task_list = taskGroup[2]
        if db.get_high_water_mark(mark_type=hwm_output) is None:
            db.set_high_water_mark(mark_type=hwm_output, time=0)
        high_water = db.get_high_water_mark(mark_type=hwm_output)
        for task in task_list:
            out_dirs = task[1]

            # Remove any output which is newer than HWM
            for out_dir in out_dirs:
                for dir_name, subdir_list, file_list in os.walk(out_dir):
                    for f in file_list:
                        utc = mod_log.filename_to_utc(f)
                        if utc < 0:
                            continue
                        if utc > high_water:
                            os.system("rm -f %s" % os.path.join(dir_name, f))

    os.chdir(cwd)
    log_txt("Finished daytimeJobsClean")


# If we're called as a script, run the method exportData()
if __name__ == "__main__":
    utc_now = time.time()
    if len(sys.argv) > 1:
        utc_now = float(sys.argv[1])
    mod_log.set_utc_offset(utc_now - time.time())
    dbh = meteorpi_db.MeteorDatabase(mod_settings.settings['dbFilestore'])
    day_time_jobs_clean(dbh)
