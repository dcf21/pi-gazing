#!../../pythonenv/bin/python
# updateCameraStatus.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# This script is used to manually update a camera status

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

# Select camera status to update
defaultCameraId = CAMERA_ID;
cameraId = raw_input('Select cameraId to update <default %s>: '%defaultCameraId)
if not cameraId: cameraId = defaultCameraId

cameraStatus = fdb_handle.get_camera_status(camera_id=cameraId)

if not cameraStatus:
  cameraStatus = mp.CameraStatus( "watec_default" , "watec_902h" , "" , "default" , mp.Orientation( 0,0,360,0,0 ), mp.Location( LATITUDE_DEFAULT , LONGITUDE_DEFAULT , False ), cameraId )

# Reset clipping region
cameraStatus.regions=[]

# Read user-specified clipping region
print "Enter new clipping region. Specify one white-space separated x y coordinate on each line. Leave a blank line to start a new region. Leave two blank lines to finish:"
ptlist=[]
while 1:
  line = raw_input()
  words=line.split()
  if len(words)==2:
    x = float(words[0])
    y = float(words[1])
    ptlist.extend([x,y])
  else:
    if len(ptlist)>1: cameraStatus.add_region(ptlist)
    else            : break
    ptlist=[]

# Apply to historical data?
backdate   = raw_input('Apply to all historical data? (Y/N) ')
valid_from = None
if backdate in 'Yy': valid_from=datetime.datetime.fromtimestamp(0)

fdb_handle.update_camera_status(cameraStatus, time=valid_from, camera_id=cameraId)

