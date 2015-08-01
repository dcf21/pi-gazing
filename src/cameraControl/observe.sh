#!/bin/bash
# Script to start observing
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

sleep 10 # If we're being called from rc.local, firebird DB may not have started yet
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
cd $DIR
./loadMonitor.py &
./main.py
