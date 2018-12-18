#!../../virtualenv/bin/python3
# -*- coding: utf-8 -*-
# list_files.py
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
Lists all of the files entered into the database by a particular observatory between two given unix times
"""

import argparse
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
args = parser.parse_args()

print("# ./listFiles.py {} {}\n".format(args.utc_min, args.utc_max))

obstory_id_list = db.get_obstory_ids()
for obstory_id in obstory_id_list:
    title = "Observatory <{}>".format(obstory_id)
    print("\n\n{}\n{}".format(title, "-" * len(title)))

    obstory_info = db.get_obstory_from_id(obstory_id=obstory_id)

    search = mp.FileRecordSearch(obstory_ids=[obstory_id], time_min=args.utc_min, time_max=args.utc_max)
    files = db.search_files(search)
    files = files['files']
    files.sort(key=lambda x: x.file_time)
    print("  * %d matching files in time range %s --> %s" % (len(files),
                                                             dcf_ast.date_string(args.utc_min),
                                                             dcf_ast.date_string(args.utc_max)))
    for file_objects in files:
        print("  * {} -- {}".format(dcf_ast.date_string(file_objects.file_time), file_objects.file_name))
