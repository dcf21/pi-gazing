#!../../virtual-env/bin/python
# triggerRate.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# Make a histogram of number raw videos and trigger videos by hour

import os,time,sys,glob,datetime,operator
from math import *

from mod_settings import *
from mod_time import *

import meteorpi_model as mp
import meteorpi_fdb

# Convert file metadata into a dictionary for easy searching
def getMetaItem(fileRec,key):
  NSkey = mp.NSString(key)
  output = None
  for item in fileRec.meta:
    if item.key==NSkey: output=item.value
  return output

pid = os.getpid()
os.chdir(DATA_PATH)

utcMin   = 0
utcMax   = time.time()
cameraId = mod_settings.my_installation_id()
label    = ""

if len(sys.argv)>1: utcMin   = float(sys.argv[1])
if len(sys.argv)>2: utcMax   = float(sys.argv[2])
if len(sys.argv)>3: cameraId =       sys.argv[3]

if (utcMax==0): utcMax = time.time()

fdb_handle = meteorpi_fdb.MeteorDatabase( DBPATH , FDBFILESTORE )

search = mp.FileRecordSearch(camera_ids=[cameraId],semantic_type=mp.NSString("timelapse/frame/lensCorr"),exclude_events=True,before=UTC2datetime(utcMax),after=UTC2datetime(utcMin))
files  = fdb_handle.search_files(search)
files  = [i for i in files['files']]

search = mp.EventSearch(camera_ids=[cameraId],before=UTC2datetime(utcMax),after=UTC2datetime(utcMin))
events = fdb_handle.search_events(search)
events = [i for i in events['events']]

histogram = {}

for f in files:
  utc = datetime2UTC(f.file_time)
  hour= floor(utc/3600)*3600
  if hour not in histogram: histogram[hour] = { 'events':[] , 'images':[] }
  histogram[hour]['images'].append(f)

for e in events:
  utc = datetime2UTC(e.event_time)
  hour= floor(utc/3600)*3600
  if hour not in histogram: histogram[hour] = { 'events':[] , 'images':[] }
  histogram[hour]['events'].append(f)  

# Find time bounds of data
keys = histogram.keys()
keys.sort()
if len(keys)==0:
  print "No results found for camera <%s>"%cameraId
  sys.exit(0)
utcMin = keys[0]
utcMax = keys[-1]

# Render quick and dirty table
out  = sys.stdout
hour = utcMin
out.write("# %12s %12s %12s %12s %12s\n"%("UTC","N_images","N_events","SkyClarity","SunAltitude"))
while (hour<=utcMax):
  out.write("  %12d "%hour)
  if (hour not in histogram):out.write("%12s %12s %12s %12s\n"%(0,0,0,0))
  else:
    d = histogram[hour]
    sunAlt = "---"
    skyCla = "---"
    if (d['images']):
      sunAlt = sum( getMetaItem(i,'sunAlt') for i in d['images'])/len(d['images'])
      skyCla = sum( getMetaItem(i,'skyClarity') for i in d['images'])/len(d['images'])
    out.write("%12s %12s %12s %12s\n"%(len(d['images']) , len(d['events']) , skyCla , sunAlt ))
  hour+=3600

