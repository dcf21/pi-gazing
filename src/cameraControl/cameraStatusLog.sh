#!/bin/bash
# cameraStatusLog.py

cd /home/pi/meteor-pi/src/cameraControl/
echo -e "\n\n# Disk usage"
df

echo -e "\n\n# File checksums"
find -type f -exec md5sum "{}" +

echo -e "\n\n# Log messages"
tail -n 1000 ../../datadir/meteorPi.log 

echo -e "\n\n# Python errors"
tail -n 1000 ../../datadir/python.log

