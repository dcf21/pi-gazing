# -*- coding: utf-8 -*-
# constellation_fetch.py
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


from math import *


# Class used to work out which constellations point lie in
class ConstellationFetcher:
    def __init__(self, c):
        """
        Constructor reads constellation names and id numbers from database, and reads their outlines from the file
        <../../data/starPlot_ppl8/dataRaw/constellations/eq2000.dat>.

        :param c:
            MySQLdb database connection
        """

        c.execute("""
SELECT constellationId,abbrev,'' AS genitiveForm FROM inthesky_constellations WHERE abbrev='Unknown';
""")
        self.fail_id = c.fetchone()

        filename = "../../data/starPlot_ppl8/dataRaw/constellations/eq2000.dat"

        point_list = ["@@@", 0]
        self.constellations = []
        for line in open(filename):
            if (len(line.strip()) < 1) or (line.strip()[0] == "#"):
                continue
            words = line.split()
            ra = float(words[0]) * pi / 12
            dec = float(line[12:22]) * pi / 180
            if line[11] == "-":
                dec *= -1
            con_abbrev = line[23:].split()[0]
            if con_abbrev != point_list[0]:
                c.execute("SELECT constellationId,abbrev,genitiveForm FROM inthesky_constellations WHERE abbrev=%s;",
                          (con_abbrev,))
                con_info = c.fetchone()
                point_list = [con_info["abbrev"], con_info["constellationId"], con_info["genitiveForm"]]
                self.constellations.append(point_list)
            point_list.append([ra, dec])

    @staticmethod
    def angdist_radec(ra0, dec0, ra1, dec1):
        """
        Calculate the angular distance between two points on the sky.

        :param ra0:
            Right ascension of first point, radians

        :type ra0:
            float

        :param dec0:
            Declination of first point, radians

        :type dec0:
            float

        :param ra1:
            Right ascension of second point, radians

        :type ra1:
            float

        :param dec1:
            Declination of second point, radians

        :type dec1:
            float

        :return:
            Angular distance, radians
        """

        def gsl_pow_2(x):
            return x * x

        p0x = sin(ra0) * cos(dec0)
        p0y = cos(ra0) * cos(dec0)
        p0z = sin(dec0)

        p1x = sin(ra1) * cos(dec1)
        p1y = cos(ra1) * cos(dec1)
        p1z = sin(dec1)

        sep = sqrt(gsl_pow_2(p0x - p1x) + gsl_pow_2(p0y - p1y) + gsl_pow_2(p0z - p1z))

        return 2 * asin(sep / 2)

    @staticmethod
    def d_wind(ra, dec, ra0, dec0, ra1, dec1):
        """
        Work out the change in winding number about the central point (ra, dec) along the line segment from
        (ra0, dec0) to (ra1, dec1). By adding up the changes along a closed polygon describing the outline of a
        sky area (e.g. a constellation), it is possible to work out whether the point (ra, dec) is within that
        polygon. If the winding number is zero, the point is not in that sky area, otherwise it is.

        :param ra:
            Right ascension of central point, radians

        :type ra:
            float

        :param dec:
            Declination of central point, radians

        :type dec:
            float

        :param ra0:
            Right ascension of first point, radians

        :type ra0:
            float

        :param dec0:
            Declination of first point, radians

        :type dec0:
            float

        :param ra1:
            Right ascension of second point, radians

        :type ra1:
            float

        :param dec1:
            Declination of second point, radians

        :type dec1:
            float

        :return:
            Change in winding number along line segment
        """
        xa0 = sin(ra0) * cos(dec0)
        xa1 = sin(ra1) * cos(dec1)
        ya0 = cos(ra0) * cos(dec0)
        ya1 = cos(ra1) * cos(dec1)
        za0 = sin(dec0)
        za1 = sin(dec1)

        xb0 = xa0 * cos(-ra) + ya0 * sin(-ra)
        xb1 = xa1 * cos(-ra) + ya1 * sin(-ra)
        yb0 = xa0 * sin(ra) + ya0 * cos(-ra)
        yb1 = xa1 * sin(ra) + ya1 * cos(-ra)
        zb0 = za0
        zb1 = za1

        a = (pi / 2) - dec

        xc0 = xb0
        xc1 = xb1
        yc0 = yb0 * cos(- a) + zb0 * sin(- a)
        yc1 = yb1 * cos(- a) + zb1 * sin(- a)
        # zC0 = yb0*sin(  a) + zb0*cos(- a)
        # zC1 = yb1*sin(  a) + zb1*cos(- a);

        dw = atan2(xc0, yc0) - atan2(xc1, yc1)
        while dw < -pi:
            dw += 2 * pi
        while dw > pi:
            dw -= 2 * pi
        return dw

    def constellation_fetch(self, ra, dec):  # Hours and degrees
        """
        Work out which constellation the point (ra,dec) is in.

        :param ra:
            Right ascension of point, hours

        :type ra:
            float

        :param dec:
            Declination of point, degrees

        :type dec:
            float

        :return:
            A list of [constellation id, constellation abbreviation, constellation genative form]
        """
        ra *= pi / 12
        dec *= pi / 180
        for i in self.constellations:
            winding = 0.0
            angsep = self.angdist_radec(ra, dec, i[3][0], i[3][1])
            n = len(i)
            # Winding number calculation triggers for constellation containing point opposite to (RA,DEC)
            # as well as for desired point; filter for this now.
            if angsep > pi / 2:
                continue
            for j in range(3, n):
                k = (j + 1)
                if k >= n:
                    k += 3 - n
                winding += self.d_wind(ra, dec, i[j][0], i[j][1], i[k][0], i[k][1])
            if abs(winding) > pi:
                return [i[1], i[0], i[2]]
        return [self.fail_id["constellationId"], self.fail_id["abbrev"], self.fail_id["genitiveForm"]]
