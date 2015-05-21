#!/usr/bin/python
# animate_alignment.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# Take the output of align_gnomonic and animate how the frames are aligned

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

outLines  = []
fits      = []
frNum     = 0
for line in lines:
  if not line.startswith("ADD"):
    outLines.append(line)
    continue
  fits.append(line)

groupSize=12
nImg=len(fits)
nGrp=int(floor(nImg/groupSize))

for i in range(nGrp):
  o = open("/tmp/animate_align.cfg","w")
  for line in outLines: o.write("%s\n"%(line.strip()))
  for j in range(i*groupSize,(i+1)*groupSize):
    img=fits[j]
    o.write("%s\n"%(img))

  os.system("./bin/stack /tmp/animate_align.cfg")

  # Draw an arrow to label a point
  xarr = 768 ; yarr = 544
  os.system("""arrow_head="path 'M 0,0  l -15,-5  +5,+5  -5,+5  +15,-5 z'" ; convert /tmp/output.png -stroke red -fill red -strokewidth 3 -draw "line %s,%s %s,%s" -draw "translate %s,%s rotate -90 scale 1.4,1.4 $arrow_head" /tmp/output2.png ; mv /tmp/output2.png /tmp/output.png"""%(xarr,yarr+80,xarr,yarr,xarr,yarr))

  os.system("mv /tmp/output.png /tmp/animate_align_fr%06d.png"%frNum)
  frNum+=1

