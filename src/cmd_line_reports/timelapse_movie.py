#!../../virtualenv/bin/python3
# -*- coding: utf-8 -*-
# timelapse_movie.py
#
# -------------------------------------------------
# Copyright 2015-2019 Dominic Ford
#
# This file is part of Pi Gazing.
#
# Pi Gazing is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pi Gazing is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Pi Gazing.  If not, see <http://www.gnu.org/licenses/>.
# -------------------------------------------------

"""
Make a time lapse video of still images recorded between specified start and end times
"""

import argparse
import os
import sys
import time

from pigazing_helpers.obsarchive import obsarchive_db, obsarchive_model
from pigazing_helpers.settings_read import settings, installation_info

db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                       db_host=installation_info['mysqlHost'],
                                       db_user=installation_info['mysqlUser'],
                                       db_password=installation_info['mysqlPassword'],
                                       db_name=installation_info['mysqlDatabase'],
                                       obstory_id=installation_info['observatoryId'])

# Read input parameters
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--t-min', dest='utc_min', default=time.time() - 3600 * 24,
                    type=float,
                    help="Only list events seen after the specified unix time")
parser.add_argument('--t-max', dest='utc_max', default=time.time(),
                    type=float,
                    help="Only list events seen before the specified unix time")
parser.add_argument('--observatory', dest='obstory_id', default=installation_info['observatoryId'],
                    help="ID of the observatory we are to list events from")
parser.add_argument('--label', dest='label', default="",
                    help="Label to put at the bottom of each frame of the video")
parser.add_argument('--img-type', dest='img_type', default="pigazing:timelapse/frame/bgrdSub/lensCorr",
                    help="The type of image to list")
parser.add_argument('--stride', dest='stride', default=1, type=int,
                    help="Only show every nth item, to reduce output")
args = parser.parse_args()

print("# ./timelapse_movie.py --t-min {} --t-max {} --observatory \"{}\" --label \"{}\" --img-type \"{}\" --stride {}\n"
      .format(args.utc_min, args.utc_max, args.obstory_id, args.label, args.img_type, args.stride))

pid = os.getpid()
tmp = os.path.join("/tmp", "dcf_movieImages_{:d}".format(pid))
os.system("mkdir -p {}".format(tmp))

try:
    obstory_info = db.get_obstory_from_id(obstory_id=args.obstory_id)
except ValueError:
    print("Unknown observatory <{}>. Run ./list_observatories.py to see a list of available observatories.".
          format(args.obstory_id))
    sys.exit(0)

obstory_id = obstory_info['publicId']

search = obsarchive_model.FileRecordSearch(obstory_ids=[obstory_id], semantic_type=args.img_type,
                                           time_min=args.utc_min, time_max=args.utc_max, limit=1000000)
files = db.search_files(search)
files = files['files']
files.sort(key=lambda x: x.file_time)

print("Found {:d} images between time <{}> and <{}> from observatory <{}>".
      format(len(files), args.utc_min, args.utc_max, args.obstory_id))

filename_format = os.path.join(tmp, "frame_{:d}_{{:08d}}.jpg".format(pid))

img_num = 1
for count, file_item in enumerate(files):
    if not (count % args.stride == 0):
        continue
    utc = file_item.file_time
    os.system("convert {} -gravity SouthEast -fill ForestGreen -pointsize 20 -font Ubuntu-Bold "
              "-annotate +16+10 '{} {}' {}""".format(db.file_path_for_id(file_item.id), args.label,
                                                     time.strftime("%d %b %Y %H:%M", time.gmtime(utc)),
                                                     filename_format.format(img_num)))
    img_num += 1

os.system("ffmpeg -r 40 -i {} -codec:v libx264 {}".format(filename_format, os.path.join(tmp, "timelapse.mp4")))
