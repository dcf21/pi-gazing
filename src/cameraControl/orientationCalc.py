#!../../pythonenv/bin/python
# orientationCalc.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# Use astrometry.net to calculate the orientation of the camera based on recent images

import os,time,sys,re,glob,datetime,operator,subprocess
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

  deg = pi/180
  rad = 180/pi
  hr  = pi/12

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
  search = mp.FileRecordSearch(camera_ids=[cameraId],semantic_type=mp.NSString("timelapse/frame/bgrdSub/lensCorr"),exclude_events=True,before=UTC2datetime(utcMax),after=UTC2datetime(utcMin),limit=1000000)
  files  = fdb_handle.search_files(search)
  files  = [i for i in files['files']]
  logTxt("%d candidate time-lapse images in past 24 hours"%len(files))

  # Filter out files where the sky clariy is good and the Sun is well below horizon
  acceptableFiles = []
  for f in files:
    if (getMetaItem(f,'skyClarity') < 0.6): continue
    if (getMetaItem(f,'sunAlt')     >  -3): continue
    acceptableFiles.append(f)

  logTxt("%d acceptable images found for alignment"%len(acceptableFiles))

  # If we don't have enough images, we can't proceed to get a secure orientation fit
  if (len(acceptableFiles)<20):
    logTxt("Giving up: not enough suitable images")
    return

  # We can't afford to run astrometry.net on too many images, so pick the 20 best ones
  acceptableFiles.sort(key=lambda f: getMetaItem(f,'skyClarity') )
  acceptableFiles = acceptableFiles[0:20]
  logTxt("Using files with timestamps: %s"%([datetime2UTC(f.file_time) for f in acceptableFiles]))

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
    d = ImageDimensions("tmp.png")
    fractionX = 0.5 # Pass only central 50% of image to astrometry.net. It's not very reliable with wide-field images
    fractionY = 0.5
    os.system("convert tmp.png -crop %dx%d+%d+%d +repage tmp2.png"%( fractionX*d[0] , fractionY*d[1] , (1-fractionX)*d[0]/2 , (1-fractionY)*d[1]/2 ))
    astrometryStartTime = time.time()
    os.system("timeout 5m solve-field --no-plots --crpix-center --overwrite tmp2.png > txt") # Insert --no-plots to speed things up
    astrometryTimeTaken = time.time() - astrometryStartTime
    logTxt("Astrometry.net took %d seconds to analyse image at time <%s>"%(astrometryTimeTaken,f.file_time))
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
    scalex= 2 * atan( tan( float(test.group(1)) / 2 * deg ) * (1/fractionX) ) * rad # Expand size of image to whole image, not just the central tile we sent to astrometry.net
    scaley= 2 * atan( tan( float(test.group(2)) / 2 * deg ) * (1/fractionY) ) * rad
    d = ImageDimensions(fname)
    fits.append( {'f':f,'ra':ra,'dec':dec,'pa':posang,'sx':scalex,'sy':scaley,'dims':d} )

  # Average the resulting fits
  if len(fits)<10:
    logTxt("Giving up: astrometry.net only managed to fit %d images"%len(fits))
    return

  paList     = [ i['pa']*deg for i in fits ] ; paBest     = mod_astro.meanAngle(paList)[0]
  scalexList = [ i['sx']*deg for i in fits ] ; scalexBest = mod_astro.meanAngle(scalex)[0]
  scaleyList = [ i['sy']*deg for i in fits ] ; scaleyBest = mod_astro.meanAngle(scalex)[0]

  altAzList  = [ mod_astro.altAz( i['ra']*hr , i['dec']*deg , datetime2UTC(i['f'].file_time) , cameraStatus.orientation.latitude , cameraStatus.orientation.longitude ) for i in fits ]
  [ altAzBest , altAzError ] = mod_astro.meanAngle2D(altAzList)

  # Print fit information
  logTxt("Orientation fit. Alt: %.2f deg. Az: %.2f deg. PA: %.2f deg. ScaleX: %.2f deg. ScaleY: %.2f deg. Uncertainty: %.2f deg."%(altAzBest[1]*rad,altAzBest[0]*rad,paBest*rad,scalexBest*rad,scaleyBest*rad,altAzError*rad))

  # Update camera status
  cameraStatus.orientation = Orientation( altitude=altAzBest[1]*rad, azimuth=altAzBest[0]*rad, error=altAzError*rad, rotation=paBest*rad, width_of_field=scalexBest*rad )
  # fdb_handle.update_camera_status(cameraStatus, time=UTC2datetime(utcNow), camera_id=cameraId)

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

