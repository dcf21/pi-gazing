# mod_log.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import os
import time

import mod_settings
import mod_astro

pid = os.getpid()

t_offset = 0


def get_utc():
    global t_offset
    return time.time() + t_offset


def get_utc_offset():
    global t_offset
    return t_offset


def set_utc_offset(x):
    global t_offset
    t_offset = x


log_file = open(os.path.join(mod_settings.settings['dataPath'], "meteorPi.log"), "a")


def log_txt(txt):
    output = "[%s py] %s" % (time.strftime("%b %d %Y %H:%M:%S", time.gmtime(get_utc())), txt)
    print output
    log_file.write("%s\n" % output)
    log_file.flush()


# Function for turning filenames into Unix times
def filename_to_utc(f):
    f = os.path.split(f)[1]
    if not f.startswith("20"):
        return -1
    year = int(f[0: 4])
    mon = int(f[4: 6])
    day = int(f[6: 8])
    hour = int(f[8:10])
    minute = int(f[10:12])
    sec = int(f[12:14])
    return mod_astro.utc_from_jd(mod_astro.julian_day(year, mon, day, hour, minute, sec))


def fetch_day_name_from_filename(f):
    f = os.path.split(f)[1]
    if not f.startswith("20"):
        return None
    utc = filename_to_utc(f)
    utc -= 12 * 3600
    [year, month, day, hour, minu, sec] = mod_astro.inv_julian_day(mod_astro.jd_from_utc(utc))
    return "%04d%02d%02d" % (year, month, day)
