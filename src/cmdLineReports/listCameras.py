#!../../virtual-env/bin/python
# listObservatories.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# List all of the observatories which have data entered into the database

import meteorpi_db

import mod_settings

db = meteorpi_db.MeteorDatabase(mod_settings.settings['dbFilestore'])


# List current observatory statuses
print "List of observatories"
print "---------------------"

obstory_list = db.get_obstory_names()
obstory_list.sort()

print "\nObservatories: %s\n" % obstory_list

for obstory in obstory_list:
    print "%s\n" % obstory
    status = db.get_obstory_status(obstory_name=obstory)
    for item in status:
        print "  * %s = %s\n" % (item, status[item])
    print "\n"
