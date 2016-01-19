# mod_gnomonic.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import datetime
import os
import subprocess
import time
from math import pi, sin, cos, atan2


def position_angle(lng1, lat1, lng2, lat2):
    lat1 *= pi / 180
    lat2 *= pi / 180
    lng1 *= pi / 12
    lng2 *= pi / 12
    y = sin(lng2 - lng1) * cos(lat2)
    x = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(lng2 - lng1)
    bearing = atan2(y, x)
    return bearing


def image_time(fname):
    os.environ['TZ'] = 'UTC'
    time.tzset()

    fs = os.path.split(fname)[1]
    if len(fs) > 14:
        date_in = [fs[0:4], fs[4:6], fs[6:8], fs[8:10], fs[10:12], fs[12:14]]
        if False not in [x.isdigit() for x in date_in]:
            date_in = [int(x) for x in date_in]
            t = datetime.datetime(date_in[0], date_in[1], date_in[2], date_in[3], date_in[4], date_in[5])
            return float(t.strftime("%s"))

    pid = os.getpid()
    os.system("identify -verbose %s | grep exif:DateTime: > /tmp/it_%d" % (fname, pid))
    image_time = open("/tmp/it_%d" % pid).read()
    os.system("rm -f /tmp/it_%d" % pid)
    words = image_time.split()
    if len(words) < 3:
        return 0
    date_in = [int(i) for i in words[-2].split(":")]
    time_in = [int(i) for i in words[-1].split(":")]

    t = datetime.datetime(date_in[0], date_in[1], date_in[2], time_in[0], time_in[1], time_in[2])
    return float(t.strftime("%s"))


def image_dimensions(file_path):
    d = subprocess.check_output(["identify", file_path]).split()[2].split("x")
    d = [int(i) for i in d]
    return d
