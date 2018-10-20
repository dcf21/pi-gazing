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

import argparse
import sys

from meteorpi_helpers.obsarchive import obsarchive_db
from meteorpi_helpers.settings_read import settings, installation_info

db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                       db_host=settings['mysqlHost'],
                                       db_user=settings['mysqlUser'],
                                       db_password=settings['mysqlPassword'],
                                       db_name=settings['mysqlDatabase'],
                                       obstory_id=installation_info['observatoryId'])

# Read input parameters
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--user', dest='user', default=None,
                    help="The user account to update")
args = parser.parse_args()

# List all current user accounts
print("Current web interface accounts")
print("------------------------------")
users = db.get_users()
for user in users:
    print("%20s -- roles: %s" % (user.user_id, " ".join(user.roles)))
print("\n")

# If no user account specified to update, stop now
if args.user is None:
    sys.exit(0)

# Enter password
password = input('Enter password: ')

# Enter roles
defaultRoles = "user voter obstory_admin import"
roles = input('Enter roles <default %s>: ' % defaultRoles).split()
if not roles:
    roles = defaultRoles.split()

db.create_or_update_user(username=args.userstrip(), password=password.strip(), roles=roles,
                         name=None, job=None, email=None, join_date=None, profile_pic=None, profile_text=None)

# Commit changes to database
db.commit()
