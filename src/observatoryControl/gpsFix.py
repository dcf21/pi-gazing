#!../../virtual-env/bin/python
# gpsFix.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# This script attempts to connect to a USB GPS dongle, if we have one. It uses gpsd, which needs to be installed. The
# python module of the same name (gpsd) is used to communicate with gpsd, but since this isn't widely available in
# a standard version (it's not in the pip repository, for example), we ship the source for it in the directory gpsd.

# The output from this script, if successful, is a JSON structure with the elements: offset, latitude, longitude.
# The offset is the number of seconds that the second clock is AHEAD of the time measured from GPS

# If no connection is made within 30 seconds, this script gives up and returns "False"

# This script is best run as a stand-alone binary, as GpsPoller isn't stable over long periods. It tends to
# spontaneously quit saying "Connection reset by peer".

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
                self.current_value = self.session.next()
                if ('mode' in self.current_value) and (self.current_value.mode == 3):
                    dt = dateutil.parser.parse(self.current_value['time'])
                    utc = time.mktime(dt.timetuple())
                    self.clock_offset = time.time() - utc
                    self.latitude = self.current_value['lat']
                    self.longitude = self.current_value['lon']
                    self.altitude = self.current_value['alt']
                time.sleep(0.2)  # tune this, you might not get values that quickly
        except StopIteration:
            pass


gpsp = GpsPoller()
gpsp.daemon = True
gpsp.start()


# gpsp now polls every .2 seconds for new data, storing it in self.current_value

def fetchGPSfix():
    tstart = time.time()
    while 1:
        x = gpsp.get_current_value()
        if x and ('mode' in x) and (x.mode == 3):
            return {'offset': -gpsp.clock_offset,
                    'latitude': gpsp.latitude,
                    'longitude': gpsp.longitude,
                    'altitude': gpsp.altitude
                    }
        if (time.time() > tstart + 90):
            return False  # Give up after 90 seconds
        time.sleep(2)


if __name__ == '__main__':
    print json.dumps(fetchGPSfix())
