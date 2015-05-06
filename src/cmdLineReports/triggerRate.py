#!/usr/bin/python
# triggerRate.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# Make a histogram of number raw videos and trigger videos by hour

import os,time,sys,glob,datetime,operator
from math import *

from mod_settings import *
import mod_hwm

pid = os.getpid()
os.chdir(DATA_PATH)

fileList                = {}
fileList['rawVideos']   = glob.glob("rawvideo/*.h264")
fileList['triggerVids'] = glob.glob("triggers_raw_nonlive/*/*.rawvid")
histogram               = {}

utcMin = time.time()
utcMax = 0

for histogramTitle in fileList:
  histogram[histogramTitle] = {}
  for f in fileList[histogramTitle]:
    utc = mod_hwm.filenameToUTC(f)
    if (utc<0): continue
    hour= floor(utc/3600)*3600
    if (hour<utcMin): utcMin=hour
    if (hour>utcMax): utcMax=hour
    if hour not in histogram[histogramTitle]: histogram[histogramTitle][hour] =1
    else                                    : histogram[histogramTitle][hour]+=1

# Render quick and dirty table
out  = sys.stdout
hour = utcMin
out.write("# UTC   ")
for histogramTitle in histogram: out.write("N_%s   "%histogramTitle)
out.write("\n")
while (hour<=utcMax):
  out.write("%10d   "%hour)
  for histogramTitle in histogram:
    if hour in histogram[histogramTitle]: count=histogram[histogramTitle][hour]
    else                                : count=0
    out.write("%6d   "%count)
  out.write("\n")
  hour+=3600

