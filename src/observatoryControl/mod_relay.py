# mod_relay.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import RPi.GPIO as GPIO

import installation_info
from mod_log import log_txt


def camera_on():
    log_txt("Turning camera on.")
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(installation_info.local_conf['gpioPinRelay'], GPIO.OUT)
    GPIO.output(installation_info.local_conf['gpioPinRelay'], installation_info.local_conf['relayOnGPIOState'])


def camera_off():
    log_txt("Turning camera off.")
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(installation_info.local_conf['gpioPinRelay'], GPIO.OUT)
    GPIO.output(installation_info.local_conf['gpioPinRelay'], not installation_info.local_conf['relayOnGPIOState'])
