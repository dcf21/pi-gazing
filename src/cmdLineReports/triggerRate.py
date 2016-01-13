#!../../virtual-env/bin/python
# triggerRate.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# Make a histogram of number raw videos and trigger videos by hour

import sys
import time
import math

import meteorpi_db
import meteorpi_model as mp

import mod_astro
import mod_settings
import installation_info

utc_min = time.time() - 3600 * 24
utc_max = time.time()
obstory_name = installation_info.local_conf['observatoryName']

if len(sys.argv) > 1:
    utc_min = float(sys.argv[1])
if len(sys.argv) > 2:
    utc_max = float(sys.argv[2])
if len(sys.argv) > 3:
    obstory_name = sys.argv[3]

if utc_max == 0:
    utc_max = time.time()

print "# ./triggerRate.py %f %f \"%s\"\n" % (utc_min, utc_max, obstory_name)

db = meteorpi_db.MeteorDatabase(mod_settings.settings['dbFilestore'])

s = db.get_obstory_status(obstory_name=obstory_name)
if not s:
    print "Unknown observatory <%s>. Run ./listObservatories.py to see a list of available observatories." % \
          obstory_name
    sys.exit(0)

search = mp.FileRecordSearch(obstory_ids=[obstory_name], semantic_type="timelapse/frame/lensCorr",
                             time_min=utc_min, time_max=utc_max, limit=1000000)
files = db.search_files(search)
files = files['files']
files.sort(key=lambda x: x.file_time)

search = mp.EventSearch(obstory_ids=[obstory_name], semantic_type="movingObject",
                        time_min=utc_min, time_max=utc_max, limit=1000000)
events = db.search_observations(search)
events = events['events']

histogram = {}

for f in files:
    utc = f.file_time
    hour_start = math.floor(utc / 3600) * 3600
    if hour_start not in histogram:
        histogram[hour_start] = {'events': [], 'images': []}
    histogram[hour_start]['images'].append(f)

for e in events:
    utc = e.obs_time
    hour_start = math.floor(utc / 3600) * 3600
    if hour_start not in histogram:
        histogram[hour_start] = {'events': [], 'images': []}
    histogram[hour_start]['events'].append(e)

# Find time bounds of data
keys = histogram.keys()
keys.sort()
if len(keys) == 0:
    print "No results found for observatory <%s>" % obstory_name
    sys.exit(0)
utc_min = keys[0]
utc_max = keys[-1]

# Render quick and dirty table
out = sys.stdout
hour_start = utc_min
printed_blank_line = True
out.write("# %12s %4s %2s %2s %2s %12s %12s %12s %12s\n" % ("UTC", "Year", "M", "D", "hr", "N_images",
                                                            "N_events", "SkyClarity", "SunAltitude"))
while hour_start <= utc_max:
    if hour_start in histogram:
        [year, month, day, h, m, s] = mod_astro.inv_julian_day(mod_astro.jd_from_utc(hour_start + 1))
        out.write("  %12d %04d %02d %02d %02d " % (hour_start, year, month, day, h))
        d = histogram[hour_start]
        sun_alt = "---"
        sky_clarity = "---"
        if d['images']:
            sun_alt = "%.1f" % (sum(db.get_file_metadata(i, 'sunAlt') for i in d['images']) / len(d['images']))
            sky_clarity = "%.1f" % (sum(db.get_file_metadata(i, 'skyClarity') for i in d['images']) / len(d['images']))
        if d['images'] or d['events']:
            out.write("%12s %12s %12s %12s\n" % (len(d['images']), len(d['events']), sky_clarity, sun_alt))
            printed_blank_line = False
    else:
        if not printed_blank_line:
            out.write("\n")
        printed_blank_line = True
    hour_start += 3600
