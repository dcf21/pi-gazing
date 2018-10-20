#!../../virtualenv/bin/python3
# -*- coding: utf-8 -*-
# update_regions.py
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
This script is used to manually update an observatory status

Observing regions are used to specify that a particular observatory should only analyse certain portions of the
visible field to look for moving objects (e.g. meteors). This is useful when the field also contains distracting
objects such as buildings, roads, etc, where humans are often moving around.

You should enter a series of coordinate positions which represent the corners of a polygon within which the
observatory should search for moving objects. This is a bit fiddly to do through a commandline interface, so you
may want to use the web interface instead.
"""

import argparse
import json

from meteorpi_helpers.obsarchive import obsarchive_db
from meteorpi_helpers.settings_read import settings, installation_info

db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                       db_host=settings['mysqlHost'],
                                       db_user=settings['mysqlUser'],
                                       db_password=settings['mysqlPassword'],
                                       db_name=settings['mysqlDatabase'],
                                       obstory_id=installation_info['observatoryId'])

# Read arguments
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--obstory-id',
                    help="Observatory ID code",
                    dest="obstory_id",
                    default=installation_info['observatoryId'])
parser.add_argument('--metadata_time',
                    help="Unix time stamp for update",
                    dest="metadata_time", type=float,
                    default=None)
parser.add_argument('--lens',
                    help="Name of new lens",
                    dest="lens",
                    default=None)
args = parser.parse_args()

# List current observatory statuses
print("Current observatory statuses")
print("----------------------------")
obstory_list = db.get_obstory_names()
for obstory in obstory_list:
    print("%s\n" % obstory)
    status = db.get_obstory_status(obstory_id=obstory)
    for item in status:
        print("  * {} = {}\n".format(item, status[item]))
    print("\n")

assert args.obstory_id in obstory_list, "Observatory does not exist!"

# Read user-specified clipping region
print("Enter new clipping region. Specify one white-space separated x y coordinate on each line.")
print("Leave a blank line to start a new region. Leave two blank lines to finish:")
regions = []
point_list = []
while 1:
    line = input()
    words = line.split()
    if len(words) == 2:
        x = float(words[0])
        y = float(words[1])
        point_list.append([x, y])
    else:
        if len(point_list) > 1:
            regions.append(point_list)
        else:
            break
        point_list = []

db.register_obstory_metadata(obstory_id=args.obstory_id,
                             key="clippingRegion",
                             value=json.dumps(regions),
                             metadata_time=args.metadata_time,
                             time_created=time.time(),
                             user_created="system")

# Commit changes to database
db.commit()
