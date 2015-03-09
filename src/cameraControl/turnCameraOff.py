#!/usr/bin/python
# module_relay.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import os,time
import RPi.GPIO as GPIO

def cameraOn():
 GPIO.setmode(GPIO.BOARD)
 GPIO.setup(10, GPIO.OUT)
 GPIO.output(10 ,True)

cameraOn()

