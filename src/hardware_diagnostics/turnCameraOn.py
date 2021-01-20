#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# turnCameraOn.py
#
# -------------------------------------------------
# Copyright 2015-2021 Dominic Ford
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
Run this python script to manually turn the camera in an observatory on.

You shouldn't normally need to do this, as the camera is automatically turned on when the observatory starts
observing each day. However you may want to run this when you are testing the camera.
"""

import logging
import sys

from pigazing_helpers.relay_control import camera_on

logging.basicConfig(level=logging.INFO,
                    stream=sys.stdout,
                    format='[%(asctime)s] %(levelname)s:%(filename)s:%(message)s',
                    datefmt='%d/%m/%Y %H:%M:%S')
logger = logging.getLogger(__name__)
logger.info(__doc__.strip())

camera_on()
