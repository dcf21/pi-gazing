#!../../virtual-env/bin/python
# listCameras.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import meteorpi_db

import mod_settings

db = meteorpi_db.MeteorDatabase(mod_settings.settings['dbFilestore'])


# List current camera statuses
print "List of cameras"
print "---------------"

obstory_list = db.get_obstory_names()
obstory_list.sort()

print "\nCameras: %s\n" % obstory_list

for obstory in obstory_list:
    print "%s\n" % obstory
    status = db.get_obstory_status(obstory_name=obstory)
    for item in status:
        print "  * %s = %s\n" % (item, status[item])
    print "\n"
