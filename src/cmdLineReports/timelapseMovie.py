#!/usr/bin/python
# timelapseMovie.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# Make a histogram of number raw videos and trigger videos by hour

import os,time,sys,glob,datetime,operator
from math import *

from mod_settings import *
from mod_time import *

import meteorpi_model as mp
import meteorpi_fdb

pid = os.getpid()
os.chdir(DATA_PATH)

utcMin   = 0
utcMax   = time.time()
cameraId = meteorpi_fdb.get_installation_id()
label    = ""

if len(sys.argv)>1: utcMin   = float(sys.argv[1])
if len(sys.argv)>2: utcMax   = float(sys.argv[2])
if len(sys.argv)>3: cameraId =       sys.argv[3]
if len(sys.argv)>4: label    =       sys.argv[4]

if (utcMax==0): utcMax = time.time()

fdb_handle = meteorpi_fdb.MeteorDatabase( DBPATH , FDBFILESTORE )

search = mp.FileRecordSearch(camera_ids=[cameraId],semantic_type=mp.NSString("timelapse/frame/lensCorr"),exclude_events=True,before=UTC2datetime(utcMax),after=UTC2datetime(utcMin))
files  = fdb_handle.search_files(search)
files  = [i for i in files['files']]
files.sort(key=lambda x: x.file_time)

filestub="/tmp/frame_%d_%%08d.jpg"%pid

useEveryNthImage=2

imgNo=1
count=1
for f in files:
  count+=1
  if not (count%useEveryNthImage==0): continue
  utc = datetime2UTC(f.file_time)
  os.system("""convert %s -gravity SouthEast -fill ForestGreen -pointsize 20 -font Ubuntu-Bold -annotate +16+10 '%s %s' %s"""%(f.get_path(), label, time.strftime("%d %b %Y %H:%M", time.gmtime(utc)), filestub%imgNo))
  imgNo+=1

os.system("""avconv -r 40 -i %s -codec:v libx264 /tmp/timelapse.mp4"""%filestub)

