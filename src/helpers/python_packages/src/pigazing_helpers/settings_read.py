# -*- coding: utf-8 -*-
# settings_read.py
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

import os
import re
import sys

from .vendor import xmltodict

# Fetch path to local installation settings
our_path = os.path.abspath(__file__)
root_path = re.match(r"(.*/src/)", our_path).group(1)
if not os.path.exists(os.path.join(root_path, "../configuration_local/installation_settings.conf")):
    sys.stderr.write(
        "You must create a file <configuration_local/installation_settings.conf> with local camera settings.\n")
    sys.exit(1)

# Read the local installation information from <configuration_local/installation_settings.conf>
installation_info = {}
for line in open(os.path.join(root_path, "../configuration_local/installation_settings.conf")):
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

# Read the list of known observatories from <configuration_global/known_observatories.xml>
known_observatories = {}
path = os.path.join(root_path, "../configuration_global/known_observatories.xml")

observatories = xmltodict.parse(open(path, "rb"))['observatories']['observatory']
if not type(observatories) in (list, tuple):
    observatories = [observatories]

for observatory in observatories:
    obs_id = observatory['observatoryId']

    # Ensure that numerical fields are stored as floats
    for key in ('latitude', 'longitude'):
        observatory[key] = float(observatory[key])

    # Build dictionary of known observatories by ID
    known_observatories[obs_id] = observatory

# The settings below control how the observatory controller works
data_directory = os.path.join(root_path, "../datadir")

settings = {
    'softwareVersion': 3,

    # The user account user by the Pi Gazing observing code
    'pigazingUser': 'system',

    # The path to python scripts in the src directory
    'pythonPath': root_path,

    # The path to compiled binary executables in the videoAnalysis directory
    'binaryPath': os.path.join(root_path, "observe/video_analysis/bin"),
    'imageProcessorPath': os.path.join(root_path, "helpers/image_processing/bin"),

    # Flag telling us whether we're a raspberry pi or a desktop PC
    'i_am_a_rpi': os.uname()[4].startswith("arm"),

    # The directory where we expect to find images and video files
    'dataPath': data_directory,

    # The directory where pigazing_db stores its files
    'dbFilestore': os.path.join(data_directory, "db_filestore"),

    # Flag specifying whether to hunt for meteors in real time, or record H264 video for subsequent analysis
    'realTime': installation_info['realTime'],

    # Flag specifying whether to produce debugging output from C code
    'debug': installation_info['debug'],

    # How far below the horizon do we require the Sun to be before we start observing?
    'sunRequiredAngleBelowHorizon': installation_info['sunRequiredAngleBelowHorizon'],

    # How many seconds before/after sun is above horizon do we wait before bothering observing
    'sunMargin': installation_info['sunMargin'],  # 30 minutes

    # When observing with non-real-time triggering, this is the maximum number of seconds of video allowed
    # in a single file
    'videoMaxRecordTime': installation_info['videoMaxRecordTime'],

    # Video settings.
    'videoDev': installation_info['videoDev'],
}

# Check to make sure everything is going to work
assert os.path.exists(settings['binaryPath']), \
    "You need to compile the src/observing C code before using this script"
assert os.path.exists(settings['imageProcessorPath']), \
    "You need to compile the src/image_projection C code before using this script"

assert os.path.exists(settings['dataPath']), (
    "You need to create a directory or symlink 'datadir' in the root of your Pi Gazing working copy, "
    "where we store all recorded data")
