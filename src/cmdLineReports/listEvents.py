#!../../virtual-env/bin/python
# listEvents.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# Lists all of the moving objects recorded by an observatory between given unix times

import sys
import time

import meteorpi_db
import meteorpi_model as mp

import mod_astro
import mod_settings
import installation_info

utc_min = time.time() - 3600 * 24
utc_max = time.time()
obstory_name = installation_info.local_conf['observatoryName']
label = ""
img_type = ""
stride = 1

if len(sys.argv) > 1:
    utc_min = float(sys.argv[1])
if len(sys.argv) > 2:
    utc_max = float(sys.argv[2])
if len(sys.argv) > 3:
    obstory_name = sys.argv[3]
if len(sys.argv) > 4:
    label = sys.argv[4]
if len(sys.argv) > 5:
    img_type = sys.argv[5]
if len(sys.argv) > 6:
    stride = int(sys.argv[6])

if (utc_max == 0):
    utc_max = time.time()

print "# ./listEvents.py %f %f \"%s\" \"%s\" \"%s\" %d\n" % (utc_min, utc_max, obstory_name, label, img_type, stride)

db = meteorpi_db.MeteorDatabase(mod_settings.settings['dbFilestore'])

try:
    obstory_info = db.get_obstory_from_name(obstory_name=obstory_name)
except ValueError:
    print "Unknown observatory <%s>. Run ./listObservatories.py to see a list of available observatories." % \
          obstory_name
    sys.exit(0)

obstory_id = obstory_info['publicId']

search = mp.ObservationSearch(obstory_ids=[obstory_id],
                              time_min=utc_min, time_max=utc_max, limit=1000000)
triggers = db.search_observations(search)
triggers = triggers['obs']
triggers.sort(key=lambda x: x.obs_time)

print "Observatory <%s>" % obstory_name
print "  * %d matching triggers in time range %s --> %s" % (len(triggers),
                                                            mod_astro.time_print(utc_min),
                                                            mod_astro.time_print(utc_max))
for event in triggers:
    event_id = event.id
    duration = db.get_observation_metadata(event_id, "meteorpi:duration")
    peak_amplitude = db.get_observation_metadata(event_id, "meteorpi:amplitudePeak")
    if duration is None:
        duration = -1
    if peak_amplitude is None:
        peak_amplitude = -1
    print "  * [ID %s] %s -- Duration %5.1f sec -- Peak amplitude %7.1f" % (event_id,
        mod_astro.time_print(event.obs_time), duration, peak_amplitude)
