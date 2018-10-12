#!../../virtual-env/bin/python
# checkDatabaseIntegrity.py
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

# Checks for missing files, duplicate publicIds, etc

import os
import meteorpi_db
import mod_settings

db = meteorpi_db.MeteorDatabase(mod_settings.settings['dbFilestore'])
sql = db.con

# Check observation groups
print("Checking observation groups...")
sql.execute("SELECT publicId FROM archive_obs_groups;")
seen_ids = {}
for item in sql.fetchall():
    id = item['publicId']
    if id in seen_ids:
        print("Observation groups: Duplicate ID <%s>" % id)
    else:
        seen_ids[id] = True

# Check observations
print("Checking observations...")
sql.execute("SELECT publicId FROM archive_observations;")
seen_ids = {}
for item in sql.fetchall():
    id = item['publicId']
    if id in seen_ids:
        print("Observations: Duplicate ID <%s>" % id)
    else:
        seen_ids[id] = True

# Check files
print("Checking files...")
sql.execute("SELECT repositoryFname FROM archive_files;")
seen_ids = {}
for item in sql.fetchall():
    id = item['repositoryFname']
    if id in seen_ids:
        print("Files: Duplicate ID <%s>" % id)
    else:
        seen_ids[id] = True

# Check files exist
print("Checking whether files exist...")
sql.execute("SELECT repositoryFname FROM archive_files;")
for item in sql.fetchall():
    id = item['repositoryFname']
    if not os.path.exists(db.file_path_for_id(id)):
        print("Files: Missing file ID <%s>" % id)
