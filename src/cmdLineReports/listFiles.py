#!../../virtual-env/bin/python
# listFiles.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import time
import sys

import mod_astro
import mod_settings

import meteorpi_model as mp
import meteorpi_db

db = meteorpi_db.MeteorDatabase(mod_settings.settings['dbFilestore'])

utc_min = 0
utc_max = time.time()

argc = len(sys.argv)
if argc > 1:
    utc_min = float(sys.argv[1])
if argc > 2:
    utc_max = float(sys.argv[2])

print "# ./listFiles.py %s %s\n" % (utc_min, utc_max)

obstory_list = db.get_obstory_names()
for obstory_name in obstory_list:
    title = "Observatory <%s>" % obstory_name
    print "\n\n%s\n%s" % (title, "-" * len(title))

    search = mp.FileRecordSearch(obstory_ids=[obstory_name], time_min=utc_max, time_max=utc_min)
    files = db.search_files(search)
    files = files['files']
    files.sort(key=lambda x: x.file_time)
    print "  * %d matching files in time range %s --> %s" % (len(files),
                                                             mod_astro.time_print(utc_min),
                                                             mod_astro.time_print(utc_max))
    for fileObj in files:
        print "  * %s -- %s" % (mod_astro.time_print(fileObj.file_time), fileObj.file_name)
