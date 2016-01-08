# mod_log.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import os
import time

import mod_settings

pid = os.getpid()

toffset = 0


def getUTC():
    global toffset
    return time.time() + toffset


def getUTCoffset():
    global toffset
    return toffset


def setUTCoffset(x):
    global toffset
    toffset = x


logfile = open(os.path.join(mod_settings.DATA_PATH, "meteorPi.log"), "a")


def logTxt(txt):
    output = "[%s py] %s" % (time.strftime("%b %d %Y %H:%M:%S", time.gmtime(getUTC())), txt)
    print output
    logfile.write("%s\n" % output)
    logfile.flush()

# Function for turning filenames into Unix times
def filenameToUTC(f):
    f = os.path.split(f)[1]
    if not f.startswith("20"):
        return -1
    year = int(f[0: 4])
    mon = int(f[4: 6])
    day = int(f[6: 8])
    hour = int(f[8:10])
    minu = int(f[10:12])
    sec = int(f[12:14])
    return UTCfromJD(JulianDay(year, mon, day, hour, minu, sec))


def fetchDayNameFromFilename(f):
    f = os.path.split(f)[1]
    if not f.startswith("20"):
        return None
    utc = filenameToUTC(f)
    utc = utc - 12 * 3600
    [year, month, day, hour, minu, sec] = InvJulianDay(JDfromUTC(utc))
    return "%04d%02d%02d" % (year, month, day)
