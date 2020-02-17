#!/bin/bash
# liveView.sh
# Pi Gazing
# Dominic Ford

# This script is used to produce a live view of what a camera can see, using mplayer

mplayer -vo sdl -tv device=/dev/video0 tv://

