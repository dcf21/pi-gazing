#!/usr/bin/python
# align_null.py
# Dominic Ford
# $Id: align_null.py 1127 2014-11-03 22:06:29Z pyxplot $

import sys,subprocess
from math import *

fnames = sys.argv[1:]
fnames.sort()

fits = []
for f in fnames:
 d = subprocess.check_output(["identify", f]).split()[2].split("x") ; d = [int(i) for i in d]
 fits.append( [f,d] )

i = int(floor(len(fits)/2))

print "SET output /tmp/output.jpg"
print "SET camera cameras/null"

print "%-91s %4.1f %4d %4d %4d %4d %5.2f"%("FLAT",1,fits[i][1][0],fits[i][1][1],0,0,0) # Exposure compensation, x size, y size, x shift, y shift, rotation
for f in fits:
  print "ADD %-82s %4.1f %4.1f %9s %4d %4d %4d %4d %5.2f"%(f[0],1,1,"",f[1][0],f[1][1],0,0,0) # Filename, weight, exposure compensation, x size, y size, x shift, y shift, rotation

