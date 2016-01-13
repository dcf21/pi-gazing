#!/usr/bin/python
# fitinfo_gnomonic.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# Pipe output of align_gnomonic.py into this script

import sys,os,re,subprocess
from math import *

from lib_astro import *

DEG = pi/180

indata = sys.stdin.read()
lines  = indata.split("\n")

output    = "/tmp/output.png"
metadata  = {}
out_xsize = 1
out_ysize = 1
out_ra    = 0
out_dec   = 0
out_pa    = 0
out_scalex= 45
out_scaley= 45

count  = 1
lines2 = []
for line in lines:
 line=line.strip()
 if len(line)==0: continue
 if line[0]=="#": continue
 words = line.split()
 if words[0]=="OUTPUT":
   output=words[1]
 elif words[0]=="SET":
   metadata[words[1]] = float(words[2])
 elif words[0]=="FLAT":
   assert False, "Cannot use this script on flat stacking configuration scripts"
 elif words[0]=="GNOMONIC":
  out_xsize = float(words[1])
  out_ysize = float(words[2])
  out_ra    = float(words[3]) # hours
  out_dec   = float(words[4]) # degs
  out_pa    = float(words[5]) # pa
  out_scalex= float(words[6]) # degs; angular size of image
  out_scaley= float(words[7]) # degs; angular size of image
 else:
  fname = words[0]
  weight= float(words[1])
  expcom= float(words[2])
  ra    = float(words[3]) # hours
  dec   = float(words[4]) # degs
  pa    = float(words[5]) # pa
  scalex= float(words[6]) # degs; angular size of image
  scaley= float(words[7]) # degs; angular size of image

  lines2.append( [count,fname,weight,expcom,ra,dec,pa,scalex,scaley] )
  count+=1

print "# %-72s %10s %9s %7s %7s"%("FILENAME","UTC","SIDEREAL","ALT","AZ")

for [count,fname,weight,expcom,ra,dec,pa,scalex,scaley] in lines2:
  # print count
  bestLng=0 ; bestOffset=999
  lng=0
  while (lng<360):
   pa2    = positionAngle(ra,dec  ,  lng*12./180,metadata["latitude"])*180/pi
   offset = abs(pa - pa2) % 360
   if (offset>180): offset = 360-offset
   # print "%9.4f %9.4f %9.4f %9.4f %9.4f %9.4f %9.4f %9.4f"%(ra,dec,lng*12./180,metadata["latitude"],pa,pa2,offset,bestOffset)
   if (offset<bestOffset):
     bestOffset=offset
     bestLng   =lng
   lng+=0.01
  siderealTimeImg = (( bestLng - metadata["longitude"] + 5*360 ) % 360) / 180*12; # Hours

  utcBest= 0
  utcBestOffset= 999
  utcmin = metadata["utc"] - 12*3600
  utcmax = metadata["utc"] + 12*3600
  utc    = utcmin
  while (utc<utcmax):
    st = siderealTime(utc)
    off= abs(st - siderealTimeImg) % 24
    if (off>12): off=24-off
    if (off<utcBestOffset):
     utcBestOffset = off
     utcBest       = utc
    utc+=1

  [alt,az] = altAz(ra,dec,utcBest,metadata["latitude"],metadata["longitude"])

  print "%-74s %10d %9.4f %7.2f %7.2f"%(fname,utcBest,siderealTimeImg,alt,az)

