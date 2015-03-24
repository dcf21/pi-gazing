# module_hwm.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import os
from module_astro import *

# Read our high water marks
def fetchHWM():
  highWaterMarks = {}
  if os.path.exists("highWaterMark.dat"):
   for line in open("highWaterMark.dat"):
    words   = line.split()
    keyword = words[0]
    utc     = words[1]
    try:
      utc=float(utc)
    except:
      continue
    highWaterMarks[keyword] = utc
  return highWaterMarks

def writeHWM(highWaterMarks):
  f = open("highWaterMark.dat","w")
  for keyword,utc in highWaterMarks.iteritems():
    f.write("%16s %s\n"%(keyword,utc))
  f.close()

# Function for turning filenames into Unix times
def filenameToUTC(f):
  if not f.startswith("20"): return -1;
  f = os.path.split(f)[1]
  year = int(f[ 0: 4])
  mon  = int(f[ 4: 6])
  day  = int(f[ 6: 8])
  hour = int(f[ 8:10])
  minu = int(f[10:12])
  sec  = int(f[12:14])
  return UTCfromJD(JulianDay(year, mon, day, hour, minu, sec))

def fetchDayNameFromFilename(f):
  if not f.startswith("20"): return None;
  utc = filenameToUTC(f)
  utc = utc - 12*3600
  [year,month,day,hour,minu,sec] = InvJulianDay(JDfromUTC(utc))
  return "%04d%02d%02d"%(year,month,day)

