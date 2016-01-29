#!../../virtual-env/bin/python
# updateUser.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# This script is used to add users to the web interface

# It is useful to run this after <sql/rebuild.sh>

import sys

import meteorpi_db

import mod_settings

db = meteorpi_db.MeteorDatabase(mod_settings.settings['dbFilestore'])

# List all current user accounts
print "Current web interface accounts"
print "------------------------------"
users = db.get_users()
for user in users:
    print "%20s -- roles: %s\n" % (user.user_id, " ".join(user.roles))
print "\n"

# Select user to update
default_user_id = "admin"
if len(sys.argv) > 1:
    user_id = sys.argv[1]
else:
    user_id = raw_input('Select userId to update <default %s>: ' % default_user_id)
if not user_id:
    user_id = default_user_id

# Enter password
password = raw_input('Enter password: ')

# Enter roles
defaultRoles = "user voter obstory_admin import"
roles = raw_input('Enter roles <default %s>: ' % defaultRoles).split()
if not roles:
    roles = defaultRoles.split()

db.create_or_update_user(user_id=user_id, password=password, roles=roles)

# Commit changes to database
db.commit()
