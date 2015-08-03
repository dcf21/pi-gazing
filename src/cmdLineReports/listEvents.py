#!../../virtual-env/bin/python
# listEvents.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import os,time,sys,glob,datetime,operator
from math import *

from mod_settings import *
from mod_time import *
from mod_astro import *

import meteorpi_model as mp
import meteorpi_fdb

pid = os.getpid()
os.chdir(DATA_PATH)

utcMin   = time.time() - 3600*24
utcMax   = time.time()
cameraId = my_installation_id()
label    = ""
imgType  = ""
stride   = 1

if len(sys.argv)>1: utcMin   = float(sys.argv[1])
if len(sys.argv)>2: utcMax   = float(sys.argv[2])
if len(sys.argv)>3: cameraId =       sys.argv[3]
if len(sys.argv)>4: label    =       sys.argv[4]
if len(sys.argv)>5: imgType  =       sys.argv[5]
if len(sys.argv)>6: stride   = int  (sys.argv[6])

if (utcMax==0): utcMax = time.time()

print "# ./listEvents.py %f %f \"%s\" \"%s\" \"%s\" %d\n"%(utcMin,utcMax,cameraId,label,imgType,stride)

fdb_handle = meteorpi_fdb.MeteorDatabase( DBPATH , FDBFILESTORE )

search = mp.EventSearch(camera_ids=[cameraId],before=UTC2datetime(utcMax),after=UTC2datetime(utcMin),limit=1000000)
triggers = fdb_handle.search_events(search)
triggers = triggers['events']
triggers.sort(key=lambda x: x.event_time)

s = fdb_handle.get_camera_status(camera_id=cameraId)
if not s:
  print "Unknown camera <%s>. Run ./listCameras.py to see a list of available cameras."%cameraId
  sys.exit(0)

print "Camera <%s>"%cameraId
print "  * High water mark: %s"%fdb_handle.get_high_water_mark(camera_id=cameraId)
print "  * Software: %s"%s.software_version
print "  * Lens: %s"%s.lens
print "  * Sensor: %s"%s.sensor
print "  * Validity of this status: %s -> %s"%(s.valid_from,s.valid_to)
print "  * Location: %s"%s.location
print "  * Orientation: %s"%s.orientation
print "  * Regions: %s"%s.regions
print "  * %d matching triggers in time range %s --> %s"%(len(triggers),UTC2datetime(utcMin),UTC2datetime(utcMax))
for event in triggers:
    print "  * %s"%event
