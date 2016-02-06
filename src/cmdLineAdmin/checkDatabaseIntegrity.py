#!../../virtual-env/bin/python
# checkDatabaseIntegrity.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# Checks for missing files, duplicate publicIds, etc

import os
import meteorpi_db
import mod_settings

db = meteorpi_db.MeteorDatabase(mod_settings.settings['dbFilestore'])
sql = db.con

# Check observation groups
print "Checking observation groups..."
sql.execute("SELECT publicId FROM archive_obs_groups;")
seen_ids = []
for item in sql.fetchall():
    id = item['publicId']
    if id in seen_ids:
        print "Observation groups: Duplicate ID <%s>" % id
    else:
        seen_ids.append(id)

# Check observations
print "Checking observations..."
sql.execute("SELECT publicId FROM archive_observations;")
seen_ids = []
for item in sql.fetchall():
    id = item['publicId']
    if id in seen_ids:
        print "Observations: Duplicate ID <%s>" % id
    else:
        seen_ids.append(id)

# Check files
print "Checking files..."
sql.execute("SELECT repositoryFname FROM archive_files;")
seen_ids = []
for item in sql.fetchall():
    id = item['repositoryFname']
    if id in seen_ids:
        print "Files: Duplicate ID <%s>" % id
    else:
        seen_ids.append(id)

# Check files
print "Checking whether files exist..."
for item in sql.fetchall():
    id = item['repositoryFname']
    if not os.path.exists(db.file_path_for_id(id)):
        print "Files: Missing file ID <%s>" % id
