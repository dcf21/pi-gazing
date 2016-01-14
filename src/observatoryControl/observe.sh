#!/bin/bash
# observe.sh
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# This script is the main entry point for the observatory control software.
#
# We normally configure Raspberry Pis to run this script from /etc/rc.local on start up

# Wait a short while before we do anything. If we're called from rc.local, mysql server may not have started yet
sleep 10

# Change into the observatoryControl directory
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
cd $DIR
source ../../virtual-env/bin/activate # Need this so that astrometry.net uses right python environment

# The script loadMonitor.py runs in the background and flashes LEDs connected to the GPIO port to indicate
# system activity
./loadMonitor.py &

# The script main.py actually observes the night sky. We catch any python exceptions which may occur in a log file.
./main.py &>> /home/pi/meteor-pi/datadir/python.log
