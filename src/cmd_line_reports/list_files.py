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

import time
import sys
import argparse
from meteorpi_helpers import dcf_ast
from meteorpi_helpers.obsarchive import obsarchive_db
from meteorpi_helpers.settings_read import settings, installation_info

db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                       db_host=settings['mysqlHost'],
                                       db_user=settings['mysqlUser'],
                                       db_password=settings['mysqlPassword'],
                                       db_name=settings['mysqlDatabase'],
                                       obstory_id=installation_info['observatoryId'])

utc_min = 0
utc_max = time.time()

argc = len(sys.argv)
if argc > 1:
    utc_min = float(sys.argv[1])
if argc > 2:
    utc_max = float(sys.argv[2])

print("# ./listFiles.py %s %s\n" % (utc_min, utc_max))

obstory_list = db.get_obstory_names()
for obstory_name in obstory_list:
    title = "Observatory <%s>" % obstory_name
    print("\n\n%s\n%s" % (title, "-" * len(title)))

    obstory_info = db.get_obstory_from_name(obstory_name=obstory_name)
    obstory_id = obstory_info['publicId']

    search = mp.FileRecordSearch(obstory_ids=[obstory_id], time_min=utc_min, time_max=utc_max)
    files = db.search_files(search)
    files = files['files']
    files.sort(key=lambda x: x.file_time)
    print("  * %d matching files in time range %s --> %s" % (len(files),
                                                             dcf_ast.date_string(utc_min),
                                                             dcf_ast.date_string(utc_max)))
    for fileObj in files:
        print("  * %s -- %s" % (dcf_ast.date_string(fileObj.file_time), fileObj.file_name))
