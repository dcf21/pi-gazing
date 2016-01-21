#!../../virtual-env/bin/python
# timelapseMovie.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# Make a timelapse video of still images recorded between specified start and end times

import os
import sys
import time

import meteorpi_db
import meteorpi_model as mp

import mod_settings
import installation_info

pid = os.getpid()
tmp = os.path.join("/tmp", "dcf_movieImages_%d" % pid)
os.system("mkdir -p %s" % tmp)

utc_min = time.time() - 3600 * 24
utc_max = time.time()
obstory_name = installation_info.local_conf['observatoryName']
label = ""
img_type = "meteorpi:timelapse/frame/bgrdSub/lensCorr"
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

if utc_max == 0:
    utc_max = time.time()

print "# ./timelapseMovie.py %f %f \"%s\" \"%s\" \"%s\" %d\n" % (utc_min, utc_max, obstory_name,
                                                                 label, img_type, stride)

db = meteorpi_db.MeteorDatabase(mod_settings.settings['dbFilestore'])

try:
    obstory_info = db.get_obstory_from_name(obstory_name=obstory_name)
except ValueError:
    print "Unknown observatory <%s>. Run ./listObservatories.py to see a list of available observatories." % \
          obstory_name
    sys.exit(0)

obstory_id = obstory_info['publicId']

search = mp.FileRecordSearch(obstory_ids=[obstory_id], semantic_type=img_type,
                             time_min=utc_min, time_max=utc_max, limit=1000000)
files = db.search_files(search)
files = files['files']
files.sort(key=lambda x: x.file_time)

print "Found %d images between time <%s> and <%s> from observatory <%s>" % (len(files), utc_min, utc_max, obstory_name)

filename_format = os.path.join(tmp, "frame_%d_%%08d.jpg" % pid)

img_num = 1
count = 1
for file_item in files:
    count += 1
    if not (count % stride == 0):
        continue
    utc = file_item.file_time
    os.system("convert %s -gravity SouthEast -fill ForestGreen -pointsize 20 -font Ubuntu-Bold "
              "-annotate +16+10 '%s %s' %s""" % (db.file_path_for_id(file_item.id), label,
                                                 time.strftime("%d %b %Y %H:%M", time.gmtime(utc)),
                                                 filename_format % img_num))
    img_num += 1

os.system("avconv -r 40 -i %s -codec:v libx264 %s" % (filename_format, os.path.join(tmp, "timelapse.mp4")))
