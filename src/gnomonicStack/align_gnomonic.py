#!/usr/bin/python
# align_gnomonic.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import sys,os,re,subprocess,time
from math import *

from lib_astro import *

def logtxt(x):
  print "# %s"%x
  sys.stderr.write("# [%s] %s\n"%(time.strftime("%a, %d %b %Y %H:%M:%S"),x))

def sgn(x):
  if x<0: return -1
  if x>0: return  1
  return 0

camera = sys.argv[1]
fnames = sys.argv[2:]
fnames.sort()

cwd = os.getcwd()
pid = os.getpid()
tmp = "/tmp/align_gnomonic_%d"%pid
os.system("mkdir %s"%tmp)
os.chdir(tmp)

barrelCorrect = os.path.join(cwd,"bin","barrel");
subtractBinary= os.path.join(cwd,"bin","subtract");
camera        = os.path.join(cwd,camera);

fits = []

count=0
for f in fnames:
  logtxt("Working on <%s>"%f)
  count+=1
  f = os.path.join(cwd,f)
  os.system("rm -f *")
  os.system("%s %s %s tmp2.png"%(barrelCorrect,f,camera)) # Barrel-correct image
  os.system("%s tmp2.png /tmp/average.png tmp3.png"%(subtractBinary))
  os.system("convert tmp3.png -crop 360x240+180+120 +repage tmp.png")
  os.system("timeout 5m solve-field --no-plots --crpix-center --overwrite tmp.png > txt") # Insert --no-plots to speed things up
  # os.system("mv tmp-ngc.png /tmp/frame%04d.png"%count)
  fittxt = open("txt").read()
  test = re.search(r"\(RA H:M:S, Dec D:M:S\) = \(([\d-]*):(\d\d):([\d.]*), [+]?([\d-]*):(\d\d):([\d\.]*)\)",fittxt)
  if not test:
    logtxt("Cannot read central RA and Dec from %s"%f)
    continue
  rasgn = sgn(float(test.group(1)))
  ra    = abs(float(test.group(1))) + float(test.group(2))/60 + float(test.group(3))/3600
  if (rasgn<0): ra*=-1
  decsgn= sgn(float(test.group(4)))
  dec   = abs(float(test.group(4))) + float(test.group(5))/60 + float(test.group(6))/3600
  if (decsgn<0): dec*=-1
  test = re.search(r"up is [+]?([-\d\.]*) degrees (.) of N",fittxt)
  if not test:
    logtxt("Cannot read position angle from %s"%f)
    continue
  posang = float(test.group(1)) + 180 # This 180 degree rotation appears to be a bug in astrometry.net (pos angles relative to south, not north)
  while (posang>180): posang-=360
  if test.group(2)=="W": posang*=-1
  test = re.search(r"Field size: ([\d\.]*) x ([\d\.]*) deg",fittxt)
  if not test:
    logtxt("Cannot read field size from %s"%f)
    continue
  scalex=float(test.group(1))
  scaley=float(test.group(2))
  d = ImageDimensions(f)
  fits.append( [f,ra,dec,posang,scalex,scaley,d] )

i = int(floor(len(fits)/2))

print "SET output /tmp/output.png"
print "SET camera %s"%camera
print "SET latitude 0"
print "SET longitude 0"
print "SET utc %10d"%(ImageTime(fits[i][0]))

# Exposure compensation, xsize, ysize, Central RA, Central Dec, position angle, scalex, scaley
print "%-102s %4.1f %4d %4d %10.5f %10.5f %10.5f %10.5f %10.5f"%("GNOMONIC",1,fits[i][6][0],fits[i][6][1],fits[i][1],fits[i][2],fits[i][3],fits[i][4],fits[i][5])
for i in range(len(fits)):
  d = ImageDimensions(fits[i][0])
  # Filename, weight, exposure compensation, Central RA, Central Dec, position angle, scalex, scaley
  print "ADD %-93s %4.1f %4.1f %4d %4d %10.5f %10.5f %10.5f %10.5f %10.5f"%(fits[i][0],1,1,d[0],d[1],fits[i][1],fits[i][2],fits[i][3],fits[i][4],fits[i][5])

os.system("rm -Rf %s"%tmp)
