#!/usr/bin/python
# timelapseMovie.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# Make a histogram of number raw videos and trigger videos by hour

import os,time,sys,glob,datetime,operator
from math import *

from module_settings import *
import module_hwm

pid = os.getpid()
os.chdir(DATA_PATH)

fileList = glob.glob("timelapse_img_processed/*/*BS0.png")
fileList.sort()

filestub="/tmp/frame_%d_%%08d.jpg"%pid

imgNo=1
for f in fileList:
  utc = module_hwm.filenameToUTC(os.path.split(f)[1])
  if (not utc): continue
  os.system("""convert %s -gravity SouthEast -fill ForestGreen -pointsize 20 -font Ubuntu-Bold -annotate +16+10 '%s' %s"""%(f, time.strftime("%d %b %Y %H:%M", time.gmtime(utc)), filestub%imgNo))
  imgNo+=1

os.system("""avconv -r 40 -i %s -codec:v libx264 /tmp/timelapse.mp4"""%filestub)

