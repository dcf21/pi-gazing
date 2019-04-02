#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# observatory_status.py
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
Lists all of the metadata updates posted by a particular observatory between two given unix times
"""

import argparse
import sys
import time

from pigazing_helpers import dcf_ast
from pigazing_helpers.obsarchive import obsarchive_db
from pigazing_helpers.obsarchive import obsarchive_model as mp
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
parser.add_argument('--stride', dest='stride', default=1, type=int,
                    help="Only show every nth item, to reduce output")
args = parser.parse_args()

print("# ./observatory_status.py --t-min {:f} --t-max {:f} --observatory \"{}\" --stride {}\n".
      format(args.utc_min, args.utc_max, args.obstory_id, args.stride))

try:
    obstory_info = db.get_obstory_from_id(obstory_id=args.obstory_id)
except ValueError:
    print("Unknown observatory <{}>. Run ./list_observatories.py to see a list of available observatories.".
          format(args.obstory_id))
    sys.exit(0)

title = "Observatory <{}>".format(args.obstory_id)
print("\n\n{}\n{}".format(title, "-" * len(title)))

search = mp.ObservatoryMetadataSearch(obstory_ids=[args.obstory_id], time_min=args.utc_min, time_max=args.utc_max)
data = db.search_obstory_metadata(search)
data = data['items']
data.sort(key=lambda x: x.time)
print("  * {:d} matching metadata items in time range {} --> {}".format(len(data),
                                                                        dcf_ast.date_string(args.utc_min),
                                                                        dcf_ast.date_string(args.utc_max)))

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
    print("  * {} [ID {}] {} -- {:16s} = {}".format(current_flag, item.id, dcf_ast.date_string(item.time),
                                                    item.key, item.value))
