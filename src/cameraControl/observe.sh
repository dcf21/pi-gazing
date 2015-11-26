#!/bin/bash
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# Main script to start observing loop

sleep 10 # If we're being called from rc.local, firebird DB may not have started yet
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
cd $DIR
source /home/pi/meteor-pi/virtual-env/bin/activate # Need this so that astrometry.net uses right python environment
./loadMonitor.py &
./main.py &>> /home/pi/meteor-pi/datadir/python.log
