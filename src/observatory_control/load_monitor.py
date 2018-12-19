#!../../virtualenv/bin/python3
# -*- coding: utf-8 -*-
# load_monitor.py
#
# -------------------------------------------------
# Copyright 2015-2018 Dominic Ford
#
# This file is part of Pi Gazing.
#
# Pi Gazing is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pi Gazing is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Pi Gazing.  If not, see <http://www.gnu.org/licenses/>.
# -------------------------------------------------

"""
This script flashes LEDs to indicate the load of the RPi
"""

import os
import time
import math

from pigazing_helpers import settings_read
import installation_info

# Set up GPIO lines as outputs. But only if we're running on a RPi, as otherwise we don't have any lines to configure...
if settings_read.settings['i_am_a_rpi']:
    import RPi.GPIO as GPIO

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(installation_info.local_conf['gpioLedA'], GPIO.OUT)
    GPIO.setup(installation_info.local_conf['gpioLedB'], GPIO.OUT)
    GPIO.setup(installation_info.local_conf['gpioLedC'], GPIO.OUT)
    GPIO.output(installation_info.local_conf['gpioLedA'], True)
    GPIO.output(installation_info.local_conf['gpioLedB'], True)
    GPIO.output(installation_info.local_conf['gpioLedC'], True)


# Set the two LEDs according to whether x and y are true or false
def set_lights(x, y):
    if settings_read.settings['i_am_a_rpi']:
        GPIO.output(installation_info.local_conf['gpioLedA'], x)
        GPIO.output(installation_info.local_conf['gpioLedB'], y)
    else:
        print("%10s %10s" % (x, y))


# This is a sum of all of the load measurements we have ever made
loadCount = 0

# This is the filename of the log file which we watch for changes
logFilename = os.path.join(settings_read.settings['dataPath'], "pigazing.log")

# This is the last time that we saw the log file update
lastLogTime = 0

# Pulse the load-indicator LED whenever loadCount increases by this amount
loadDivisor = 300

# Main loop
while True:
    loadCount = float(open("/proc/stat").readline().split()[1]) / loadDivisor
    led1 = (math.floor(loadCount) % 2 == 0)
    if os.path.exists(logFilename):
        lastLogTime = os.path.getmtime(logFilename)
    led2 = ((time.time() - lastLogTime) < 10)
    set_lights(led1, led2)
    time.sleep(0.25)
