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

from pigazing_helpers.obsarchive import obsarchive_db
from pigazing_helpers.settings_read import settings, installation_info

db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                       db_host=settings['mysqlHost'],
                                       db_user=settings['mysqlUser'],
                                       db_password=settings['mysqlPassword'],
                                       db_name=settings['mysqlDatabase'],
                                       obstory_id=installation_info['observatoryId'])

# List current observatory statuses
print("List of observatories")
print("---------------------")

obstory_id_list = db.get_obstory_ids()
obstory_id_list.sort()

print("\nObservatories: %s\n" % obstory_id_list)

for obstory_id in obstory_id_list:
    print("{}\n".format(obstory_id))
    print("  * Observatory configuration")
    obstory_object = db.get_obstory_from_id(obstory_id)
    for item in ['latitude', 'longitude', 'name', 'publicId']:
        print("    * {} = {}".format(item, obstory_object[item]))
    status = db.get_obstory_status(obstory_id=obstory_id)
    status_keys = list(status.keys())
    status_keys.sort()
    print("\n  * Additional metadata")
    for item in status_keys:
        print("    * {} = {}".format(item, status[item]))
    print("\n")
