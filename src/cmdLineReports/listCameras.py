#!/usr/bin/python
# listCameras.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import datetime

from mod_settings import *

import meteorpi_model as mp
import meteorpi_fdb
fdb_handle = meteorpi_fdb.MeteorDatabase( DBPATH , FDBFILESTORE )

# List current camera statuses
print "Current camera statuses"
print "-----------------------"
cameraList = fdb_handle.get_cameras()
for cameraId in cameraList:
  print "%s\n  * %s\n  * High water mark: %s"%(cameraId,fdb_handle.get_camera_status(camera_id=cameraId),fdb_handle.get_high_water_mark(camera_id=cameraId))
print "\n"

