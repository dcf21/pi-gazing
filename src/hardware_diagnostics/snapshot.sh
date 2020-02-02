#!/bin/bash
# snapshot.sh
# Pi Gazing
# Dominic Ford

# This script is used to take a live snapshot of what a camera can see.

# It takes two commandline arguments, e.g.:
# ./snapshot.sh tmp.png 500

if [ -e "/dev/video1" ] ; then
 device="/dev/video1"
else
 device="/dev/video0"
fi

# In this example, the snapshot would be saved to tmp.png, and would be an average of 500 video frames

../observe/video_analysis/bin/snapshot --output $1 --frames $2 --device $device
