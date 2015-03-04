#!/usr/bin/python
# daytimeJobs.py
# $Id: daytimeJobs.py 1197 2015-02-21 15:17:26Z pyxplot $

import os,time,sys,glob,datetime

import module_log
from module_log import logTxt,getUTC
from module_settings import *

pid = os.getpid()

# User should supply unix time on commandline at which we are to stop work
if len(sys.argv)!=3:
  print "Need to call daytimeJobs.py with clock offset, and an end time to tell it when it needs to quit by."
  sys.exit(1)

utcOffset = float(sys.argv[1])
quitTime  = float(sys.argv[2])
module_log.toffset = utcOffset

logTxt("Running daytimeJobs. Need to quit at %s."%(datetime.datetime.fromtimestamp(quitTime).strftime('%Y-%m-%d %H:%M:%S')))
os.chdir (DATA_PATH)

# Read list of days which have already been processed
finishedDays = []
if os.path.exists("finishedDays.dat"):
 for line in open("finishedDays.dat"):
  finishedDays.append(line.strip())

# Get list of directories
dirList = glob.glob("2???????")
dirList.sort() ; dirList.reverse()
for directory in dirList:
  if directory not in finishedDays:
    logTxt("Now processing directory <%s>."%directory)
    images = glob.glob("%s/*.img"%directory)
    images.sort()
    imagesrgb = glob.glob("%s/*.rgb"%directory)
    imagesrgb.sort()
    videos = glob.glob("%s/*.vid"%directory)
    videos.sort()
    for img in images:
      if quitTime and (getUTC()>quitTime): break
      target = img[:-3]+"jpg"
      if not os.path.exists(target):
        logTxt("    Working on image <%s>."%img)
        os.system("%s/raw2jpeg %s %s"%(BINARY_PATH,img,target))
    for img in imagesrgb:
      if quitTime and (getUTC()>quitTime): break
      target = img[:-3]+"png"
      if not os.path.exists(target+".0"):
        logTxt("    Working on RGB image <%s>."%img)
        os.system("%s/raw2rgbpng %s %s"%(BINARY_PATH,img,target))
    for img in videos:
      if quitTime and (getUTC()>quitTime): break
      target = img[:-3]+"mp4"
      if not os.path.exists(target):
        logTxt("    Working on video <%s>."%img)
        os.system("%s/raw2opm %s %s"%(BINARY_PATH,img,"/tmp/pivid_%s.h264"%pid))
        os.system("avconv -i '%s' -c:v copy -f mp4 '%s'"%("/tmp/pivid_%s.h264"%pid,target))
        os.system("rm -f /tmp/pivid_%s.h264"%pid)
    if quitTime and (getUTC()>quitTime):
      logTxt("Interrupting processing as we've run out of time")
      break
    finishedDays.append(directory)

# Write new list of finished days
f = open("finishedDays.dat","w")
finishedDays.sort()
for i in finishedDays: f.write("%s\n"%i)
f.close()

# Twiddle our thumbs
if quitTime:
  logTxt("Finished daytimeJobs. Now twiddling our thumbs for a bit.")
  timeLeft = quitTime - getUTC()
  if (timeLeft>0): time.sleep(timeLeft)
  logTxt("Finished daytimeJobs and also twiddling thumbs.")

