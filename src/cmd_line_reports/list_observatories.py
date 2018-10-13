#!../../virtualenv/bin/python3
# -*- coding: utf-8 -*-
# list_observatories.py
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
List all of the observatories which have data entered into the database
"""

import meteorpi_db

from meteorpi_helpers import settings_read

db = meteorpi_db.MeteorDatabase(settings_read.settings['dbFilestore'])

# List current observatory statuses
print("List of observatories")
print("---------------------")

obstory_list = db.get_obstory_names()
obstory_list.sort()

print("\nObservatories: %s\n" % obstory_list)

for obstory in obstory_list:
    print("%s\n" % obstory)
    print("  * Observatory configuration")
    o = db.get_obstory_from_name(obstory)
    for item in ['latitude', 'longitude', 'name', 'publicId']:
        print("    * %s = %s" % (item, o[item]))
    status = db.get_obstory_status(obstory_name=obstory)
    status_keys = list(status.keys())
    status_keys.sort()
    print("\n  * Additional metadata")
    for item in status_keys:
        print("    * %s = %s" % (item, status[item]))
    print("\n")
