#!../../virtual-env/bin/python
# deleteData.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# Deletes all of the observations and files recorded by a particular observatory between two times.

# Commandline syntax:
# ./deleteData.py t_min t_max observatory

import os
import sys
import time

import meteorpi_db
import meteorpi_model as mp

import mod_settings
import installation_info
import mod_astro

pid = os.getpid()

utc_min = time.time() - 3600 * 24
utc_max = time.time()
observatory = installation_info.local_conf['observatoryName']

if len(sys.argv) > 1:
    utc_min = float(sys.argv[1])
if len(sys.argv) > 2:
    utc_max = float(sys.argv[2])
if len(sys.argv) > 3:
    observatory = sys.argv[3]

if utc_max == 0:
    utc_max = time.time()

print "# ./deleteData.py %f %f \"%s\"\n" % (utc_min, utc_max, observatory)

db = meteorpi_db.MeteorDatabase(mod_settings.settings['dbFilestore'])

s = db.get_obstory_status(obstory_name=observatory)
if not s:
    print "Unknown observatory <%s>.\nRun ./listObservatories.py to see a list of available options." % observatory
    sys.exit(0)

search = mp.FileRecordSearch(obstory_ids=[observatory],
                             time_min=utc_min,
                             time_max=utc_max,
                             limit=1000000)
files = db.search_files(search)
files = [i for i in files['files']]
files.sort(key=lambda x: x.file_time)

search = mp.ObservationSearch(obstory_ids=[observatory],
                              time_min=utc_min,
                              time_max=utc_max,
                              limit=1000000)
observations = db.search_observations(search)
observations = observations['obs']
observations.sort(key=lambda x: x.obs_time)

print "Observatory <%s>" % observatory
print "  * %6d matching files in time range %s --> %s" % (len(files),
                                                          mod_astro.time_print(utc_min),
                                                          mod_astro.time_print(utc_max))
print "  * %6d matching observations in time range" % (len(observations))

confirmation = raw_input('Delete these files? (Y/N) ')
if confirmation not in 'Yy':
    sys.exit(0)

db.clear_database(tmin=utc_min, tmax=utc_max, obstory_names=observatory)

# Commit changes to database
db.commit()
