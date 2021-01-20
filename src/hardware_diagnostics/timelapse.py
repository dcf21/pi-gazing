#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# timelapse.py
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
This is a demo script which turns the camera on, and then records a time lapse video of frames recorded once a
minute until the script is killed
"""

import logging
import os
import sys
import time
from math import *

logging.basicConfig(level=logging.INFO,
                    stream=sys.stdout,
                    format='[%(asctime)s] %(levelname)s:%(filename)s:%(message)s',
                    datefmt='%d/%m/%Y %H:%M:%S')
logger = logging.getLogger(__name__)
logger.info(__doc__.strip())

frame_interval = 60

pid = os.getpid()

logger.info("timelapse launched")

# Start time for time lapse sequence
time_next_frame = floor((time.time() + 10) / 10) * 10

# Make directory
dirname = "/tmp/pigazing_timelapse"
os.system("mkdir -p {}".format(dirname))
os.chdir(dirname)

frame_num = 1

while True:
    logger.info("Waiting for next exposure")
    wait = time_next_frame - time.time()
    if wait > 0:
        time.sleep(wait)

    # Filename
    filename = "frame{:06d}.jpg".format(frame_num)
    while True:
        if os.path.exists(filename):
            frame_num += 1
            filename = "frame{:06d}.jpg".format(frame_num)
        else:
            break

    # Take exposure
    logger.info("Taking photo")
    os.system("rm -f tmp.jpg")
    os.system("./snapshot.sh --output tmp.png --frames 500")
    os.system("convert tmp.png -background black -rotate -180 tmp2.jpg")
    os.system("convert tmp2.jpg -gravity South -background Green -splice 0x26 -pointsize 16 -font Ubuntu-Bold "
              "-annotate +0+2 '{}' {}".format(time.strftime("%b %d %Y %H:%M:%S", time.gmtime(time.time())),
                                              filename))

    # Use ffmpeg to make a time lapse video. Can't do this inside the loop if we intend to observe for a very
    # long time, as otherwise it takes more than a minute to do this encoding after each frame...
    os.system("rm -f /tmp/pigazing_timelapse.mp4")
    os.system("ffmpeg -r 10 -i frame%06d.jpg -codec:v libx264 /tmp/pigazing_timelapse.mp4")

    time_next_frame += frame_interval
