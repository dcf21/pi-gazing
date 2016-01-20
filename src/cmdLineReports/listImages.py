#!../../virtual-env/bin/python
# listImages.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# Lists all of the still (timelapse) images recorded by an observatory between specified start and end times

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
img_type = "meteorpi:timelapse/frame/bgrdSub/lensCorr"
stride = 5

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

if utc_max == 0:
    utc_max = time.time()

print "# ./listImages.py %f %f \"%s\" \"%s\" \"%s\" %d\n" % (utc_min, utc_max, obstory_name, label, img_type, stride)

db = meteorpi_db.MeteorDatabase(mod_settings.settings['dbFilestore'])

s = db.get_obstory_status(obstory_name=obstory_name)
if not s:
    print "Unknown observatory <%s>. Run ./listObservatories.py to see a list of available observatories." % \
          obstory_name
    sys.exit(0)

search = mp.FileRecordSearch(obstory_ids=[obstory_name], semantic_type=img_type,
                             time_min=utc_min, time_max=utc_max, limit=1000000)
files = db.search_files(search)
files = files['files']
files.sort(key=lambda x: x.file_time)

print "Observatory <%s>" % obstory_name
print "  * %d matching files in time range %s --> %s" % (len(files),
                                                         mod_astro.time_print(utc_min),
                                                         mod_astro.time_print(utc_max))
count = 1
for file_item in files:
    count += 1
    if not (count % stride == 0):
        continue
    sky_clarity = db.get_file_metadata(file_item.id, 'meteorpi:skyClarity')
    if sky_clarity is None:
        sky_clarity = -1
    [year, month, day, h, m, s] = mod_astro.inv_julian_day(mod_astro.jd_from_utc(file_item.file_time))
    print "  * Date %04d/%02d/%02d %02d:%02d:%02d UTC   Sky clarity %8.1f   Filename <%s>" % (
        year, month, day, h, m, s, sky_clarity, file_item.id)
