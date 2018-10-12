#!../../virtual-env/bin/python
# updateRegions.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# -------------------------------------------------
# Copyright 2016 Cambridge Science Centre.

# This file is part of Meteor Pi.

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

# This script is used to manually update an observatory status

# Observing regions are used to specify that a particular observatory should only analyse certain portions of the
# visible field to look for moving objects (e.g. meteors). This is useful when the field also contains distracting
# objects such as buildings, roads, etc, where humans are often moving around.

# You should enter a series of coordinate positions which represent the corners of a polygon within which the
# observatory should search for moving objects. This is a bit fiddly to do through a commandline interface, so you
# may want to use the web interface instead.

import sys
import json

import meteorpi_db
import meteorpi_model as mp

import mod_settings
import installation_info

db = meteorpi_db.MeteorDatabase(mod_settings.settings['dbFilestore'])


def fetch_option(title, key, indict, default, argv_index):
    if key in indict:
        default = indict[key]
    if (argv_index > 0) and (len(sys.argv) > argv_index):
        value = sys.argv[argv_index]
    else:
        value = input('Set %s <default %s>: ' % (title, default))
    if not value:
        value = default
    return value


# List current observatory statuses
print("Current observatory statuses")
print("----------------------------")
obstory_list = db.get_obstory_names()
for obstory in obstory_list:
    print("%s\n" % obstory)
    status = db.get_obstory_status(obstory_name=obstory)
    for item in status:
        print("  * %s = %s\n" % (item, status[item]))
    print("\n")

# Select observatory status to update
obstory = fetch_option(title="observatory to update",
                       key="_",
                       indict={},
                       default=installation_info.local_conf['observatoryName'],
                       argv_index=1)

assert obstory in obstory_list, "Observatory does not exist!"

# Find out time that metadata update should be applied to
metadata_time = fetch_option(title="time stamp for update",
                             key="_",
                             indict={},
                             default=mp.now(),
                             argv_index=2)
metadata_time = float(metadata_time)

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

db.register_obstory_metadata(obstory_name=obstory,
                             key="clippingRegion",
                             value=json.dumps(regions),
                             metadata_time=metadata_time,
                             time_created=mp.now(),
                             user_created="system")

# Commit changes to database
db.commit()
