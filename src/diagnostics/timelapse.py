#!../../virtual-env/bin/python
# timelapse.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# This is a demo script which turns the camera on, and then records a time lapse video of frames recorded once a
# minute until the script is killed

from __future__ import division

import os
import time
from math import *

frame_interval = 60

logfile = open("log.txt", "a")


def utc():
    return time.time()


def logtxt(txt):
    logfile.write("[%s] %s\n" % (time.strftime("%b %d %Y %H:%M:%S", time.gmtime(utc())), txt))
    logfile.flush()


pid = os.getpid()

logtxt("timelapse launched")

# Start time for time lapse sequence
time_next_frame = floor((utc() + 10) / 10) * 10

# Make directory
dirname = "/tmp/meteorpi_timelapse"
os.system("mkdir -p %s" % dirname)
os.chdir(dirname)

frame_num = 1

while True:
    logtxt("Waiting for next exposure")
    wait = time_next_frame - utc()
    if wait > 0:
        time.sleep(wait)

    # Filename
    fname = "frame%06d.jpg" % (frame_num)
    while True:
        if os.path.exists(fname):
            frame_num += 1
            fname = "frame%06d.jpg" % (frame_num)
        else:
            break

    # Take exposure
    logtxt("Taking photo")
    os.system("rm -f tmp.jpg")
    os.system("./snapshot.sh tmp.png 500")
    os.system("convert tmp.png -background black -rotate -180 tmp2.jpg")
    os.system("convert tmp2.jpg -gravity South -background Green -splice 0x26 -pointsize 16 -font Ubuntu-Bold "
              "-annotate +0+2 '%s' %s" % (time.strftime("%b %d %Y %H:%M:%S", time.gmtime(utc())), fname))

    # Use avconv to make a timelapse video. Can't do this inside the loop if we intend to observe for a very
    # long time, as otherwise it takes more than a minute to do this encoding after each frame...
    os.system("rm -f /tmp/meteorpi_timelapse.mp4")
    os.system("avconv -r 10 -i frame%06d.jpg -codec:v libx264 /tmp/meteorpi_timelapse.mp4")

    time_next_frame += frame_interval
