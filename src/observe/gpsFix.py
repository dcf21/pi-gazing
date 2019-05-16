#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# gps_fix.py
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

"""
This script attempts to connect to a USB GPS dongle, if we have one. It uses gpsd, which needs to be installed. The
python module of the same name (gpsd) is used to communicate with gpsd.

The output from this script, if successful, is a JSON structure with the elements: offset, latitude, longitude.

See <https://pypi.org/project/gps3/>
"""

import os
import json
import dateutil.parser
import time

from gps3 import gps3


def fetch_gps_fix():
    altitude = None
    latitude = None
    longitude = None
    unix_time = None
    clock_offset = None

    gps_socket = gps3.GPSDSocket()
    data_stream = gps3.DataStream()
    gps_socket.connect(host="localhost", port=2947)
    gps_socket.watch(devicepath="/dev/ttyUSB0")
    while True:
        new_data = gps_socket.next(timeout=1)
        if new_data:
            data_stream.unpack(new_data)
            if isinstance(data_stream.TPV['alt'], float):
                altitude = data_stream.TPV['alt']
            if isinstance(data_stream.TPV['lat'], float):
                latitude = data_stream.TPV['lat']
            if isinstance(data_stream.TPV['lon'], float):
                longitude = data_stream.TPV['lon']
            if isinstance(data_stream.TPV['time'], str):
                try:
                    dt = dateutil.parser.parse(data_stream.TPV['time'])
                    unix_time = time.mktime(dt.timetuple())
                    clock_offset = time.time() - unix_time
                except ValueError:
                    pass

        # If we have a complete fix, we can quit
        if altitude is not None and latitude is not None and longitude is not None and unix_time is not None:
            return {
                "time": unix_time,
                "clock_offset": clock_offset,
                "latitude": latitude,
                "longitude": longitude,
                "altitude": altitude
            }


if __name__ == '__main__':
    # On Ubuntu 18.04, gpsd doesn't seem to automatically pick up USB devices
    os.system("service gpsd stop ; killall gpsd ; gpsd /dev/ttyUSB0 -n")

    print(json.dumps(fetch_gps_fix()))
