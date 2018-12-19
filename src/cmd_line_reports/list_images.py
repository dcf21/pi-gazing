#!../../virtualenv/bin/python3
# -*- coding: utf-8 -*-
# list_images.py
#
# -------------------------------------------------
# Copyright 2015-2018 Dominic Ford
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
Lists all of the still (time-lapse) images recorded by an observatory between specified start and end times
"""

import argparse
import sys
import time

from pigazing_helpers import dcf_ast
from pigazing_helpers.obsarchive import obsarchive_db
from pigazing_helpers.obsarchive import obsarchive_model as mp
from pigazing_helpers.settings_read import settings, installation_info

db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                       db_host=settings['mysqlHost'],
                                       db_user=settings['mysqlUser'],
                                       db_password=settings['mysqlPassword'],
                                       db_name=settings['mysqlDatabase'],
                                       obstory_id=installation_info['observatoryId'])

# Read input parameters
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--t-min', dest='utc_min', default=time.time() - 3600 * 24,
                    type=float,
                    help="Only list events seen after the specified unix time")
parser.add_argument('--t-max', dest='utc_max', default=time.time(),
                    type=float,
                    help="Only list events seen before the specified unix time")
parser.add_argument('--observatory', dest='obstory_id', default=installation_info.local_conf['observatoryId'],
                    help="ID of the observatory we are to list events from")
parser.add_argument('--img-type', dest='img_type', default="pigazing:timelapse/frame/bgrdSub/lensCorr",
                    help="The type of image to list")
parser.add_argument('--stride', dest='stride', default=1, type=int,
                    help="Only show every nth item, to reduce output")
args = parser.parse_args()

print("# ./list_images.py {} {} \"{}\" \"{}\" {}\n".
      format(args.utc_min, args.utc_max, args.obstory_id, args.img_type, args.stride))

try:
    obstory_info = db.get_obstory_from_id(obstory_id=args.obstory_id)
except ValueError:
    print("Unknown observatory <{}>. Run ./list_observatories.py to see a list of available observatories.".
          format(args.obstory_id))
    sys.exit(0)

search = mp.FileRecordSearch(obstory_ids=[args.obstory_id], semantic_type=args.img_type,
                             time_min=args.utc_min, time_max=args.utc_max, limit=1000000)
files = db.search_files(search)
files = files['files']
files.sort(key=lambda x: x.file_time)

print("Observatory <{}>".format(args.obstory_id))
print("  * {:d} matching files in time range {} --> {}".format(len(files),
                                                               dcf_ast.date_string(args.utc_min),
                                                               dcf_ast.date_string(args.utc_max)))
for count, file_item in enumerate(files):
    if not (count % args.stride == 0):
        continue
    sky_clarity = db.get_file_metadata(file_item.id, 'pigazing:skyClarity')
    if sky_clarity is None:
        sky_clarity = -1
    [year, month, day, h, m, s] = dcf_ast.inv_julian_day(dcf_ast.jd_from_unix(file_item.file_time))
    print("  * Date {:04d}/{:02d}/{:02d} {:02d}:{:02d}:{:02d} UTC   Sky clarity {:8.1f}   Filename <{}>".
          format(year, month, day, h, m, s, sky_clarity, file_item.id))
