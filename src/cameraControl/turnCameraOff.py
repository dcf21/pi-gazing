#!/usr/bin/python
# module_relay.py
# $Id: turnCameraOff.py 1173 2015-02-06 00:08:16Z pyxplot $

import os,time
import RPi.GPIO as GPIO

def cameraOn():
 GPIO.setmode(GPIO.BOARD)
 GPIO.setup(10, GPIO.OUT)
 GPIO.output(10 ,True)

cameraOn()

