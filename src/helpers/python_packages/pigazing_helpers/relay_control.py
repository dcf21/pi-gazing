# -*- coding: utf-8 -*-
# relay_control.py
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

import logging

from .settings_read import settings, installation_info


def camera_on():
    """
    Use the Raspberry Pi GPIO outputs to trigger the relay to turn on power to the camera.

    :return:
        None
    """

    logging.info("Turning camera on.")

    if not settings['i_am_a_rpi']:
        logging.info("No work to do as not running on RPi")
        return

    import RPi.GPIO as GPIO

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(int(installation_info['gpioPinRelay']), GPIO.OUT)
    GPIO.output(int(installation_info['gpioPinRelay']),
                int(installation_info['relayOnGPIOState']))


def camera_off():
    """
    Use the Raspberry Pi GPIO outputs to trigger the relay to turn off power to the camera.

    :return:
        None
    """

    logging.info("Turning camera off.")

    if not settings['i_am_a_rpi']:
        logging.info("No work to do as not running on RPi")
        return

    import RPi.GPIO as GPIO

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(int(installation_info['gpioPinRelay']), GPIO.OUT)
    GPIO.output(int(installation_info['gpioPinRelay']),
                int(not installation_info['relayOnGPIOState']))
