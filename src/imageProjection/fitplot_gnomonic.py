#!/usr/bin/python
# fitplot_gnomonic.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# Pipe output of align_gnomonic.py into this script

import sys,os,re,subprocess
from math import *

DEG = pi/180

indata = sys.stdin.read()
lines  = indata.split("\n")

output    = "/tmp/output.jpg"
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
  xsize = float(words[3])
  ysize = float(words[4])
  ra    = float(words[5]) # hours
  dec   = float(words[6]) # degs
  pa    = float(words[7]) # pa
  scalex= float(words[8]) # degs; angular size of image
  scaley= float(words[9]) # degs; angular size of image

  lines2.append( [count,fname,weight,expcom,xsize,ysize,ra,dec,pa,scalex,scaley] )
  count+=1

cwd = os.getcwd()
pid = os.getpid()
tmp = "/tmp/fitplot_gnomonic_%d"%pid
os.system("mkdir %s"%tmp)
os.chdir("/tmp") # Just to make sure we don't stay in cwd
os.chdir(tmp)

for [count,fname,weight,expcom,xsize,ysize,ra,dec,pa,scalex,scaley] in lines2:
  print count
  f = open("fitplot.cfg","w")
  f.write("""
MODEL
out_filename=fitplot
PhotoFName=%s
position_angle=%f
ra_central=%f
dec_central=%f
width=20
AngWidth=%f
aspect=%f
"""%(fname,pa,ra,dec,scalex,ysize/xsize))
  f.close()
  os.system("/home/dcf21/svn_repository/StarPlot_ppl8/scripts/Starcharts2/bin/starchart.bin fitplot.cfg")
  os.system("mv output/fitplot.eps %s"%os.path.join(cwd,"%s_%04d.eps"%(output,count)))
  os.system("rm -Rf *")

os.system("rm -Rf %s"%tmp)

