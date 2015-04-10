#!/usr/bin/python
# main.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import os,time,datetime

import module_astro
import module_relay

from module_log import logTxt,getUTC,getUTCoffset
from module_settings import *

logTxt("Camera controller launched")


os.system("mkdir -p %s"%DATA_PATH)
if (not REAL_TIME): os.system("mkdir -p %s/rawvideo"%DATA_PATH)

# Only do these steps on a raspberry pi
if I_AM_A_RPI:
  logTxt("Waiting for GPS link")
  os.system("killall gpsd ; gpsd /dev/ttyUSB0 -F /var/run/gpsd.sock")
  import module_gps
  [toffset,latitude,longitude] = module_gps.fetchTimeOffset()
  flagGPS = 1
  logTxt("GPS link achieved")
else:
  toffset     = 0
  latitude    = LATITUDE_DEFAULT
  longitude   = LONGITUDE_DEFAULT
  flagGPS     = 0
  logTxt("We are not running on a RPi; so not bothering to try to get GPS link")

logTxt("Longitude = %.2f ; Latitude = %.2f ; Clock offset is %.1f"%(longitude,latitude,toffset))

while True:
  logTxt("Camera controller considering what to do next.")
  timeNow            = getUTC()
  sunTimes           = module_astro.sunTimes(timeNow,longitude,latitude)
  secondsTillSunrise = sunTimes[0] - timeNow
  secondsTillSunset  = sunTimes[2] - timeNow

  if ( (secondsTillSunset < -sunMargin) or (secondsTillSunrise > sunMargin) ):
    if (secondsTillSunrise <   0): secondsTillSunrise += 3600*24 - 300
    secondsTillSunrise -= sunMargin
    if (secondsTillSunrise > 600):
      if (REAL_TIME):
        tstop = timeNow+secondsTillSunrise
        logTxt("Starting observing run until %s (running for %d seconds)."%(datetime.datetime.fromtimestamp(tstop).strftime('%Y-%m-%d %H:%M:%S'),secondsTillSunrise))
        module_relay.cameraOn()
        time.sleep(10)
        logTxt("Camera has been turned on.")
        os.system("%s/debug/observe %d %d %d %s %s %d %d %s %s %s %d %d %s/rawvideo/%s"%(BINARY_PATH,getUTCoffset(),timeNow,tstop,CAMERA_ID,VIDEO_DEV,VIDEO_WIDTH,VIDEO_HEIGHT,VIDEO_FPS,latitude,longitude,flagGPS,VIDEO_UPSIDE_DOWN,DATA_PATH,timekey))
        module_relay.cameraOff()
        logTxt("Camera has been turned off.")
        time.sleep(10)
        continue
      else:
        if (secondsTillSunrise>VIDEO_MAXRECTIME): secondsTillSunrise=VIDEO_MAXRECTIME # Do not record more than an hour of video in one file
        tstop = timeNow+secondsTillSunrise
        logTxt("Starting video recording until %s (running for %d seconds)."%(datetime.datetime.fromtimestamp(tstop).strftime('%Y-%m-%d %H:%M:%S'),secondsTillSunrise))
        module_relay.cameraOn()
        time.sleep(10)
        logTxt("Camera has been turned on.")
        timekey = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')
        os.system("%s/debug/recordH264 %d %d %d %s %s %d %d %s %s %s %d %d %s/rawvideo/%s"%(BINARY_PATH,getUTCoffset(),timeNow,tstop,CAMERA_ID,VIDEO_DEV,VIDEO_WIDTH,VIDEO_HEIGHT,VIDEO_FPS,latitude,longitude,flagGPS,VIDEO_UPSIDE_DOWN,DATA_PATH,timekey))
        module_relay.cameraOff()
        logTxt("Camera has been turned off.")
        time.sleep(10)
        continue

  nextObservingTime = secondsTillSunset + sunMargin
  if (nextObservingTime<0): nextObservingTime += 3600*24 - 300
  if (nextObservingTime > 600) and (REAL_TIME or not I_AM_A_RPI): # Do daytimejobs on a RPi only if we are doing real-time observation
    tstop = timeNow+nextObservingTime
    logTxt("Starting daytime jobs until %s (running for %d seconds)."%(datetime.datetime.fromtimestamp(tstop).strftime('%Y-%m-%d %H:%M:%S'),nextObservingTime))
    os.system("cd %s ; python daytimeJobs.py %d %d"%(PYTHON_PATH,getUTCoffset(),tstop))
  else:
    logTxt("Not quite time to start observing yet, so let's sleep for %d seconds."%nextObservingTime)
    time.sleep(nextObservingTime)
  time.sleep(10)

