#!/usr/bin/python
# orientationCalc.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# Use astrometry.net to calculate the orientation of the camera based on recent images

import os,time,sys,re,glob,datetime,operator
from math import *

from mod_settings import *
from mod_time import *
from mod_log import logTxt,getUTC

import meteorpi_model as mp
import meteorpi_fdb

# Return the dimensions of an image
def ImageDimensions(f):
  d = subprocess.check_output(["identify", f]).split()[2].split("x") ; d = [int(i) for i in d]
  return d

# Return the sign of a number
def sgn(x):
  if x<0: return -1
  if x>0: return  1
  return 0

# Convert file metadata into a dictionary for easy searching
def getMetaItem(fileRec,key):
  NSkey = mp.NSString(key)
  output = None
  for item in fileRec.meta:
    if item.key==NSkey: output=item.value
  return output

pid = os.getpid()
os.chdir(DATA_PATH)


def orientationCalc(cameraId,utcNow,utcMustStop=0):
  logTxt("Starting calculation of camera alignment")

  # Path the binaries in <gnomonicStack>
  barrelCorrect = os.path.join(STACKER_PATH,"barrel");

  # Calculate time span to use images from
  utcMax   = utcNow
  utcMin   = utcMax - 3600*24
  fdb_handle = meteorpi_fdb.MeteorDatabase( DBPATH , FDBFILESTORE )

  # Fetch camera status
  cameraStatus = fdb_handle.get_camera_status(camera_id=cameraId,time=UTC2datetime(utcNow))
  lensName = cameraStatus.lens

  # Search for background-subtracted timelapse photography within this range
  search = mp.FileRecordSearch(camera_ids=[cameraId],semantic_type=mp.NSString("timelapse/frame/bgrdSub/lensCorr"),exclude_events=True,before=UTC2datetime(utcMax),after=UTC2datetime(utcMin))
  files  = fdb_handle.search_files(search)

  # Filter out files where the sky clariy is good and the Sun is well below horizon
  acceptableFiles = []
  for f in files:
    if (getMetaItem(f,'skyClarity') < 0.6): continue
    if (getMetaItem(f,'sunAlt')     > -10): continue
    acceptableFiles.append(f)

  logTxt("%d acceptable images found for alignment"%len(acceptableFiles))

  # If we don't have enough images, we can't proceed to get a secure orientation fit
  if (len(acceptableFiles)<20):
    logTxt("Giving up: not enough suitable images")
    return

  # We can't afford to run astrometry.net on too many images, so pick the 20 best ones
  acceptableFiles.sort(key=lambda f: getMetaItem(f,'skyClarity') )
  acceptableFiles = acceptableFiles[0:20]
  logTxt("Using files with timestamps: %s"%([f.file_time for f in acceptableFiles]))

  # Make a temporary directory to store files in. This is necessary as astrometry.net spams the cwd with lots of temporary junk
  cwd = os.getcwd()
  pid = os.getpid()
  tmp = "/tmp/dcf21_orientationCalc_%d"%pid
  os.system("mkdir %s"%tmp)
  os.chdir(tmp)

  # Loop over selected images and use astrometry.net to find their orientation
  fits = []
  for f in acceptableFiles:
    fname = f.get_path()
    os.system("%s %s %s tmp.png"%(barrelCorrect,fname,os.path.join(STACKER_PATH,"../cameras",lensName))) # Barrel-correct image
    os.system("convert tmp.png -crop 360x240+180+120 +repage tmp2.png")
    os.system("timeout 5m solve-field --no-plots --crpix-center --overwrite tmp2.png > txt") # Insert --no-plots to speed things up
    fittxt = open("txt").read()
    test = re.search(r"\(RA H:M:S, Dec D:M:S\) = \(([\d-]*):(\d\d):([\d.]*), [+]?([\d-]*):(\d\d):([\d\.]*)\)",fittxt)
    if not test:
      logTxt("Cannot read central RA and Dec from image at <%s>"%f.file_time)
      continue
    rasgn = sgn(float(test.group(1)))
    ra    = abs(float(test.group(1))) + float(test.group(2))/60 + float(test.group(3))/3600
    if (rasgn<0): ra*=-1
    decsgn= sgn(float(test.group(4)))
    dec   = abs(float(test.group(4))) + float(test.group(5))/60 + float(test.group(6))/3600
    if (decsgn<0): dec*=-1
    test = re.search(r"up is [+]?([-\d\.]*) degrees (.) of N",fittxt)
    if not test:
      logTxt("Cannot read position angle from image at <%s>"%f.file_time)
      continue
    posang = float(test.group(1)) + 180 # This 180 degree rotation appears to be a bug in astrometry.net (pos angles relative to south, not north)
    while (posang>180): posang-=360
    if test.group(2)=="W": posang*=-1
    test = re.search(r"Field size: ([\d\.]*) x ([\d\.]*) deg",fittxt)
    if not test:
      logTxt("Cannot read field size from image at <%s>"%f.file_time)
      continue
    scalex=float(test.group(1))
    scaley=float(test.group(2))
    d = ImageDimensions(fname)
    fits.append( [f,ra,dec,posang,scalex,scaley,d] )

  # Print fit information
  logTxt(fits)

  # Clean up and exit
  os.chdir(cwd)
  os.system("rm -Rf %s"%tmp)
  return

# If we're called as a script, run the method orientationCalc()
if __name__ == "__main__":
  cameraId = meteorpi_fdb.get_installation_id()
  utcNow   = time.time()
  if len(sys.argv)>1: cameraId = sys.argv[1]
  if len(sys.argv)>2: utcNow   = float(sys.argv[2])
  orientationCalc(cameraId,utcNow,0)

