# -*- coding: utf-8 -*-
# sunset_times.py
#
# -------------------------------------------------
# Copyright 2015-2018 Dominic Ford
#
# This file is part of Meteor Pi.
#
# Meteor Pi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Meteor Pi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Meteor Pi.  If not, see <http://www.gnu.org/licenses/>.
# -------------------------------------------------

from math import pi, sin, cos, acos, asin, atan, atan2, floor, fmod, fabs, hypot, sqrt, isnan
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
    xyz = [sin(ra) * cos(dec),
           -sin(dec),  # y-axis = towards south pole
           cos(ra) * cos(dec)]  # z-axis = vernal equinox; RA=0

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


# Converts an altitude and azimuth into an RA and Dec
# RA is returned in hours. All other angles should be in degrees.
def ra_dec(alt, az, utc, latitude, longitude):
    alt *= pi / 180
    az *= pi / 180
    st = sidereal_time(utc) * pi / 12 + longitude * pi / 180
    xyz3 = [sin(az) * cos(alt), sin(-alt), -cos(az) * cos(alt)]

    # Rotate by latitude around x-axis
    xyz2 = [0, 0, 0]
    t = pi / 2 - latitude * pi / 180
    xyz2[0] = xyz3[0]
    xyz2[1] = xyz3[1] * cos(t) + xyz3[2] * sin(t)
    xyz2[2] = -xyz3[1] * sin(t) + xyz3[2] * cos(t)

    # Rotate by hour angle around y-axis
    xyz = [0, 0, 0]
    xyz[0] = xyz2[0] * cos(st) + xyz2[2] * sin(st)
    xyz[1] = xyz2[1]
    xyz[2] = -xyz2[0] * sin(st) + xyz2[2] * cos(st)

    dec = -asin(xyz[1])
    ra = atan2(xyz[0], xyz[2])

    while ra < 0:
        ra += 2 * pi
    return [ra * 12 / pi, dec * 180 / pi]

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
            [(xlist[i] - xmean) ** 2 + (ylist[i] - ymean) ** 2 + (zlist[i] - zmean) ** 2
             for i in range(len(xlist))]
    ) / len(pos_list))
    asd = atan(sd)  # Find angular spread of points as seen from centre
    return [pmean, asd]  # [Mean,SD] in radians


# Return the right ascension and declination of the zenith
def get_zenith_position(lat, lng, utc):
    st = sidereal_time(utc) * pi / 12
    lat *= pi / 180
    lng *= pi / 180
    x = cos(lng + st) * cos(lat)
    y = sin(lng + st) * cos(lat)
    z = sin(lat)
    v = Vector(x, y, z)
    return v.to_ra_dec()
