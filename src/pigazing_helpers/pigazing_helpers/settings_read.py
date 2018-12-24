# -*- coding: utf-8 -*-
# settings_read.py
#
# -------------------------------------------------
# Copyright 2015-2019 Dominic Ford
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

import os
import re
import sys

# Fetch path to local installation settings
our_path = os.path.abspath(os.getcwd())
root_path = re.match(r"(.*/src)", our_path).group(1) + "/"
if not os.path.exists(os.path.join(root_path, "../configuration/installation_settings.conf")):
    sys.stderr.write(
        "You must create a file <configuration/installation_settings.conf> with local camera settings.\n")
    sys.exit(1)

installation_info = {}
for line in open(os.path.join(root_path, "../configuration/installation_settings.conf")):
    line = line.strip()

    # Ignore blank lines and comment lines
    if len(line) == 0 or line[0] == '#':
        continue

    # Remove any comments from the ends of lines
    if '#' in line:
        line = line.split('#')[0]

    # Split this configuration parameter into the setting name, and the setting value
    words = line.split(':')
    value = words[1].strip()

    # Try and convert the value of this setting to a float
    try:
        value = float(value)
    except ValueError:
        pass

    installation_info[words[0].strip()] = value

# The settings below control how the observatory controller works
data_directory = os.path.join(root_path, "../datadir")

settings = {

    'softwareVersion': 3,

    # The user account user by the Pi Gazing observing code
    'pigazingUser': 'system',

    # The path to python scripts in the src directory
    'pythonPath': root_path,

    # The path to compiled binary executables in the videoAnalysis directory
    'binaryPath': os.path.join(root_path, "observing/bin"),
    'stackerPath': os.path.join(root_path, "image_projection/bin"),

    # Flag telling us whether we're a raspberry pi or a desktop PC
    'i_am_a_rpi': os.uname()[4].startswith("arm"),

    # The directory where we expect to find images and video files
    'dataPath': data_directory,

    # The directory where pigazing_db stores its files
    'dbFilestore': os.path.join(data_directory, "db_filestore"),

    # Flag telling us whether to hunt for meteors in real time, or record H264 video for subsequent analysis
    'realTime': True,

    # How many seconds before/after sun is above horizon do we wait before bothering observing
    'sunMargin': 1800,  # 30 minutes

    # When observing with non-real-time triggering, this is the maximum number of seconds of video allowed
    # in a single file
    'videoMaxRecordTime': 7200,

    # Position to assume when we don't have any GPS data available
    'longitudeDefault': installation_info['longitude'],
    'latitudeDefault': installation_info['latitude'],

    # Video settings. THESE SHOULD BE READ FROM THE DATABASE!
    'videoDev': "/dev/video0",

}

# Check to make sure everything is going to work
assert os.path.exists(settings['binaryPath']), \
    "You need to compile the src/observing C code before using this script"
assert os.path.exists(settings['stackerPath']), \
    "You need to compile the src/image_projection C code before using this script"

assert os.path.exists(settings['dataPath']), (
    "You need to create a directory or symlink 'datadir' in the root of your Pi Gazing working copy, "
    "where we store all recorded data")
