#!/bin/bash
# liveView.sh
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# This script is used to produce a live view of what a camera can see, using mplayer

mplayer -tv device=/dev/video0 tv://

