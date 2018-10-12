# mod_gnomonic.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# -------------------------------------------------
# Copyright 2016 Cambridge Science Centre.

# This file is part of Meteor Pi.

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

from math import sin, cos, tan, pi, asin, atan, atan2, sqrt, fabs, hypot
import scipy.optimize


def rotate_xy(a, theta):
    a0 = a[0] * cos(theta) + a[1] * -sin(theta)
    a1 = a[0] * sin(theta) + a[1] * cos(theta)
    a2 = a[2]
    return [a0, a1, a2]


def rotate_xz(a, theta):
    a0 = a[0] * cos(theta) + a[2] * -sin(theta)
    a1 = a[1]
    a2 = a[0] * sin(theta) + a[2] * cos(theta)
    return [a0, a1, a2]


# Return the position angle of the great circle path from (RA1, Dec1) to (RA2, Dec2), as seen at the former point
def position_angle(ra1, dec1, ra2, dec2):
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
    x0 = cos(ra0) * cos(dec0)
    y0 = sin(ra0) * cos(dec0)
    z0 = sin(dec0)
    x1 = cos(ra1) * cos(dec1)
    y1 = sin(ra1) * cos(dec1)
    z1 = sin(dec1)
    d = sqrt(pow(x0 - x1, 2) + pow(y0 - y1, 2) + pow(z0 - z1, 2))
    return 2 * asin(d / 2)


def find_mean_position(ra0, dec0, ra1, dec1, ra2, dec2):
    x0 = cos(ra0) * cos(dec0)
    y0 = sin(ra0) * cos(dec0)
    z0 = sin(dec0)
    x1 = cos(ra1) * cos(dec1)
    y1 = sin(ra1) * cos(dec1)
    z1 = sin(dec1)
    x2 = cos(ra2) * cos(dec2)
    y2 = sin(ra2) * cos(dec2)
    z2 = sin(dec2)
    x3 = (x0 + x1 + x2) / 3
    y3 = (y0 + y1 + y2) / 3
    z3 = (z0 + z1 + z2) / 3
    dec_mean = asin(z3)
    ra_mean = atan2(y3, x3)
    return [ra_mean, dec_mean]


def gnomonic_project(ra, dec, ra0, dec0, size_x, size_y, scale_x, scale_y, pos_ang, bca, bcb, bcc):
    dist = ang_dist(ra, dec, ra0, dec0)

    if dist > pi / 2:
        x = -1
        y = -1
        return [x, y]

    [za, az] = make_zenithal(ra, dec, ra0, dec0)
    radius = tan(za)
    az += pos_ang

    # Correction for barrel distortion
    r = radius / tan(scale_y / 2)
    bcd = 1. - bca - bcb - bcc
    r2 = (((bca * r + bcb) * r + bcc) * r + bcd) * r
    radius = r2 * tan(scale_y / 2)

    yd = radius * cos(az) * (size_y / 2. / tan(scale_y / 2.)) + size_y / 2.
    xd = radius * -sin(az) * (size_x / 2. / tan(scale_x / 2.)) + size_x / 2.

    return [xd, yd]


# Includes correction for barrel distortion
def inv_gnom_project(ra0, dec0, size_x, size_y, scale_x, scale_y, x, y, pos_ang, bca, bcb, bcc):
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
        pos = gnomonic_project(ra, dec, ra0, dec0, size_x, size_y, scale_x, scale_y, pos_ang, bca, bcb, bcc)
        return hypot(pos[0] - x, pos[1] - y)

    params_initial = [ra, dec]
    params_optimised = scipy.optimize.minimize(mismatch_slave, params_initial, method='nelder-mead',
                                               options={'xtol': 1e-8, 'disp': False, 'maxiter': 1e8, 'maxfev': 1e8}).x
    # print "Position before barrel correction: (%s,%s)" % (ra, dec)
    # print "Position after barrel correction: (%s,%s)" % (params_optimised[0], params_optimised[1])
    return params_optimised
