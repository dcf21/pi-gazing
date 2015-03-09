# module_relay.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import os,time
import RPi.GPIO as GPIO

from module_log import logTxt,getUTC

def cameraOn():
 logTxt("Turning camera on.")
 GPIO.setmode(GPIO.BOARD)
 GPIO.setup(10, GPIO.OUT)
 GPIO.output(10 ,False)

def cameraOff():
 logTxt("Turning camera off.")
 GPIO.setmode(GPIO.BOARD)
 GPIO.setup(10, GPIO.OUT)
 GPIO.output(10 ,True)

