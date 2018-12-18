#!../../virtualenv/bin/python3
# -*- coding: utf-8 -*-
# turn_camera_off.py
#
# -------------------------------------------------
# Copyright 2015-2018 Dominic Ford
#
# This file is part of Meteor Pi.
#
# Meteor Pi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Meteor Pi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Meteor Pi.  If not, see <http://www.gnu.org/licenses/>.
# -------------------------------------------------

"""
Run this python script to manually turn the camera in an observatory off.

You shouldn't normally need to do this, as the camera is automatically turned on when the observatory starts
observing each day. However you may want to run this when you are testing the camera.
"""

from pigazing_helpers.relay_control import camera_off

camera_off()
