#!../../virtualenv/bin/python3
# -*- coding: utf-8 -*-
# update_user.py
#
# -------------------------------------------------
# Copyright 2015-2019 Dominic Ford
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
This script is used to add users to the web interface

It is useful to run this after <sql/rebuild.sh>
"""

import argparse
import sys

from pigazing_helpers.obsarchive import obsarchive_db
from pigazing_helpers.settings_read import settings, installation_info

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
parser.add_argument('--password', dest='password', default=None,
                    help="The password for this user")
parser.add_argument('--role', dest='roles', action='append', default=None,
                    help="The list of roles for this user")
args = parser.parse_args()

# List all current user accounts
print("Current web interface accounts")
print("------------------------------")
user_objects = db.get_users()
for user_object in user_objects:
    print("%20s -- roles: %s" % (user_object.user_id, " ".join(user_object.roles)))
print("\n")

# If no user account specified to update, stop now
if args.user is None:
    sys.exit(0)

# Enter password
if args.pasword is None:
    password = input('Enter password: ')

# Enter roles
if args.roles is None:
    default_roles = "user voter obstory_admin import"
    args.roles = input('Enter roles <default %s>: ' % default_roles).split()
    if not args.roles:
        args.roles = default_roles.split()

db.create_or_update_user(username=args.userstrip(), password=args.password.strip(), roles=args.roles,
                         name=None, job=None, email=None, join_date=None, profile_pic=None, profile_text=None)

# Commit changes to database
db.commit()
