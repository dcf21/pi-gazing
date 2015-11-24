# mod_hwm.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import os

from mod_astro import *


# File to database
def fileToDB(fname, mustBeFloat=False):
    output = {}
    if (not os.path.exists(fname)):
        return output
    for line in open(fname):
        if line.strip() == "":
            continue
        if line[0] == "#":
            continue
        words = line.split()
        keyword = words[0]
        val = words[1]
        try:
            val = float(val)
        except:
            if (mustBeFloat):
                continue
        output[keyword] = val
    return output


def DBtoFile(fname, db):
    f = open(fname, "w")
    keywords = db.keys()
    keywords.sort()
    for keyword in keywords:
        value = db[keyword]
        f.write("%16s %s\n" % (keyword, value))
    f.close()


# Read our high water marks
def fetchHWM():
    return fileToDB("highWaterMark.dat", True)


def writeHWM(highWaterMarks):
    DBtoFile("highWaterMark.dat", highWaterMarks)


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
