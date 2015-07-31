#!../../virtual-env/bin/python
# load_monitor.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# This script flashes LEDs to indicate the load of the RPi

import os,time
from math import *
import RPi.GPIO as GPIO

import mod_settings

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(7 , GPIO.OUT)
GPIO.setup(11, GPIO.OUT)
GPIO.output(7 , True)
GPIO.output(11, True)

loadCount   = 0
logFilename = os.path.join(mod_settings.DATA_PATH,"meteorPi.log")
lastLogTime = 0

while 1:
  loadCount += float(open("/proc/loadavg").readline().split(" ")[0]) / 4
  GPIO.output(7, floor(loadCount/4)%2==0)
  if os.path.exists(logFilename): lastLogTime = os.path.getmtime(logFilename)
  if (time.time() - lastLogTime) < 10:
    GPIO.output(11, True)
  else:
    GPIO.output(11, False)
  time.sleep(0.2)

