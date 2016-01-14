#!../../virtual-env/bin/python
# observatoryStatus.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# Lists all of the metadata updates posted by a particular observatory between two given unix times

import time
import sys

import meteorpi_model as mp
import meteorpi_db

import mod_astro
import mod_settings

import installation_info

db = meteorpi_db.MeteorDatabase(mod_settings.settings['dbFilestore'])

utc_min = time.time() - 3600 * 24
utc_max = time.time()
obstory_name = installation_info.local_conf['observatoryName']

argc = len(sys.argv)
if argc > 1:
    utc_min = float(sys.argv[1])
if argc > 2:
    utc_max = float(sys.argv[2])
if len(sys.argv) > 3:
    obstory_name = sys.argv[3]

if utc_max == 0:
    utc_max = time.time()

print "# ./observatoryStatus.py %f %f \"%s\"\n" % (utc_min, utc_max, obstory_name)

s = db.get_obstory_status(obstory_name=obstory_name)
if not s:
    print "Unknown observatory <%s>. Run ./listObservatories.py to see a list of available observatories." % \
          obstory_name
    sys.exit(0)

title = "Observatory <%s>" % obstory_name
print "\n\n%s\n%s" % (title, "-" * len(title))

search = mp.ObservatoryMetadataSearch(obstory_ids=[obstory_name], time_min=utc_min, time_max=utc_max)
data = db.search_obstory_metadata(search)
data = data['items']
data.sort(key=lambda x: x.time)
print "  * %d matching metadata items in time range %s --> %s" % (len(data),
                                                                  mod_astro.time_print(utc_min),
                                                                  mod_astro.time_print(utc_max))

# Check which items remain current
data.reverse()
keys_seen = []
for item in data:
    if item.key not in keys_seen:
        item.still_current = True
        keys_seen.append(item.key)
    else:
        item.still_current = False
data.reverse()

# Display list of items
for item in data:
    if item.still_current:
        current_flag = "+"
    else:
        current_flag = " "
    print "  * %s [ID %s] %s -- %16s = %s" % (current_flag, item.id, mod_astro.time_print(item.time),
                                              item.key, item.value)
