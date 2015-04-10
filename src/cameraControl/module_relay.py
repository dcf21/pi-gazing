# module_relay.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import os,time
import RPi.GPIO as GPIO

from module_log import logTxt,getUTC

def cameraOn():
 logTxt("Turning camera on.")
 GPIO.setwarnings(False)
 GPIO.setmode(GPIO.BOARD)
 GPIO.setup(12, GPIO.OUT)
 GPIO.output(12 ,False)

def cameraOff():
 logTxt("Turning camera off.")
 GPIO.setwarnings(False)
 GPIO.setmode(GPIO.BOARD)
 GPIO.setup(12, GPIO.OUT)
 GPIO.output(12 ,True)

