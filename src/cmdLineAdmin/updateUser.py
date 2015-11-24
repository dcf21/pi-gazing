#!../../virtual-env/bin/python
# updateUser.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# This script is used to add users to the web interface

import sys

import meteorpi_fdb

from mod_settings import *

fdb_handle = meteorpi_fdb.MeteorDatabase(DBPATH, FDBFILESTORE)

# List all current user accounts
print "Current web interface accounts"
print "------------------------------"
users = fdb_handle.get_users()
for user in users:
    print "%20s -- roles: %s\n" % (user.user_id, " ".join(user.get_roles()))
print "\n"

# Select user to update
defaultUserId = "admin";
if len(sys.argv) > 1:
    defaultUserId = sys.argv[1]
else:
    userId = raw_input('Select userId to update <default %s>: ' % defaultUserId)
if not userId: userId = defaultUserId

# Enter password
password = raw_input('Enter password: ')

# Enter roles
defaultRoles = "user camera_admin import"
roles = raw_input('Enter roles <default %s>: ' % defaultRoles).split()
if not roles: roles = defaultRoles.split()

fdb_handle.create_or_update_user(userId, password, roles)
