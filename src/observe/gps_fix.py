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

import json

from gps3 import gps3


def fetch_gps_fix():
    gps_socket = gps3.GPSDSocket()
    data_stream = gps3.DataStream()
    gps_socket.connect()
    gps_socket.watch()
    for new_data in gps_socket:
        if new_data:
            data_stream.unpack(new_data)
            print('Altitude = ', data_stream.TPV['alt'])
            print('Latitude = ', data_stream.TPV['lat'])
            print('Longitude = ', data_stream.TPV['lon'])
            print('Time = ', data_stream.TPV['time'])


if __name__ == '__main__':
    print(json.dumps(fetch_gps_fix()))
