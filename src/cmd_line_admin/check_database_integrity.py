#!../../virtualenv/bin/python3
# -*- coding: utf-8 -*-
# check_database_integrity.py
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
Checks for missing files, duplicate publicIds, etc
"""

import os

from pigazing_helpers.obsarchive import obsarchive_db
from pigazing_helpers.settings_read import settings, installation_info

db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                       db_host=settings['mysqlHost'],
                                       db_user=settings['mysqlUser'],
                                       db_password=settings['mysqlPassword'],
                                       db_name=settings['mysqlDatabase'],
                                       obstory_id=installation_info['observatoryId'])
sql = db.con

# Check observation groups
print("Checking observation groups...")
sql.execute("SELECT publicId FROM archive_obs_groups;")
seen_ids = {}
for item in sql.fetchall():
    id = item['publicId']
    if id in seen_ids:
        print("Observation groups: Duplicate ID <{}>".format(id))
    else:
        seen_ids[id] = True

# Check observations
print("Checking observations...")
sql.execute("SELECT publicId FROM archive_observations;")
seen_ids = {}
for item in sql.fetchall():
    id = item['publicId']
    if id in seen_ids:
        print("Observations: Duplicate ID <{}>".format(id))
    else:
        seen_ids[id] = True

# Check files
print("Checking files...")
sql.execute("SELECT repositoryFname FROM archive_files;")
seen_ids = {}
for item in sql.fetchall():
    id = item['repositoryFname']
    if id in seen_ids:
        print("Files: Duplicate ID <{}>".format(id))
    else:
        seen_ids[id] = True

# Check files exist
print("Checking whether files exist...")
sql.execute("SELECT repositoryFname FROM archive_files;")
for item in sql.fetchall():
    id = item['repositoryFname']
    if not os.path.exists(db.file_path_for_id(id)):
        print("Files: Missing file ID <{}>".format(id))
