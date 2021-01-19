# -*- coding: utf-8 -*-
# vector_algebra.py
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

from math import pi, sin, cos, acos, asin, atan2, fmod, sqrt

from .dcf_ast import sidereal_time

"""
Functions for dealing with planes and lines
"""


class Point:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def __str__(self):
        return "Point({}, {}, {})".format(self.x, self.y, self.z)

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
    def from_lat_lng(lat, lng, alt, utc):
        lat *= pi / 180
        lng *= pi / 180
        if utc is not None:
            st = sidereal_time(utc) * pi / 12
        else:
            st = 0
        r_earth = 6371e3
        r = r_earth + alt
        x = r * cos(lng + st) * cos(lat)
        y = r * sin(lng + st) * cos(lat)
        z = r * sin(lat)
        return Point(x, y, z)

    def to_lat_lng(self, utc):
        mag = abs(self)
        deg = 180 / pi
        if utc is not None:
            st = sidereal_time(utc) * pi / 12
        else:
            st = 0
        r_earth = 6371e3
        lat = asin(self.z / mag) * deg
        lng = (atan2(self.y, self.x) - st) * deg
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
        return "Vector({}, {}, {})".format(self.x, self.y, self.z)

    def __add__(self, other):
        """
        Add two Vectors together.
        :param Vector other:
        :return Vector:
        """
        if other == 0:
            return self
        return Vector(self.x + other.x, self.y + other.y, self.z + other.z)

    def __radd__(self, other):
        """
        Add two Vectors together.
        :param Vector other:
        :return Vector:
        """
        if other == 0:
            return self
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

    def __truediv__(self, other):
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
        x = cos(ra) * cos(dec)
        y = sin(ra) * cos(dec)
        z = sin(dec)
        return Vector(x, y, z)

    def to_ra_dec(self):
        """
        Converts a vector into an (RA, Dec) direction.
        :return Dict:
        """
        mag = abs(self)

        # Direction is undefined
        if mag == 0:
            return {'ra': 0, 'dec': 0}

        dec = asin(self.z / mag)
        ra = atan2(self.y, self.x)
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

    def angle_with(self, other):
        """
        Returns the angle between two Vectors (radians)
        :param Vector other:
        :return float Angle between two direction vectors (degrees):
        """
        dot = self.dot_product(other)
        mag1 = abs(self)
        mag2 = abs(other)
        angle_cosine = dot / mag1 / mag2

        # Avoid domain errors in inverse cosine
        if angle_cosine > 1:
            angle_cosine = 1
        if angle_cosine < -1:
            angle_cosine = -1

        return acos(angle_cosine) * 180 / pi

    def normalise(self):
        """
        Return the unit vector in the same direction as this vector
        :return Vector:
        """
        mag = abs(self)
        return Vector(self.x / mag, self.y / mag, self.z / mag)


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
        return "Line( x0=Point({}, {}, {}), direction=Vector({}, {}, {}))".format(
            self.x0.x, self.x0.y, self.x0.z,
          self.direction.x, self.direction.y, self.direction.z
        )

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

    def find_closest_approach(self, other):
        """
        Find the point of closest approach between two lines.
        :param Line other:
        :return Dict:
        """

        # https://books.google.co.uk/books?id=NKONAgAAQBAJ&pg=PA20#v=onepage&q&f=false

        p1 = self.x0
        p2 = other.x0
        r = self.direction
        d = other.direction

        p1_minus_p2 = p2.displacement_vector_from(p1)

        d_dot_r = d.dot_product(r)

        mu = (p1_minus_p2.dot_product(d) - p1_minus_p2.dot_product(r) * d_dot_r) / (1 - pow(d_dot_r, 2))

        lambda_ = mu * d_dot_r - p1_minus_p2.dot_product(r)

        self_point = self.point(lambda_)
        other_point = other.point(mu)
        distance = abs(self_point.displacement_vector_from(other_point))
        angular_distance = abs(self_point.displacement_from_origin().angle_with(other_point.displacement_from_origin()))

        return {'self_point': self_point, 'other_point': other_point,
                'distance': distance, 'angular_distance': angular_distance}

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
        return "Plane( normal=Vector({}, {}, {}}), p={})".format(self.normal.x, self.normal.y, self.normal.z, self.p)

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
