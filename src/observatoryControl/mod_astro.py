# mod_astro.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

from math import *
from exceptions import KeyError
import scipy.optimize

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


# Converts an altitude and azimuth into an RA and Dec
# RA is returned in hours. All other angles should be in degrees.
def ra_dec(alt, az, utc, latitude, longitude):
    alt *= pi / 180
    az *= pi / 180
    st = sidereal_time(utc) * pi / 12 + longitude * pi / 180
    xyz3 = [sin(az) * cos(alt), cos(az) * cos(alt), sin(-alt)]

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


# Functions for dealing with planes and lines

class Point:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def __str__(self):
        return "Point(%s,%s,%s)" % (self.x, self.y, self.z)

    def to_vector(self):
        return Vector(self.x, self.y, self.z)

    def add_vector(self, other):
        """
        Add a Vector to this point
        :param Vector other:
        :return Point:
        """
        return Point(self.x + other.x, self.y + other.y, self.z + other.z)

    def displacement_vector_from(self, other):
        """
        Returns the Vector displacement of self from other.
        :param Point other:
        :return Vector:
        """
        return Vector(self.x - other.x, self.y - other.y, self.z - other.z)

    def displacement_from_origin(self):
        """
        Returns the vector displacement of this Point from the origin.
        :return Vector:
        """
        return Vector(self.x, self.y, self.z)

    def __abs__(self):
        """
        Returns the distance of this point from the origin
        :return float:
        """
        return sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    @staticmethod
    def from_lat_lng(lat, lng, utc):
        lat *= pi / 180
        lng *= pi / 180
        st = sidereal_time(utc) * pi / 12
        r_earth = 6371e3
        x = r_earth * sin(lng + st) * cos(lat)
        y = r_earth * cos(lng + st) * cos(lat)
        z = r_earth * sin(lat)
        return Point(x, y, z)

    def to_lat_lng(self, utc):
        mag = abs(self)
        deg = 180 / pi
        st = sidereal_time(utc) * pi / 12
        r_earth = 6371e3
        lat = asin(self.z / mag) * deg
        lng = (atan2(self.x, self.y) - st) * deg
        lng = fmod(lng, 360)
        while lng < 0:
            lng += 360
        return {'lat': lat, 'lng': lng, 'alt': mag - r_earth}


class Vector:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def __str__(self):
        return "Vector(%s,%s,%s)" % (self.x, self.y, self.z)

    def __add__(self, other):
        """
        Add two Vectors together.
        :param Vector other:
        :return Vector:
        """
        return Vector(self.x + other.x, self.y + other.y, self.z + other.z)

    def __radd__(self, other):
        """
        Add two Vectors together.
        :param Vector other:
        :return Vector:
        """
        return Vector(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        """
        Subtract another Vector from this one.
        :param Vector other:
        :return Vector:
        """
        return Vector(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, other):
        """
        Multiply this Vector by a scalar
        :param float other:
        :return Vector:
        """
        return Vector(self.x * other, self.y * other, self.z * other)

    def __imul__(self, other):
        """
        Multiply this Vector by a scalar
        :param float other:
        :return Vector:
        """
        return Vector(self.x * other, self.y * other, self.z * other)

    def __div__(self, other):
        """
        Divide this Vector by a scalar
        :param float other:
        :return Vector:
        """
        return Vector(self.x / other, self.y / other, self.z / other)

    def __abs__(self):
        """
        Returns the magnitude (i.e. length) of this Vector.
        :return float:
        """
        return sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    @staticmethod
    def from_ra_dec(ra, dec):
        """
        Converts an (RA, Dec) pair into a unit vector.
        :param float ra: Right ascension / hours
        :param float dec: Declination / degrees
        :return:
        """
        ra *= pi / 12
        dec *= pi / 180
        x = sin(ra) * cos(dec)
        y = cos(ra) * cos(dec)
        z = sin(dec)
        return Vector(x, y, z)

    def to_ra_dec(self):
        """
        Converts a vector into an (RA, Dec) direction.
        :return Dict:
        """
        mag = abs(self)
        dec = asin(self.z / mag)
        ra = atan2(self.x, self.y)
        ra *= 12 / pi
        dec *= 180 / pi
        while ra < 0:
            ra += 24
        while ra >= 24:
            ra -= 24
        return {'ra': ra, 'dec': dec}

    def cross_product(self, other):
        """
        Returns the cross product of two vectors.
        :param Vector other:
        :return Vector:
        """
        x_out = self.y * other.z - self.z * other.y
        y_out = self.z * other.x - self.x * other.z
        z_out = self.x * other.y - self.y * other.x
        return Vector(x_out, y_out, z_out)

    def dot_product(self, other):
        """
        Rteurns the dot product of two Vectors.
        :param Vector other:
        :return float:
        """
        return self.x * other.x + self.y * other.y + self.z * other.z


class Line:
    def __init__(self, x0, direction):
        """
        Equation of a line, in the form x = x0 + i*direction
        :param Point x0:
        :param Vector direction:
        :return:
        """
        self.x0 = x0
        self.direction = direction

    def __str__(self):
        return "Line( x0=Point(%s,%s,%s), direction=Vector(%s,%s,%s))" % (self.x0.x, self.x0.y, self.x0.z,
                                                                          self.direction.x, self.direction.y,
                                                                          self.direction.z)

    def point(self, i):
        """
        Returns a point on the line.
        :param float i:
        :return Point:
        """
        return self.x0.add_vector(self.direction * i)

    def to_plane(self, other):
        """
        Returns the plane containing this line and another direction vector.
        :param Vector other:
        :return Plane:
        """
        normal = self.direction.cross_product(other)
        p = -normal.dot_product(self.x0.displacement_from_origin())
        return Plane(normal=normal, p=p)

    def find_intersection(self, other):
        """
        Find the point of intersection between two lines. This is over-constrained, so we find intersection in (x,y)
        plane
        :param Line other:
        :return Point:
        """

        # d = self.direction
        # d2 = other.direction
        # p = self.x0
        # p2 = other.x0
        # j = (d.y * p.x - d.x * p.y - d.y * p2.x + d.x * p2.y) / (d2.x * d.y - d2.y * d.x)
        # return other.point(j)

        def mismatch_slave(parameters):
            [i, j] = parameters
            return abs(self.point(i).displacement_vector_from(other.point(j)))

        params_initial = [0, 0]
        params_optimised = scipy.optimize.minimize(mismatch_slave, params_initial, method='nelder-mead',
                                                   options={'xtol': 1e-7, 'disp': False, 'maxiter': 1e5, 'maxfev': 1e5}
                                                   ).x
        from mod_log import log_txt
        log_txt("Finding intersection: residual was %s" % mismatch_slave(params_optimised))
        return self.point(params_optimised[0])

    @staticmethod
    def average_from_list(lines):
        """
        Return the weighted average of a set of lines
        :param list[list] lines: List of [Line, weighting]
        :return:
        """
        if len(lines) < 1:
            return None
        origin = Point(0, 0, 0)
        x0_sum = Vector(0, 0, 0)
        weight_sum = 0
        direction_sum = Vector(0, 0, 0)
        for item in lines:
            [line, weight] = item
            x0_sum += line.x0.to_vector() * weight
            direction_sum += line.direction * weight
            weight_sum += weight
        return Line(x0=origin.add_vector(x0_sum / weight_sum),
                    direction=direction_sum / weight_sum)


class Plane:
    def __init__(self, normal, p):
        """
        Equation of a plane, in the form n.x+p = 0
        :param Vector normal:
        :param float p:
        :return:
        """
        self.normal = normal
        self.p = p

    def __str__(self):
        return "Plane( normal=Vector(%s,%s,%s), p=%s)" % (self.normal.x, self.normal.y, self.normal.z, self.p)

    def perpendicular_distance_to_point(self, other):
        """
        Calculate the perpendicular distance of a point from a place
        :param Point other:
        :return:
        """
        return self.normal.dot_product(other.displacement_from_origin()) + self.p

    def line_of_intersection(self, other):
        """
        Find the line of intersection between two planes
        :param Plane other:
        :return Line:
        """
        direction = self.normal.cross_product(other.normal)
        mag = abs(direction)

        # Normalise direction vector
        if mag > 0:
            direction = direction / mag

        n = self.normal
        n2 = other.normal
        p = self.p
        p2 = other.p

        # Now find a sample point which is in both planes
        try:
            z = 0
            y = (n.x * p2 - n2.x * p) / (n2.x * n.y - n.x * n2.y)
            x = (n.y * p2 - n2.y * p) / (n2.y * n.x - n.y * n2.x)
        except ZeroDivisionError:
            return None

        x0 = Point(x, y, z)
        return Line(direction=direction, x0=x0)
