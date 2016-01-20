# mod_astro.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

from math import *
from exceptions import KeyError

deg = pi / 180


# Return the [RA, Dec] of the Sun at a given Unix time. See Jean Meeus, Astronomical Algorithms, pp 163-4
def sun_pos(utc):

    jd = utc / 86400.0 + 2440587.5

    t = (jd - 2451545.0) / 36525.
    l0 = 280.46646 + 36000.76983 * t + 0.0003032 * t * t
    m = 357.52911 + 35999.05029 * t + 0.0001537 * t * t
    # e = 0.016708634 - 0.000042037 * t - 0.0000001267 * t * t

    c = ((1.914602 - 0.004817 * t - 0.000014 * t * t) * sin(m * deg) +
         (0.019993 - 0.000101 * t) * sin(2 * m * deg) +
         0.000289 * sin(3 * m * deg))

    tl = l0 + c  # true longitude
    # v = m + c  # true anomaly

    epsilon = 23 + 26. / 60 + 21.448 / 3600 + 46.8150 / 3600 * t + 0.00059 / 3600 * t * t + 0.001813 / 3600 * t * t * t

    ra = 12 / pi * atan2(cos(epsilon * deg) * sin(tl * deg), cos(tl * deg))  # hours
    dec = 180 / pi * asin(sin(epsilon * deg) * sin(tl * deg))  # degrees

    return [ra, dec]


# Returns the number of seconds between an object at a given declination rising and culminating
def rs_riseculmgap(decl_obj, latitude_obs, angle_below_horizon):  # all inputs are in radians
    angle_below_horizon = -angle_below_horizon
    z = sin(decl_obj)
    alpha = (pi / 2 - latitude_obs)
    sin_obj = (z - sin(angle_below_horizon) * cos(alpha)) / (cos(angle_below_horizon) * sin(alpha))
    cos_obj = sqrt(1 - pow(sin_obj, 2))
    b = atan2(cos_obj * cos(angle_below_horizon),
              (sin_obj * cos(angle_below_horizon) * cos(alpha) - sin(angle_below_horizon) * sin(alpha)))
    if isnan(b):
        return -1  # Return -1 if requested declination is circumpolar or below horizon
    # Return number of second between rising and culmination time. Each day, object is above horizon for 2x time period.
    return 3600 * 12 * (1 - abs(b / pi))


# Turns a unix time into a sidereal time (in hours, at Greenwich)
def sidereal_time(utc):
    u = utc
    j = 40587.5 + u / 86400.0  # Julian date - 2400000
    t = (j - 51545.0) / 36525.0  # Julian century (no centuries since 2000.0)
    st = ((
              280.46061837 +
              360.98564736629 * (j - 51545.0) +  # See pages 87-88 of Astronomical Algorithms, by Jean Meeus
              0.000387933 * t * t +
              t * t * t / 38710000.0
          ) % 360) * 12 / 180
    return st  # sidereal time, in hours. RA at zenith in Greenwich.


# Returns the UTC times for the rising, culmination and setting of an astronomical object at position [RA,Dec]
def rs_time_s(unixtime, ra, dec, longitude, latitude, angle_below_horizon):
    unixtime = floor(unixtime / 3600 / 24) * 3600 * 24  # midnight

    utc_min = unixtime - 3600 * 24 * 0.75
    r = []
    for i in range(48):
        u = utc_min + i * 3600
        r.append([u, sidereal_time(u)])

    lhr = longitude / 180 * 12
    gap = rs_riseculmgap(dec * pi / 180, latitude * pi / 180, angle_below_horizon * pi / 180)
    rcount = len(r)

    utc_rise = 0
    utc_culm = 0
    utc_set = 0

    for i in range(rcount - 1):
        st0 = r[i][1]
        st1 = r[i + 1][1]
        if st1 < st0:
            st1 += 24
        if ra < (st0 + lhr):
            st0 -= 24
            st1 -= 24
        if ra > (st1 + lhr):
            st0 += 24
            st1 += 24
        tculm = (ra - (st0 + lhr)) / (st1 - st0)
        if (tculm < 0) or (tculm >= 1):
            continue
        tculm = r[i][0] + (r[i + 1][0] - r[i][0]) * tculm
        utc_rise = tculm - gap
        utc_culm = tculm
        utc_set = tculm + gap

    return [utc_rise, utc_culm, utc_set]


# Returns unix times for [sunrise , sun culmination , sunset]
def sun_times(unix_time, longitude=0.12, latitude=52.2):
    s = sun_pos(unix_time)
    r = rs_time_s(unix_time, s[0], s[1], longitude, latitude, -0.5)
    return r


# Converts an RA and Dec into an altitude and an azimuth
# RA should be in hours; all other angles should be in degrees.
def alt_az(ra, dec, utc, latitude, longitude):
    ra *= pi / 12
    dec *= pi / 180
    st = sidereal_time(utc) * pi / 12 + longitude * pi / 180
    xyz = [sin(ra) * cos(dec), -sin(dec),
           cos(ra) * cos(dec)]  # y-axis = north/south pole; z-axis (into screen) = vernal equinox

    # Rotate by hour angle around y-axis
    xyz2 = [0, 0, 0]
    xyz2[0] = xyz[0] * cos(st) - xyz[2] * sin(st)
    xyz2[1] = xyz[1]
    xyz2[2] = xyz[0] * sin(st) + xyz[2] * cos(st)

    # Rotate by latitude around x-axis
    xyz3 = [0, 0, 0]
    t = pi / 2 - latitude * pi / 180
    xyz3[0] = xyz2[0]
    xyz3[1] = xyz2[1] * cos(t) - xyz2[2] * sin(t)
    xyz3[2] = xyz2[1] * sin(t) + xyz2[2] * cos(t)

    alt = -asin(xyz3[1])
    az = atan2(xyz3[0], -xyz3[2])
    return [alt * 180 / pi, az * 180 / pi]  # [altitude, azimuth] of object in degrees


# Returns the Julian Day number of a calendar date (British calendar)
def julian_day(year, month, day, hour, minute, sec):
    last_julian_day = 17520902.0
    first_gregorian_day = 17520914.0
    requested_date = 10000.0 * year + 100 * month + day

    if month <= 2:
        month += 12
        year -= 1

    if requested_date <= last_julian_day:
        b = -2 + ((year + 4716) / 4) - 1179  # Julian calendar
    elif requested_date >= first_gregorian_day:
        b = (year / 400) - (year / 100) + (year / 4)  # Gregorian calendar
    else:
        raise KeyError("The requested date never happened")

    jd = 365.0 * year - 679004.0 + 2400000.5 + b + floor(30.6001 * (month + 1)) + day
    day_fraction = (fabs(hour) + fabs(minute) / 60.0 + fabs(sec) / 3600.0) / 24.0
    return jd + day_fraction


def inv_julian_day(jd):
    day_fraction = (jd + 0.5) - floor(jd + 0.5)
    hour = int(floor(24 * day_fraction))
    minute = int(floor(fmod(1440 * day_fraction, 60)))
    sec = fmod(86400 * day_fraction, 60)

    # Number of whole Julian days. b = Number of centuries since the Council of Nicaea.
    # c = Julian Day number as if century leap years happened.
    a = int(jd + 0.5)
    if a < 2361222.0:
        c = int(a + 1524)  # Julian calendar
    else:
        b = int((a - 1867216.25) / 36524.25)
        c = int(a + b - (b / 4) + 1525)  # Gregorian calendar
    d = int((c - 122.1) / 365.25)  # Number of 365.25 periods, starting the year at the end of February
    e_ = int(365 * d + d / 4)  # Number of days accounted for by these
    f = int((c - e_) / 30.6001)  # Number of 30.6001 days periods (a.k.a. months) in remainder
    day = int(floor(c - e_ - int(30.6001 * f)))
    month = int(floor(f - 1 - 12 * (f >= 14)))
    year = int(floor(d - 4715 - int(month >= 3)))
    return [year, month, day, hour, minute, sec]


def time_print(utc):
    [year, month, day, hour, minute, sec] = inv_julian_day(jd_from_utc(utc))
    return "%04d-%02d-%02d %02d:%02d:%02d" % (year, month, day, hour, minute, sec)


# Returns a UTC timestamp from a Julian Day number
def utc_from_jd(jd):
    return 86400.0 * (jd - 2440587.5)


def jd_from_utc(utc):
    return (utc / 86400.0) + 2440587.5


# Average of multiple angles; well behaved at 0/360 degree wrap-around. Input in radians.
def mean_angle(angle_list):
    xlist = [sin(a) for a in angle_list]  # Project angles onto a circle
    ylist = [cos(a) for a in angle_list]
    xmean = sum(xlist) / len(angle_list)  # Find centroid
    ymean = sum(ylist) / len(angle_list)
    amean = atan2(xmean, ymean)  # Find angle of centroid from centre
    sd = sqrt(sum([hypot(xlist[i] - xmean, ylist[i] - ymean) ** 2 for i in range(len(xlist))]))
    asd = atan(sd)  # Find angular spread of points as seen from centre
    return [amean, asd]  # [Mean,SD] in radians


# Average of multiple polar coordinate positions
def mean_angle_2d(pos_list):
    xlist = [sin(a[1]) * sin(a[0]) for a in pos_list]  # Project angles onto a circle
    ylist = [cos(a[1]) * sin(a[0]) for a in pos_list]
    zlist = [cos(a[0]) for a in pos_list]
    xmean = sum(xlist) / len(pos_list)  # Find centroid
    ymean = sum(ylist) / len(pos_list)
    zmean = sum(zlist) / len(pos_list)
    pmean = [atan2(hypot(xmean, ymean), zmean), atan2(xmean, ymean)]
    sd = sqrt(sum(
            [(xlist[i] - xmean) ** 2 + (ylist[i] - ymean) ** 2 + (zlist[i] - zmean) ** 2 for i in
             range(len(xlist))]) / len(
            pos_list))
    asd = atan(sd)  # Find angular spread of points as seen from centre
    return [pmean, asd]  # [Mean,SD] in radians
