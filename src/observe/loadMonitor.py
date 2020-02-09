#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# load_monitor.py
#
# -------------------------------------------------
# Copyright 2015-2020 Dominic Ford
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

from pigazing_helpers.settings_read import settings, installation_info


def load_monitor():
    # Set up GPIO lines as outputs. But only if we're running on a RPi, as otherwise we don't have any lines to
    # configure...
    if settings['i_am_a_rpi']:
        import RPi.GPIO as GPIO
    
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(installation_info['gpioLedA'], GPIO.OUT)
        GPIO.setup(installation_info['gpioLedB'], GPIO.OUT)
        GPIO.setup(installation_info['gpioLedC'], GPIO.OUT)
        GPIO.output(installation_info['gpioLedA'], True)
        GPIO.output(installation_info['gpioLedB'], True)
        GPIO.output(installation_info['gpioLedC'], True)
    
    # Set the two LEDs according to whether x and y are true or false
    def set_leds(x, y):
        if settings['i_am_a_rpi']:
            GPIO.output(installation_info['gpioLedA'], x)
            GPIO.output(installation_info['gpioLedB'], y)
        else:
            print("{:10} {:10}".format(x, y))
    
    # This is the filename of the log file which we watch for changes
    log_filename = os.path.join(settings['dataPath'], "pigazing.log")
    
    # This is the last time that we saw the log file update
    last_log_time = 0
    
    # Pulse the load-indicator LED whenever load_count increases by this amount
    load_divisor = 300
    
    # Main loop
    while True:
        load_count = float(open("/proc/stat").readline().split()[1]) / load_divisor
        led1 = (math.floor(load_count) % 2 == 0)
        if os.path.exists(log_filename):
            last_log_time = os.path.getmtime(log_filename)
        led2 = ((time.time() - last_log_time) < 10)
        set_leds(led1, led2)
        time.sleep(0.25)


if __name__ == "__main__":
    load_monitor()
