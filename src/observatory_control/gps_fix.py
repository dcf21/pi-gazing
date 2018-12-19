#!../../virtualenv/bin/python3
# -*- coding: utf-8 -*-
# gps_fix.py
#
# -------------------------------------------------
# Copyright 2015-2018 Dominic Ford
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
python module of the same name (gpsd) is used to communicate with gpsd, but since this isn't widely available in
a standard version (it's not in the pip repository, for example), we ship the source for it in the directory gpsd.

The output from this script, if successful, is a JSON structure with the elements: offset, latitude, longitude.
The offset is the number of seconds that the second clock is AHEAD of the time measured from GPS

If no connection is made within 30 seconds, this script gives up and returns "False"

This script is best run as a stand-alone binary, as GpsPoller isn't stable over long periods. It tends to
spontaneously quit saying "Connection reset by peer".
"""


import dateutil.parser
import threading
import time
import json

from gpsd.gps import gps, WATCH_ENABLE


class GpsPoller(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.session = gps(mode=WATCH_ENABLE)
        self.current_value = None
        self.clock_offset = None
        self.latitude = None
        self.longitude = None
        self.altitude = None

    def get_current_value(self):
        return self.current_value

    def run(self):
        try:
            while True:
                self.current_value = next(self.session)
                if ('mode' in self.current_value) and (self.current_value.mode == 3):
                    dt = dateutil.parser.parse(self.current_value['time'])
                    utc = time.mktime(dt.timetuple())
                    self.clock_offset = time.time() - utc
                    self.latitude = self.current_value['lat']
                    self.longitude = self.current_value['lon']
                    self.altitude = self.current_value['alt']
        except StopIteration:
            pass


gpsp = GpsPoller()
gpsp.daemon = True
gpsp.start()


# gpsp now polls for new data, storing it in self.current_value

def fetch_gps_fix():
    utc_start = time.time()
    while True:
        x = gpsp.get_current_value()
        if x and ('mode' in x) and (x.mode == 3):
            time.sleep(2)
            if x and ('mode' in x) and (x.mode == 3):
                return {'offset': -gpsp.clock_offset,
                        'latitude': gpsp.latitude,
                        'longitude': gpsp.longitude,
                        'altitude': gpsp.altitude
                        }
        if time.time() > utc_start + 90:
            return False  # Give up after 90 seconds
        time.sleep(2)


if __name__ == '__main__':
    print(json.dumps(fetch_gps_fix()))
