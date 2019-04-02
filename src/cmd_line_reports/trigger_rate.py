#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# trigger_rate.py
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
Make a histogram of the number of moving objects of time lapse still images recorded by an observatory each hour
This is displayed as a table which can subsequently be plotted as a graph using, e.g. gnuplot
"""

import argparse
import math
import sys
import time

from pigazing_helpers import dcf_ast
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
args = parser.parse_args()

print("# ./trigger_rate.py --t-min {:f} --t-max {:f} --observatory \"{}\"\n".
      format(args.utc_min, args.utc_max, args.obstory_id))


# Get file metadata, turning NULL data into zeros
def get_file_metadata(db, id, key):
    val = db.get_file_metadata(id, key)
    if val is None:
        return 0
    return val


# Check that requested observatory exists
try:
    obstory_info = db.get_obstory_from_id(obstory_id=args.obstory_id)
except ValueError:
    print("Unknown observatory <{}>. Run ./list_observatories.py to see a list of available observatories.".
          format(args.obstory_id))
    sys.exit(0)

search = obsarchive_model.FileRecordSearch(obstory_ids=[args.obstory_id],
                                           semantic_type="pigazing:timelapse/frame",
                                           time_min=args.utc_min, time_max=args.utc_max,
                                           limit=1000000)
files = db.search_files(search)
files = files['files']
files.sort(key=lambda x: x.file_time)

search = obsarchive_model.ObservationSearch(obstory_ids=[args.obstory_id],
                                            observation_type="movingObject",
                                            time_min=args.utc_min, time_max=args.utc_max,
                                            limit=1000000)
events = db.search_observations(search)
events = events['obs']

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
keys = list(histogram.keys())
keys.sort()
if len(keys) == 0:
    print("No results found for observatory <{}>".format(args.obstory_id))
    sys.exit(0)
utc_min = keys[0]
utc_max = keys[-1]

# Render quick and dirty table
out = sys.stdout
hour_start = utc_min
printed_blank_line = True
out.write("# {:12s} {:4s} {:2s} {:2s} {:2s} {:12s} {:12s} {:12s} {:12s}\n".format("UTC", "Year", "M", "D", "hr",
                                                                                  "N_images", "N_events",
                                                                                  "SkyClarity", "SunAltitude"))
while hour_start <= utc_max:
    if hour_start in histogram:
        [year, month, day, h, m, s] = dcf_ast.inv_julian_day(dcf_ast.jd_from_unix(hour_start + 1))
        out.write("  {:12d} {:04d} {:02d} {:02d} {:02d} ".format(hour_start, year, month, day, h))
        d = histogram[hour_start]
        sun_alt = "---"
        sky_clarity = "---"
        if d['images']:
            sun_alt = "{:.1f}".format(sum(get_file_metadata(db, i.id, 'pigazing:sunAlt') for i in d['images']) /
                                      len(d['images']))
            sky_clarity = "{:.1f}".format(sum(get_file_metadata(db, i.id, 'pigazing:skyClarity') for i in d['images']) /
                                          len(d['images']))
        if d['images'] or d['events']:
            out.write("{:12d} {:12d} {:12s} {:12s}\n".format(len(d['images']), len(d['events']), sky_clarity, sun_alt))
            printed_blank_line = False
    else:
        if not printed_blank_line:
            out.write("\n")
        printed_blank_line = True
    hour_start += 3600
