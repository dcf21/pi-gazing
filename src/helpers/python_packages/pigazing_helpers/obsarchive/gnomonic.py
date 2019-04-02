# -*- coding: utf-8 -*-
# gnomonic.py

from math import sin, cos, tan, pi, asin, atan, atan2, sqrt, fabs, hypot


def rotate_xy(a, theta):
    """
    Rotate a 3D vector in the XY plane.

    :param a:
        List of three numbers, representing a 3D Cartesian vector.

    :param theta:
        Angle, radians.

    :return:
        List of three numbers, representing the rotated 3D Cartesian vector.
    """
    a0 = a[0] * cos(theta) + a[1] * -sin(theta)
    a1 = a[0] * sin(theta) + a[1] * cos(theta)
    a2 = a[2]
    return [a0, a1, a2]


def rotate_xz(a, theta):
    """
    Rotate a 3D vector in the XZ plane.

    :param a:
        List of three numbers, representing a 3D Cartesian vector.

    :param theta:
        Angle, radians.

    :return:
        List of three numbers, representing the rotated 3D Cartesian vector.
    """
    a0 = a[0] * cos(theta) + a[2] * -sin(theta)
    a1 = a[1]
    a2 = a[0] * sin(theta) + a[2] * cos(theta)
    return [a0, a1, a2]


def make_zenithal(ra, dec, ra0, dec0):
    """

    :param ra:
        RA of point to project, radians.

    :param dec:
        Declination of point to project, radians.

    :param ra0:
        RA of point at the centre of the gnomonic projection, radians.

    :param dec0:
        Declination of point at the centre of the gnomonic projection, radians.

    :return:
        [zenith_angle, azimuth] where:

        zenith angle is separation of [ra,dec] from [ra0,dec0] in radians.

        azimuth is the position angle of [ra,dec] relative to north, as seen from [ra0,dec0], in radians.
    """
    x = cos(ra) * cos(dec)
    y = sin(ra) * cos(dec)
    z = sin(dec)
    a = [x, y, z]
    a = rotate_xy(a, -ra0)
    a = rotate_xz(a, pi / 2 - dec0)

    # Check to improve numerical stability
    if a[2] > 0.999999999:
        a[2] = 1.0
    if a[2] < -0.999999999:
        a[2] = -1.0

    # Turn Cartesian vector into altitude and azimuth
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
    Calculate the angular separation between two points, in radians.

    :param ra0:
        RA of point 0, radians.

    :param dec0:
        Declination of point 0, radians.

    :param ra1:
        RA of point 1, radians.

    :param dec1:
        Declination of point 1, radians.

    :return:
        Angle, radians
    """
    x0 = cos(ra0) * cos(dec0)
    y0 = sin(ra0) * cos(dec0)
    z0 = sin(dec0)
    x1 = cos(ra1) * cos(dec1)
    y1 = sin(ra1) * cos(dec1)
    z1 = sin(dec1)
    d = sqrt(pow(x0 - x1, 2) + pow(y0 - y1, 2) + pow(z0 - z1, 2))
    return 2 * asin(d / 2)


def gnomonic_project(ra, dec, ra0, dec0, size_x, size_y, scale_x, scale_y, pos_ang):
    """
    Calculate the (x, y) pixel position of the point (RA, Dec) in an image.

    :param ra:
        RA of the point being calculated, radians.

    :param dec:
        Declination of the point being calculated, radians.

    :param ra0:
        RA of the centre of the frame, radians.

    :param dec0:
        Declination of the centre of the frame, radians.

    :param size_x:
        Width of the image, in pixels.

    :param size_y:
        Height of the image, in pixels.

    :param scale_x:
        Width of the field of view of the image, radians.

    :param scale_y:
        Height of the field of view of the image, radians.

    :param pos_ang:
        Position angle of the image, radians.

    :return:
        (x, y) position in pixels, with (0, 0) in the centre.

    """
    dist = ang_dist(ra, dec, ra0, dec0)

    if dist > pi / 2:
        x = -1
        y = -1
        return [x, y]

    [za, az] = make_zenithal(ra, dec, ra0, dec0)
    radius = tan(za)
    az += pos_ang

    yd = radius * cos(az) * (size_y / 2. / tan(scale_y / 2.)) + size_y / 2.
    xd = radius * -sin(az) * (size_x / 2. / tan(scale_x / 2.)) + size_x / 2.

    return [xd, yd]


def inv_gnomonic_project(ra0, dec0, size_x, size_y, scale_x, scale_y, x, y, pos_ang):
    """
    Work out the (RA, Dec) of the pixel position (x, y) within an image.

    :param ra0:
        RA of the centre of the frame, radians.

    :param dec0:
        Declination of the centre of the frame, radians.

    :param size_x:
        Width of the image, in pixels.

    :param size_y:
        Height of the image, in pixels.

    :param scale_x:
        Width of the field of view of the image, radians.

    :param scale_y:
        Height of the field of view of the image, radians.

    :param x:
        X-pixel of point being calculated, where x=0 is in the bottom left.

    :param y:
        Y-pixel of point being calculated, where y=0 is in the bottom left.

    :param pos_ang:
        Position angle of the image, radians.

    :return:
        (RA, Dec) position in radians
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

    if ra < 0:
        ra += 2 * pi

    return [ra, dec]
