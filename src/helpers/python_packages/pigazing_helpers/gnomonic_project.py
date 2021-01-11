# -*- coding: utf-8 -*-
# gnomonic_project.py
#
# -------------------------------------------------
# Copyright 2015-2020 Dominic Ford
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

from math import sin, cos, tan, pi, asin, atan, atan2, sqrt, fabs, hypot
import scipy.optimize


def rotate_xy(a, theta):
    """
    Rotate a three-component vector about the z axis

    :param a:
        Vector to rotate (list or tuple of three items)
    :param theta:
        The angle to rotate around the z axis (radians)
    :return:
        Rotated vector
    """

    a0 = a[0] * cos(theta) + a[1] * -sin(theta)
    a1 = a[0] * sin(theta) + a[1] * cos(theta)
    a2 = a[2]
    return [a0, a1, a2]


def rotate_xz(a, theta):
    """
    Rotate a three-component vector about the y axis

    :param a:
        Vector to rotate (list or tuple of three items)
    :param theta:
        The angle to rotate around the y axis (radians)
    :return:
        Rotated vector
    """

    a0 = a[0] * cos(theta) + a[2] * -sin(theta)
    a1 = a[1]
    a2 = a[0] * sin(theta) + a[2] * cos(theta)
    return [a0, a1, a2]


def position_angle(ra1, dec1, ra2, dec2):
    """
    Return the position angle of the great circle path from (RA1, Dec1) to (RA2, Dec2), as seen at the former point

    :param ra1:
        The right ascension of the first point (degrees)
    :param dec1:
        The declination of the first point (hours)
    :param ra2:
        The right ascension of the second point (degrees)
    :param dec2:
        The declination of the second point (hours)
    :return:
        The position angle (degrees)
    """

    dec1 *= pi / 180
    dec2 *= pi / 180
    ra1 *= pi / 12
    ra2 *= pi / 12
    x = cos(ra2) * cos(dec2)
    y = sin(ra2) * cos(dec2)
    z = sin(dec2)
    a = [x, y, z]
    a = rotate_xy(a, -ra1)
    a = rotate_xz(a, pi / 2 - dec1)
    azimuth = atan2(a[1], -a[0])
    return azimuth * 180 / pi


def make_zenithal(ra, dec, ra0, dec0):
    """
    Convert a position on the sky into alt/az coordinates

    :param ra:
        The right ascension of the point to convert (radians)
    :param dec:
        The declination of the point to convert (radians)
    :param ra0:
        The right ascension of the zenith (radians)
    :param dec0:
        The declination of the zenith (radians)
    :return:
        List of the zenith angle and azimuth of the point
    """

    x = cos(ra) * cos(dec)
    y = sin(ra) * cos(dec)
    z = sin(dec)
    a = [x, y, z]
    a = rotate_xy(a, -ra0)
    a = rotate_xz(a, pi / 2 - dec0)
    if a[2] > 0.999999999:
        a[2] = 1.0
    if a[2] < -0.999999999:
        a[2] = -1.0
    altitude = asin(a[2])
    if fabs(cos(altitude)) < 1e-7:
        azimuth = 0.0  # Ignore azimuth at pole!
    else:
        azimuth = atan2(a[1] / cos(altitude), a[0] / cos(altitude))
    zenith_angle = pi / 2 - altitude

    za = zenith_angle
    az = azimuth
    return [za, az]


def ang_dist(ra0, dec0, ra1, dec1):
    """
    Calculate the angular distance between two points on the sky

    :param ra0:
        The right ascension of the first point (radians)
    :param dec0:
        The declination of the first point (radians)
    :param ra1:
        The right ascension of the second point (radians)
    :param dec1:
        The declination of the second point (radians)
    :return:
        The angular separation (radians)
    """

    x0 = cos(ra0) * cos(dec0)
    y0 = sin(ra0) * cos(dec0)
    z0 = sin(dec0)
    x1 = cos(ra1) * cos(dec1)
    y1 = sin(ra1) * cos(dec1)
    z1 = sin(dec1)
    d = sqrt(pow(x0 - x1, 2) + pow(y0 - y1, 2) + pow(z0 - z1, 2))
    return 2 * asin(d / 2)


def find_mean_position(ra0, dec0, ra1, dec1, ra2, dec2):
    """
    Return the average of three points on the sky

    :param ra0:
        The right ascension of the first point (radians)
    :param dec0:
        The declination of the first point (radians)
    :param ra1:
        The right ascension of the second point (radians)
    :param dec1:
        The declination of the second point (radians)
    :param ra2:
        The right ascension of the third point (radians)
    :param dec2:
        The declination of the third point (radians)
    :return:
        The RA and Dec of the midpoint of the three points on the sky
    """

    # Convert the first point from spherical polar coordinates to Cartesian coordinates
    x0 = cos(ra0) * cos(dec0)
    y0 = sin(ra0) * cos(dec0)
    z0 = sin(dec0)

    # Convert the second point from spherical polar coordinates to Cartesian coordinates
    x1 = cos(ra1) * cos(dec1)
    y1 = sin(ra1) * cos(dec1)
    z1 = sin(dec1)

    # Convert the third point from spherical polar coordinates to Cartesian coordinates
    x2 = cos(ra2) * cos(dec2)
    y2 = sin(ra2) * cos(dec2)
    z2 = sin(dec2)

    # Work out the centroid of the three points in Cartesian space
    x3 = (x0 + x1 + x2) / 3
    y3 = (y0 + y1 + y2) / 3
    z3 = (z0 + z1 + z2) / 3

    # Work out the magnitude of the centroid vector
    mag = sqrt(x3 * x3 + y3 * y3 + z3 * z3)

    # Convert the Cartesian coordinates into RA and Dec
    dec_mean = asin(z3 / mag)
    ra_mean = atan2(y3, x3)
    return [ra_mean, dec_mean]


def gnomonic_project(ra, dec, ra0, dec0, size_x, size_y, scale_x, scale_y, pos_ang, barrel_k1, barrel_k2, barrel_k3):
    """
    Project a pair of celestial coordinates (RA, Dec) into pixel coordinates (x,y)

    :param ra:
        The right ascension of the point to project (radians)
    :param dec:
        The declination of the point to project (radians)
    :param ra0:
        The right ascension of the centre of the frame (radians)
    :param dec0:
        The declination of the centre of the frame (radians)
    :param size_x:
        The horizontal size of the frame (pixels)
    :param size_y:
        The vertical size of the frame (pixels)
    :param scale_x:
        The angular width of the frame (radians)
    :param scale_y:
        The angular height of the frame (radians)
    :param pos_ang:
        The position angle of the frame on the sky
    :param barrel_k1:
        The barrel distortion parameter K1
    :param barrel_k2:
        The barrel distortion parameter K2
    :param barrel_k3:
        The barrel distortion parameter K3
    :return:
        The (x,y) coordinates of the projected point
    """

    dist = ang_dist(ra, dec, ra0, dec0)

    if dist > pi / 2:
        x = -1
        y = -1
        return [x, y]

    [za, az] = make_zenithal(ra, dec, ra0, dec0)
    radius = tan(za)
    az += pos_ang

    # Correction for barrel distortion
    r = radius / tan(scale_x / 2)
    bc_kn = 1. - barrel_k1 - barrel_k2 - barrel_k3
    scaling = (bc_kn + barrel_k1 * (r ** 2) + barrel_k2 * (r ** 4) + barrel_k3 * (r ** 6))
    r2 = r * scaling
    radius = r2 * tan(scale_x / 2)

    yd = radius * cos(az) * (size_y / 2. / tan(scale_y / 2.)) + size_y / 2.
    xd = radius * -sin(az) * (size_x / 2. / tan(scale_x / 2.)) + size_x / 2.

    return [xd, yd]


def inv_gnom_project(ra0, dec0, size_x, size_y, scale_x, scale_y, x, y, pos_ang, barrel_k1, barrel_k2, barrel_k3):
    """
    Project a pair of pixel coordinates (x,y) into a celestial position (RA, Dec). This includes a correction for
    barrel distortion.

    :param ra0:
        The right ascension of the centre of the frame (radians)
    :param dec0:
        The declination of the centre of the frame (radians)
    :param size_x:
        The horizontal size of the frame (pixels)
    :param size_y:
        The vertical size of the frame (pixels)
    :param scale_x:
        The angular width of the frame (radians)
    :param scale_y:
        The angular height of the frame (radians)
    :param x:
        The x position of (RA, Dec)
    :param y:
        The y position of (RA, Dec)
    :param pos_ang:
        The position angle of the frame on the sky
    :param barrel_k1:
        The barrel distortion parameter K1
    :param barrel_k2:
        The barrel distortion parameter K2
    :param barrel_k3:
        The barrel distortion parameter K3
    :return:
        The (RA, Dec) coordinates of the projected point
    """
    x2 = (x - size_x / 2.) / (size_x / 2. / tan(scale_x / 2.))
    y2 = (y - size_y / 2.) / (size_y / 2. / tan(scale_y / 2.))

    za = atan(hypot(x2, y2))
    az = atan2(-x2, y2) - pos_ang

    r = za / tan(scale_y / 2.)
    za = r * tan(scale_y / 2.)

    altitude = pi / 2 - za
    a = [cos(altitude) * cos(az), cos(altitude) * sin(az), sin(altitude)]

    a = rotate_xz(a, -pi / 2 + dec0)
    a = rotate_xy(a, ra0)

    ra = atan2(a[1], a[0])
    dec = asin(a[2])

    # Correction for barrel distortion
    def mismatch_slave(parameters):
        [ra, dec] = parameters
        pos = gnomonic_project(ra=ra, dec=dec, ra0=ra0, dec0=dec0,
                               size_x=size_x, size_y=size_y, scale_x=scale_x, scale_y=scale_y, pos_ang=pos_ang,
                               barrel_k1=barrel_k1, barrel_k2=barrel_k2, barrel_k3=barrel_k3)
        return hypot(pos[0] - x, pos[1] - y)

    params_initial = [ra, dec]
    params_optimised = scipy.optimize.minimize(mismatch_slave, params_initial,
                                               options={'disp': False, 'maxiter': 1e8}).x
    # print "Position before barrel correction: (%s,%s)" % (ra, dec)
    # print "Position after barrel correction: (%s,%s)" % (params_optimised[0], params_optimised[1])
    return params_optimised
