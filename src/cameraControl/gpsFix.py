#!../../virtual-env/bin/python
# gpsFix.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

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
        self.clockoffset = None
        self.latitude = None
        self.longitude = None

    def get_current_value(self):
        return self.current_value

    def run(self):
        try:
            while True:
                self.current_value = self.session.next()
                if ('mode' in self.current_value) and (self.current_value.mode == 3):
                    dt = dateutil.parser.parse(self.current_value['time'])
                    utc = time.mktime(dt.timetuple())
                    self.clockoffset = time.time() - utc
                    self.latitude = self.current_value['lat']
                    self.longitude = self.current_value['lon']
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
            return {'offset':-gpsp.clockoffset, 'latitude':gpsp.latitude, 'longitude':gpsp.longitude}
        if (time.time() > tstart + 30):
            return False  # Give up after 30 seconds
        time.sleep(2)


if __name__ == '__main__':
    print json.dumps(fetchGPSfix())
