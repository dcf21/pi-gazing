#!../../virtual-env/bin/python
# listCameras.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import meteorpi_db

from mod_settings import *

db_handle = meteorpi_db.MeteorDatabase(DBPATH, DBFILESTORE)

# List current camera statuses
print "List of cameras"
print "---------------"
cameraList = db_handle.get_cameras()
cameraList.sort()

print "\nCameras: %s\n" % cameraList

for cameraId in cameraList:
    print "Camera <%s>" % cameraId
    print "  * High water mark: %s" % db_handle.get_high_water_mark(camera_id=cameraId)
    s = db_handle.get_camera_status(camera_id=cameraId)
    print "  * Software: %s" % s.software_version
    print "  * Lens: %s" % s.lens
    print "  * Sensor: %s" % s.sensor
    print "  * Validity of this status: %s -> %s" % (s.valid_from, s.valid_to)
    print "  * Location: %s" % s.location
    print "  * Orientation: %s" % s.orientation
    print "  * Regions: %s" % s.regions
    print "\n"
