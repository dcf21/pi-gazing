#!../../virtual-env/bin/python
# load_monitor.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# This script flashes LEDs to indicate the load of the RPi

import os,time
from math import *

import mod_settings

if mod_settings.I_AM_A_RPI:
  import RPi.GPIO as GPIO
  GPIO.setwarnings(False)
  GPIO.setmode(GPIO.BOARD)
  GPIO.setup(18, GPIO.OUT)
  GPIO.setup(22, GPIO.OUT)
  GPIO.output(18, True)
  GPIO.output(22, True)

def setLights(x,y):
  if mod_settings.I_AM_A_RPI:
    GPIO.output(18,x)
    GPIO.output(22,y)
  else:
    print "%10s %10s"%(x,y)

loadCount   = 0
logFilename = os.path.join(mod_settings.DATA_PATH,"meteorPi.log")
lastLogTime = 0

loadDivisor = 300

while 1:
  loadCount = float(open("/proc/stat").readline().split()[1]) / loadDivisor
  led1 = (floor(loadCount)%2==0)
  if os.path.exists(logFilename): lastLogTime = os.path.getmtime(logFilename)
  led2 = ((time.time() - lastLogTime) < 10)
  setLights(led1,led2)
  time.sleep(0.25)

