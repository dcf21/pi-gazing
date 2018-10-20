#!../../virtualenv/bin/python3
# -*- coding: utf-8 -*-
# timelapse_movie.py
#
# -------------------------------------------------
# Copyright 2015-2018 Dominic Ford
#
# This file is part of Meteor Pi.
#
# Meteor Pi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Meteor Pi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Meteor Pi.  If not, see <http://www.gnu.org/licenses/>.
# -------------------------------------------------

"""
Make a timelapse video of still images recorded between specified start and end times
"""

import os
import sys
import time
import argparse
from meteorpi_helpers.obsarchive import obsarchive_db
from meteorpi_helpers.settings_read import settings, installation_info

db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                       db_host=settings['mysqlHost'],
                                       db_user=settings['mysqlUser'],
                                       db_password=settings['mysqlPassword'],
                                       db_name=settings['mysqlDatabase'],
                                       obstory_id=installation_info['observatoryId'])

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

print("# ./timelapseMovie.py %f %f \"%s\" \"%s\" \"%s\" %d\n" % (utc_min, utc_max, obstory_name,
                                                                 label, img_type, stride))

db = meteorpi_db.MeteorDatabase(settings_read.settings['dbFilestore'])

try:
    obstory_info = db.get_obstory_from_name(obstory_name=obstory_name)
except ValueError:
    print("Unknown observatory <%s>. Run ./listObservatories.py to see a list of available observatories." % \
          obstory_name)
    sys.exit(0)

obstory_id = obstory_info['publicId']

search = mp.FileRecordSearch(obstory_ids=[obstory_id], semantic_type=img_type,
                             time_min=utc_min, time_max=utc_max, limit=1000000)
files = db.search_files(search)
files = files['files']
files.sort(key=lambda x: x.file_time)

print("Found %d images between time <%s> and <%s> from observatory <%s>" % (len(files), utc_min, utc_max, obstory_name))

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
