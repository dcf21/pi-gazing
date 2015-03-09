#!/usr/bin/python
# align_regularise.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# Take the output of align_gnomonic and regularise assuming that camera is pointing at a constant alt/az

import sys,os,re,subprocess
from math import *

from lib_astro import *

def sgn(x):
  if x<0: return -1
  if x>0: return  1
  return 0

inConfig = sys.argv[1]
lines    = open(inConfig).readlines()

cwd = os.getcwd()
pid = os.getpid()

sort_on_utc = lambda a,b: int(sgn(a[11]-b[11]))

outLines      = []
rejectedFiles = []
fits          = []

prevRA = -1000 ; prevDec = -1000 ; prevPa = -1000 ; imgList = []

for line in lines:
  if line.startswith("# Cannot read"):
    filename=line[38:].strip()
    utc=ImageTime(filename)
    rejectedFiles.append( [filename,utc] )
    continue
  if line.startswith("# ADD"):
    filename=line.split()[2]
    utc=ImageTime(filename)
    rejectedFiles.append( [filename,utc] )
    continue
  elif not line.startswith("ADD"):
    outLines.append(line)
    continue
  [add, filename, weight, expcomp, sizex, sizey, ra, dec, pa, scalex, scaley] = line.split()
  utc = ImageTime(filename)
  if (abs(prevRA-float(ra))>0.5)or(abs(prevDec-float(dec))>5)or(abs(prevPa-float(pa))>5):
    if imgList:
      fits.append(imgList)
      reasons=[]
      if (abs(prevRA-float(ra))>0.5): reasons.append("RAs do not match")
      if (abs(prevDec-float(dec))>5): reasons.append("Decs do not match")
      if (abs(prevPa-float(pa))>5): reasons.append("PAs do not match")
      print "# Splitting on <%s>; because %s."%(os.path.split(filename)[1],", ".join(reasons))
    imgList=[]
  prevRA=float(ra) ; prevDec=float(dec) ; prevPa=float(pa)
  imgList.append( [add, filename, float(weight), float(expcomp), float(sizex), float(sizey), float(ra), float(dec), float(pa), float(scalex), float(scaley), utc] )
if imgList: fits.append(imgList)

for imgList in fits:
 meandecl   = sum( [x[ 7] for x in imgList] ) / len(imgList)
 meanpa     = sum( [x[ 8] for x in imgList] ) / len(imgList)
 meanscalex = sum( [x[ 9] for x in imgList] ) / len(imgList)
 meanscaley = sum( [x[10] for x in imgList] ) / len(imgList)

 # Work out mean RA / UTC offset
 p=[0,0]
 for x in imgList:
   theta = x[6]*pi/12 - x[11]/(23.9344696*3600)*(2*pi)
   p[0]+= sin(theta)
   p[1]+= cos(theta)
 theta = atan2(p[0],p[1])

 for x in imgList:
   x[ 7] = meandecl
   x[ 8] = meanpa
   x[ 9] = meanscalex
   x[10] = meanscaley
   x[ 6] = ((theta + x[11]/(23.9344696*3600)*(2*pi))/pi*12 ) % 24

 imgList.sort(sort_on_utc)
 for x in rejectedFiles:
   if (x[1]>imgList[0][11])and(x[1]<imgList[-1][11]):
     ra = ((theta + x[1]/(23.9344696*3600)*(2*pi))/pi*12 ) % 24
     [sizex,sizey] = ImageDimensions(filename)
     imgList.append( ["ADD",x[0],1,1,sizex,sizey,ra,meandecl,meanpa,meanscalex,meanscaley,x[1]] )
     imgList.sort(sort_on_utc)

for line in outLines: print line.strip()

for i in range(len(fits)):
 for j in range(len(fits[i])):
  [add, filename, weight, expcomp, sizex, sizey, ra, dec, pa, scalex, scaley, utc] = fits[i][j]
  # Filename, weight, expcomp, Central RA, Central Dec, position angle, scalex, scaley
  print "ADD %-82s %4.1f %4.1f %4d %4d %10.5f %10.5f %10.5f %10.5f %10.5f"%(filename, weight, expcomp, sizex, sizey, ra, dec, pa, scalex, scaley)

