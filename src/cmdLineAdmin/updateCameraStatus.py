#!../../virtual-env/bin/python
# updateCameraStatus.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# This script is used to manually update a camera status

import datetime,sys

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
if len(sys.argv)>1: cameraId = sys.argv[1]
else              : cameraId = raw_input('Select cameraId to update <default %s>: '%defaultCameraId)
if not cameraId: cameraId = defaultCameraId

cameraStatus = fdb_handle.get_camera_status(camera_id=cameraId)

if not cameraStatus:
  cameraStatus = mp.CameraStatus( "VF-DCD-AI-3.5-18-C-2MP" , "watec_902h2_ultimate" , "https://meteorpi.cambridgesciencecentre.org" , cameraId , mp.Orientation( 0,0,360,0,0 ), mp.Location( LATITUDE_DEFAULT , LONGITUDE_DEFAULT , False ), cameraId )

# Offer user option to update sensor
if len(sys.argv)>2: sensor = sys.argv[2]
else              : sensor = raw_input('Set new sensor <default %s>: '%cameraStatus.sensor)
if sensor: cameraStatus.sensor=sensor

# Offer user option to update lens
if len(sys.argv)>3: lens = sys.argv[3]
else              : lens = raw_input('Set new lens <default %s>: '%cameraStatus.lens)
if lens: cameraStatus.lens=lens

# Apply to historical data?
if len(sys.argv)>4: backdate = sys.argv[4]
else              : backdate   = raw_input('Apply to all historical data? (Y/N) ')
valid_from = None
if backdate in 'Yy': valid_from=datetime.datetime.fromtimestamp(0)

fdb_handle.update_camera_status(cameraStatus, time=valid_from, camera_id=cameraId)

