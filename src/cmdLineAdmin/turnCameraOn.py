#!/usr/bin/python
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import os,time
import RPi.GPIO as GPIO

def cameraOn():
 GPIO.setwarnings(False)
 GPIO.setmode(GPIO.BOARD)
 GPIO.setup(12, GPIO.OUT)
 GPIO.output(12 ,False)

cameraOn()

