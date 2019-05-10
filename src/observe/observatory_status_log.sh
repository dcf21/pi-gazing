#!/bin/bash
# observatory_status_log.py
# Pi Gazing
# Dominic Ford

# This script produces a lots of system information, including:
#
# * The amount of disk space available
# * Check sums for all of the Pi Gazing source files
# * A list of recent log messages (the most recent 100 messages)
# * A list of recent python errors (the most recent 100 messages)
#
# These are returned to stdout

# In the daily observing cycle, this script is called once a day, and its output is added to the database. It can be
# used to remotely diagnose problems with the system, assuming it gets uploaded to a remote server along with
# recorded observations.

# Ensure our working directory is the observatoryControl directory
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
cd $DIR

echo -e "\n\n# Disk usage"
df

echo -e "\n\n# File check sums"
find -type f -exec md5sum "{}" +

echo -e "\n\n# Log messages"
tail -n 100 ../../datadir/pigazing.log

echo -e "\n\n# Python errors"
tail -n 100 ../../datadir/python.log

