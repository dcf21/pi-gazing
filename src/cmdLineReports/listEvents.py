#!/usr/bin/python
# listEvents.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import datetime,time,sys

from mod_settings import *
from mod_time import *

import meteorpi_model as mp
import meteorpi_fdb
fdb_handle = meteorpi_fdb.MeteorDatabase( DBPATH , FDBFILESTORE )

tmin=0
tmax=time.time()

argc = len(sys.argv)
if (argc>1): tmin=float(sys.argv[1])
if (argc>2): tmax=float(sys.argv[2])

tmin=UTC2datetime(tmin)
tmax=UTC2datetime(tmax)

cameraList = fdb_handle.get_cameras()
for cameraId in cameraList:
  title = "Camera <%s>"%cameraId
  print "\n\n%s\n%s"%(title,"-"*len(title))
  print "%s\n  * %s\n  * High water mark: %s"%(cameraId,fdb_handle.get_camera_status(camera_id=cameraId),fdb_handle.get_high_water_mark(camera_id=cameraId))
  search = mp.EventSearch(camera_ids=[cameraId],before=tmax,after=tmin)
  triggers = fdb_handle.search_events(search)
  triggers = triggers['events']
  triggers.sort(key=lambda x: x.event_time)
  print "  * %d matching triggers in time range %s --> %s"%(len(triggers),tmin,tmax)
  for event in triggers:
    print "  * %s"%event
