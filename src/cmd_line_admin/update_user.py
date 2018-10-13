#!../../virtualenv/bin/python3
# -*- coding: utf-8 -*-
# update_user.py
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
This script is used to add users to the web interface

It is useful to run this after <sql/rebuild.sh>
"""

import sys

from meteorpi_helpers.obsarchive import archive_db

from meteorpi_helpers import settings_read

db = archive_db.MeteorDatabase(settings_read.settings['dbFilestore'])

# List all current user accounts
print("Current web interface accounts")
print("------------------------------")
users = db.get_users()
for user in users:
    print("%20s -- roles: %s" % (user.user_id, " ".join(user.roles)))
print("\n")

# Select user to update
default_user_id = "admin"
if len(sys.argv) > 1:
    user_id = sys.argv[1]
else:
    user_id = input('Select userId to update <default %s>: ' % default_user_id)
if not user_id:
    user_id = default_user_id

# Enter password
password = input('Enter password: ')

# Enter roles
defaultRoles = "user voter obstory_admin import"
roles = input('Enter roles <default %s>: ' % defaultRoles).split()
if not roles:
    roles = defaultRoles.split()

db.create_or_update_user(user_id=user_id.strip(), password=password.strip(), roles=roles)

# Commit changes to database
db.commit()
