# -*- coding: utf-8 -*-
# sunset_times.py
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

from math import pi, sin, cos, asin, atan, atan2, floor, hypot, sqrt, isnan

from .dcf_ast import sidereal_time
from .vector_algebra import Vector

deg = pi / 180


# Return the [RA, Dec] of the Sun at a given Unix time. See Jean Meeus, Astronomical Algorithms, pp 163-4
def sun_pos(utc):
    """
    Calculate an estimate of the J2000.0 RA and Decl of the Sun at a particular Unix time
    :param utc:
        Unix time
    :type utc:
        float
    :return:
        [RA, Dec] in [hours, degrees]
    """

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

    return ra, dec


def rs_riseculmgap(decl_obj, latitude_obs, angle_below_horizon):
    """
    Estimate the number of seconds between an object rising and culminating at a given declination.

    :param decl_obj:
        The declination of the object, radians
    :type decl_obj:
        float
    :param latitude_obs:
        The latitude of the observer, radians
    :type latitude_obs:
        float
    :param angle_below_horizon:
        How far below the horizon does the centre of this object has to be before it "sets"? (radians)
    :type angle_below_horizon:
        float
    :return:
        The number of seconds between this object rising and culminating
    """
    angle_below_horizon = -angle_below_horizon
    z = sin(decl_obj)
    alpha = (pi / 2 - latitude_obs)
    sin_obj = (z - sin(angle_below_horizon) * cos(alpha)) / (cos(angle_below_horizon) * sin(alpha))
    cos_obj = sqrt(1 - pow(sin_obj, 2))
    b = atan2(cos_obj * cos(angle_below_horizon),
              (sin_obj * cos(angle_below_horizon) * cos(alpha) - sin(angle_below_horizon) * sin(alpha)))

    # Return -1 if requested declination is circumpolar or below horizon
    if isnan(b):
        return -1

    # Return number of second between rising and culmination time.
    # Each day, object is above horizon for 2x time period.
    return 3600 * 12 * (1 - abs(b / pi))


# Returns the UTC times for the rising, culmination and setting of an astronomical object at position [RA,Dec]
def rs_time_s(unix_time, ra, dec, longitude, latitude, angle_below_horizon):
    """
    Estimate the UTC times for the rising, culmination and setting of an astronomical object at position [RA,Dec].

    :param unix_time:
        Any unix time on the day when we should calculate rising and setting times.
    :param ra:
        The right ascension of the object, hours.
    :param dec:
        The declination of the object, degrees
    :param longitude:
        The longitude of the observer, degrees
    :param latitude:
        The latitude of the observer, degrees
    :param angle_below_horizon:
        How far below the horizon does the centre of this object has to be before it "sets"? (radians)
    :type angle_below_horizon:
        float
    :return:
        Unix times for [rising, culminating, setting]
    """

    # calculate unix time of preceding midnight
    unix_time = floor(unix_time / 3600 / 24) * 3600 * 24

    utc_min = unix_time - 3600 * 24 * 0.75
    r = []
    for i in range(48):
        u = utc_min + i * 3600
        r.append([u, sidereal_time(u)])

    lhr = longitude / 180 * 12
    gap = rs_riseculmgap(decl_obj=dec * pi / 180,
                         latitude_obs=latitude * pi / 180,
                         angle_below_horizon=angle_below_horizon * pi / 180)
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


def sun_times(unix_time, longitude=0.12, latitude=52.2, angle_below_horizon=-0.5):
    """
    Estimate unix times for sunrise , sun culmination and sunset.

    :param unix_time:
        Any unix time on the day when we should calculate rising and setting times.
    :param longitude:
        The longitude of the observer, degrees
    :param latitude:
        The latitude of the observer, degrees
    :param angle_below_horizon:
        How far below the horizon does the centre of this object has to be before it "sets"? (radians)
    :type angle_below_horizon:
        float
    :return:
        Unix times for [rising, culminating, setting]
    """

    s = sun_pos(utc=unix_time)

    r = rs_time_s(unix_time=unix_time,
                  ra=s[0], dec=s[1],
                  longitude=longitude, latitude=latitude,
                  angle_below_horizon=angle_below_horizon)

    return r


def alt_az(ra, dec, utc, latitude, longitude):
    """
    Converts [RA, Dec] into local [altitude, azimuth]

    :param ra:
        The right ascension of the object, hours.
    :param dec:
        The declination of the object, degrees
    :param longitude:
        The longitude of the observer, degrees
    :param latitude:
        The latitude of the observer, degrees
    :param utc:
        The unix time of the observation
    :return:
        The [altitude, azimuth] of the object in degrees
    """
    ra *= pi / 12
    dec *= pi / 180
    st = sidereal_time(utc=utc) * pi / 12 + longitude * pi / 180
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

    # [altitude, azimuth] of object in degrees
    return [alt * 180 / pi, az * 180 / pi]


def ra_dec(alt, az, utc, latitude, longitude):
    """
    Converts local [altitude, azimuth] into [RA, Dec]

    :param alt:
        The altitude of the object, degrees
    :param az:
        The azimuth of the object, degrees
    :param utc:
        The unix time of the observation
    :param longitude:
        The longitude of the observer, degrees
    :param latitude:
        The latitude of the observer, degrees
    :return:
        The [RA, Dec] of the object, in hours and degrees
    """
    alt *= pi / 180
    az *= pi / 180
    st = sidereal_time(utc=utc) * pi / 12 + longitude * pi / 180
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


def mean_angle(angle_list):
    """
    Find the centroid (average) of a list of angles. This is well behaved at 0/360 degree wrap-around.
    Input and output are radians.

    :param angle_list:
        List of input angles, in radians
    :type angle_list:
        list, tuple
    :return:
        The [mean, standard deviation] of the input angles, in radians
    """
    xlist = [sin(a) for a in angle_list]  # Project angles onto a circle
    ylist = [cos(a) for a in angle_list]
    xmean = sum(xlist) / len(angle_list)  # Find centroid
    ymean = sum(ylist) / len(angle_list)
    amean = atan2(xmean, ymean)  # Find angle of centroid from centre
    sd = sqrt(sum([hypot(xlist[i] - xmean, ylist[i] - ymean) ** 2 for i in range(len(xlist))]))
    asd = atan(sd)  # Find angular spread of points as seen from centre

    # Return [Mean,SD] in radians
    return [amean, asd]


def mean_angle_2d(pos_list):
    """
    Find the centroid (average) of a list of a positions on a sphere. This is well behaved at 0/360 degree wrap-around.
    Input and output are radians.

    :param pos_list:
        A list of the input positions, each specified as [latitude, longitude], in radians
    :type pos_list:
        list, tuple
    :return:
        The [mean, standard deviation] of the positions. Both are specified as [latitude, longitude], in radians.
    """
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


def get_zenith_position(latitude, longitude, utc):
    """
    Calculate the right ascension and declination of the zenith
    :param longitude:
        The longitude of the observer, degrees
    :param latitude:
        The latitude of the observer, degrees
    :param utc:
        The unix time of the observation
    :return:
        The [RA, Dec] of the zenith in [hour, degrees]
    """

    st = sidereal_time(utc) * pi / 12
    latitude *= pi / 180
    longitude *= pi / 180
    x = cos(longitude + st) * cos(latitude)
    y = sin(longitude + st) * cos(latitude)
    z = sin(latitude)
    v = Vector(x, y, z)
    return v.to_ra_dec()
