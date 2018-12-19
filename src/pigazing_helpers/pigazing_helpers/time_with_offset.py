# -*- coding: utf-8 -*-
# time_with_offset.py
#
# -------------------------------------------------
# Copyright 2015-2018 Dominic Ford
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

import os
import time

from .dcf_ast import unix_from_jd, jd_from_unix, julian_day, inv_julian_day


class ClockWithOffset:
    """
    Class used to create a clock with a fixed offset from the system clock. We use this if we have a GPS fix which tells
    us a different time from the system clock.
    """

    def __init__(self, offset):
        """
        Create a clock with a fixed offset from the system clock.

        :param offset:
            Offset from the system clock, in seconds. Positive values mean the clock will be ahead of the system clock.
        :type offset:
            float
        """
        self._offset = offset

    def get_utc(self):
        """
        Retrieve the current time
        :return:
            Unix time, seconds.
        """
        return time.time() + self._offset

    def get_utc_offset(self):
        """
        Retrieve the offset of this clock from the system clock.

        :return:
            Offset, in seconds. Positive values mean the clock will be ahead of the system clock.
        """
        return self._offset

    def set_utc_offset(self, x):
        """
        Set the offset of this clock from the system clock.
        :param x:
            Offset, in seconds. Positive values mean the clock will be ahead of the system clock.
        :return:
            None
        """
        self._offset = x


# Function for turning filenames into Unix times
def filename_to_utc(f):
    """
    Function for turning filenames of observations into Unix times. We have a standard filename convention, where
    all observations start with the UTC date and time that the observation was made.

    :param f:
        Filename of observation
    :type f:
        str
    :return:
        The unix time when the observation was made
    """

    f = os.path.split(f)[1]
    if not f.startswith("20"):
        return -1
    year = int(f[0: 4])
    mon = int(f[4: 6])
    day = int(f[6: 8])
    hour = int(f[8:10])
    minute = int(f[10:12])
    sec = int(f[12:14])
    return unix_from_jd(julian_day(year, mon, day, hour, minute, sec))


def fetch_day_name_from_filename(f):
    """
    Fetch a string describing the day when an observation was made, based on its filename. We have a standard filename
    convention, where all observations start with the UTC date and time that the observation was made.

    :param f:
        Filename of observation
    :type f:
        str
    :return:
        The day when the observation was made
    """

    f = os.path.split(f)[1]
    if not f.startswith("20"):
        return None
    utc = filename_to_utc(f)
    utc -= 12 * 3600
    [year, month, day, hour, minu, sec] = inv_julian_day(jd_from_unix(utc))
    return "{:04d}{:02d}{:02d}".format(year, month, day)
