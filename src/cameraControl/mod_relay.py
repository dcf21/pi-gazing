# mod_relay.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import RPi.GPIO as GPIO

import installation_info
from mod_log import logTxt


def cameraOn():
    logTxt("Turning camera on.")
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(12, GPIO.OUT)
    GPIO.output(12, installation_info.relayOnGPIOState)


def cameraOff():
    logTxt("Turning camera off.")
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(12, GPIO.OUT)
    GPIO.output(12, not installation_info.relayOnGPIOState)
