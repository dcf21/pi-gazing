#!/bin/bash
# observe.sh
# Pi Gazing
# Dominic Ford
#
# -------------------------------------------------
# Copyright 2015-2019 Dominic Ford
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


# This script is the main entry point for the observatory control software.
#
# We normally configure Raspberry Pis to run this script from /etc/rc.local on start up
# -------------------------------------------------

# Wait a short while before we do anything. If we're called from rc.local, services like mysql server may not have
# started yet
sleep 10

# Change into the observe directory
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
cd $DIR

# Need this so that all python tools use the right python environment
source ../../datadir/virtualenv/bin/activate

# The script load_monitor.py runs in the background and flashes LEDs connected to the GPIO port to indicate
# system activity
./loadMonitor.py &

# The script main.py actually observes the night sky. We catch any python exceptions which may occur in a log file.
# This script should never exit, so if it does, it's broken. Back off for 5 minutes and try again.

while true
 do
  ./main.py &>> ../../datadir/python.log
  sleep 300
 done
