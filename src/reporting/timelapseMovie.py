#!/usr/bin/python
# timelapseMovie.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# Make a histogram of number raw videos and trigger videos by hour

import os,time,sys,glob,datetime,operator
from math import *

from module_settings import *
import module_hwm

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

fileList = glob.glob("timelapse_img_processed/*/*_%s_frame_BS0.png"%cameraId)
fileList.sort()

filestub="/tmp/frame_%d_%%08d.jpg"%pid

useEveryNthImage=2

imgNo=1
count=1
for f in fileList:
  count+=1
  if not (count%useEveryNthImage==0): continue
  utc = module_hwm.filenameToUTC(os.path.split(f)[1])
  if (not utc): continue
  if (utc < utcMin): continue
  if (utc > utcMax): continue
  os.system("""convert %s -gravity SouthEast -fill ForestGreen -pointsize 20 -font Ubuntu-Bold -annotate +16+10 '%s %s' %s"""%(f, label, time.strftime("%d %b %Y %H:%M", time.gmtime(utc)), filestub%imgNo))
  imgNo+=1

os.system("""avconv -r 40 -i %s -codec:v libx264 /tmp/timelapse.mp4"""%filestub)

