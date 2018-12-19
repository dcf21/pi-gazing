# -*- coding: utf-8 -*-
# relay_control.py
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

import RPi.GPIO as GPIO

from .settings_read import installation_info


def camera_on(logger):
    """
    Use the Raspberry Pi GPIO outputs to trigger the relay to turn on power to the camera.

    :param logger:
        A logger object.
    :return:
        None
    """

    logger.info("Turning camera on.")
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(installation_info.local_conf['gpioPinRelay'], GPIO.OUT)
    GPIO.output(installation_info.local_conf['gpioPinRelay'], installation_info.local_conf['relayOnGPIOState'])


def camera_off(logger):
    """
    Use the Raspberry Pi GPIO outputs to trigger the relay to turn off power to the camera.

    :param logger:
        A logger object.
    :return:
        None
    """

    logger.info("Turning camera off.")
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(installation_info.local_conf['gpioPinRelay'], GPIO.OUT)
    GPIO.output(installation_info.local_conf['gpioPinRelay'], not installation_info.local_conf['relayOnGPIOState'])

    # Some relays need 5V, and the 3.3V generated by a Pi isn't enough to switch them off.
    # But setting them as an input does the trick...
    GPIO.setup(installation_info.local_conf['gpioPinRelay'], GPIO.IN)
