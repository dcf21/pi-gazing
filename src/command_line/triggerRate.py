#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# triggerRate.py
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
import sys
import time

import math
from pigazing_helpers import dcf_ast
from pigazing_helpers.obsarchive import obsarchive_db, obsarchive_model
from pigazing_helpers.settings_read import settings, installation_info


# Get file metadata, turning NULL data into zeros
def get_file_metadata(db, id, key):
    val = db.get_file_metadata(id, key)
    if val is None:
        return 0
    return val


def list_trigger_rate(utc_min, utc_max, obstory):
    db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                           db_host=installation_info['mysqlHost'],
                                           db_user=installation_info['mysqlUser'],
                                           db_password=installation_info['mysqlPassword'],
                                           db_name=installation_info['mysqlDatabase'],
                                           obstory_id=installation_info['observatoryId'])

    # Check that requested observatory exists
    try:
        obstory_info = db.get_obstory_from_id(obstory_id=obstory)
    except ValueError:
        print("Unknown observatory <{}>. Run ./listObservatories.py to see a list of available observatories.".
              format(obstory))
        sys.exit(0)

    search = obsarchive_model.FileRecordSearch(obstory_ids=[obstory],
                                               semantic_type="pigazing:timelapse",
                                               time_min=utc_min, time_max=utc_max,
                                               limit=1000000)
    files = db.search_files(search)
    files = files['files']
    files.sort(key=lambda x: x.file_time)

    search = obsarchive_model.ObservationSearch(obstory_ids=[obstory],
                                                observation_type="pigazing:movingObject/",
                                                time_min=utc_min, time_max=utc_max,
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
        print("No results found for observatory <{}>".format(obstory))
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
                sky_clarity = "{:.1f}".format(
                    sum(get_file_metadata(db, i.id, 'pigazing:skyClarity') for i in d['images']) /
                    len(d['images']))
            if d['images'] or d['events']:
                out.write(
                    "{:12d} {:12d} {:12s} {:12s}\n".format(len(d['images']), len(d['events']), sky_clarity, sun_alt))
                printed_blank_line = False
        else:
            if not printed_blank_line:
                out.write("\n")
            printed_blank_line = True
        hour_start += 3600


if __name__ == "__main__":
    # Read input parameters
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--t-min', dest='utc_min', default=0,
                        type=float,
                        help="Only list events seen after the specified unix time")
    parser.add_argument('--t-max', dest='utc_max', default=time.time(),
                        type=float,
                        help="Only list events seen before the specified unix time")
    parser.add_argument('--observatory', dest='obstory_id', default=installation_info['observatoryId'],
                        help="ID of the observatory we are to list events from")
    args = parser.parse_args()

    list_trigger_rate(utc_min=args.utc_min,
                      utc_max=args.utc_max,
                      obstory=args.obstory_id
                      )
