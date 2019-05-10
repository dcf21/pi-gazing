#!/bin/bash
# snapshot.sh
# Pi Gazing
# Dominic Ford

# This script is used to take a live snapshot of what a camera can see.

# It takes two commandline arguments, e.g.:
# ./snapshot.sh tmp.png 500

# In this example, the snapshot would be saved to tmp.png, and would be an average of 500 video frames

../observing/bin/snapshot --output $1 --frames $2
