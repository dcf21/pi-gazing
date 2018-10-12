# -*- coding: utf-8 -*-
# settings_read.py
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

import os
import installation_info

path = os.path.split(os.path.abspath(__file__))[0]
data_path = os.path.join(path, "../../datadir")

# The settings below control how the observatory controller works
settings = {

    'softwareVersion': 2,

    # The user account user by the Meteor Pi observing code
    'meteorpiUser': 'system',

    # The path to python scripts in the observatoryControl directory
    'pythonPath': path,

    # The path to compiled binary executables in the videoAnalysis directory
    'binaryPath': os.path.join(path, "../observatoryControl/videoAnalysis/bin"),
    'stackerPath': os.path.join(path, "../imageProjection/bin"),

    # Flag telling us whether we're a raspberry pi or a desktop PC
    'i_am_a_rpi': os.uname()[4].startswith("arm"),

    # The directory where we expect to find images and video files
    'dataPath': data_path,

    # The directory where meteorpi_db stores its files
    'dbFilestore': os.path.join(data_path, "db_filestore"),

    # Flag telling us whether to hunt for meteors in real time, or record H264 video for subsequent analysis
    'realTime': True,

    # How many seconds before/after sun is above horizon do we wait before bothering observing
    'sunMargin': 1800,  # 30 minutes

    # When observing with non-real-time triggering, this is the maximum number of seconds of video allowed
    # in a single file
    'videoMaxRecordTime': 7200,

    # Position to assume when we don't have any GPS data available
    'longitudeDefault': installation_info.local_conf['longitude'],
    'latitudeDefault': installation_info.local_conf['latitude'],

    # Video settings. THESE SHOULD BE READ FROM THE DATABASE!
    'videoDev': "/dev/video0",

}

# Checks to make sure everything is going to work
assert os.path.exists(settings['binaryPath']),\
    "You need to compile the videoAnalysis C code before using this script"
assert os.path.exists(settings['stackerPath']),\
    "You need to compile the imageProjection C code before using this script"

assert os.path.exists(settings['dataPath']), (
    "You need to create a symlink 'datadir' in the root of your meteor-pi working copy, "
    "where we store all recorded data")
