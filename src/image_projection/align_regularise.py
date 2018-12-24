#!../../virtualenv/bin/python3
# -*- coding: utf-8 -*-
# align_regularise.py
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

"""
This script takes a list of images that we have attempted to locate on the sky using astrometry.net. It assumes that
the camera was pointing towards a fixed direction in the sky over the course of the observations, and that the sky
was rotating as sidereal time advanced. It finds the best-fit altitude and azimuth that the camera may have been
pointing at, and then recomputes (more accurate) fits to the central position of each image.

The format that the input file is expected to take is that produced by (for example) <align_gnomonic.py>
These files are also produced by <observatoryControl/orientationCalc.py>
"""

import sys
import os
from math import pi, sin, cos, atan2

import mod_gnomonic


def sgn(val):
    if val < 0:
        return -1
    if val > 0:
        return 1
    return 0


config_in_filename = sys.argv[1]
config_in_lines = open(config_in_filename).readlines()

cwd = os.getcwd()
pid = os.getpid()


def sort_on_utc(a, b):
    return int(sgn(a[11] - b[11]))

config_out_lines = []
rejected_files = []
fits = []

previous_ra = -1000
previous_dec = -1000
previous_pa = -1000
image_list = []

# Loop over the lines in the input configuration file
for line in config_in_lines:

    # Header lines of this form indicate files that astrometry.net couldn't match against the sky. We might now be
    # able to work out where they go, so we make a list of them in rejected_files.
    if line.startswith("# Cannot read"):
        filename = line[38:].strip()
        utc = gnomonic_project.image_time(filename)
        rejected_files.append([filename, utc])
        continue
    if line.startswith("# ADD"):
        filename = line.split()[2]
        utc = gnomonic_project.image_time(filename)
        rejected_files.append([filename, utc])
        continue

    # Lines that aren't headers we recognise, and aren't ADD commands (each of which lists an image with associated fit)
    # are metadata. Pass this metadata straight through to the output file
    elif not line.startswith("ADD"):
        config_out_lines.append(line)
        continue

    # If we reach here, we have an ADD command in the config file. This lists an image file and associated fit
    [add, filename, weight, expcomp, img_size_x, img_size_y, ra, dec, pa, scalex, scaley] = line.split()
    utc = gnomonic_project.image_time(filename)

    # If the proposed location of this file on the sky is very different from the previous image, assume the camera
    # did actually move...
    if ((abs(previous_ra - float(ra)) > 0.5) or
            (abs(previous_dec - float(dec)) > 5) or
            (abs(previous_pa - float(pa)) > 5)):
        if image_list:
            fits.append(image_list)
            reasons = []
            if abs(previous_ra - float(ra)) > 0.5:
                reasons.append("RAs do not match")
            if abs(previous_dec - float(dec)) > 5:
                reasons.append("Decs do not match")
            if abs(previous_pa - float(pa)) > 5:
                reasons.append("PAs do not match")
            print("# Splitting on <%s>; because %s." % (os.path.split(filename)[1], ", ".join(reasons)))
        image_list = []
    previous_ra = float(ra)
    previous_dec = float(dec)
    previous_pa = float(pa)
    image_list.append(
            [add, filename, float(weight), float(expcomp), float(img_size_x), float(img_size_y), float(ra), float(dec),
             float(pa), float(scalex), float(scaley), utc])
if image_list:
    fits.append(image_list)

# The central declination, position angle, and field of view should remain constant.
# Take a straightforward average of all of the values returned by astrometry.net
for image_list in fits:
    mean_declination = sum([x[7] for x in image_list]) / len(image_list)
    mean_pa = sum([x[8] for x in image_list]) / len(image_list)
    mean_scale_x = sum([x[9] for x in image_list]) / len(image_list)
    mean_scale_y = sum([x[10] for x in image_list]) / len(image_list)

    # Right ascension advances with sidereal time. Theta is the difference between observed RA and sidereal time
    p = [0, 0]
    for x in image_list:
        theta = x[6] * pi / 12 - x[11] / (23.9344696 * 3600) * (2 * pi)
        p[0] += sin(theta)
        p[1] += cos(theta)

    # This is the average value of theta. Don't need to divide by number of images, as we're throwing away the
    # magnitude of the vector p!
    theta = atan2(p[0], p[1])

    # Go back and repopulate our array of images with new positions on the sky
    for x in image_list:
        x[7] = mean_declination
        x[8] = mean_pa
        x[9] = mean_scale_x
        x[10] = mean_scale_y
        x[6] = ((theta + x[11] / (23.9344696 * 3600) * (2 * pi)) / pi * 12) % 24

    image_list.sort(sort_on_utc)

    # Now go through the rejected image files, as we can infer their positions on the sky
    for x in rejected_files:
        [filename, utc] = x
        if (utc > image_list[0][11]) and (utc < image_list[-1][11]):
            ra = ((theta + utc / (23.9344696 * 3600) * (2 * pi)) / pi * 12) % 24
            [img_size_x, img_size_y] = gnomonic_project.image_dimensions(filename)
            image_list.append(["ADD", x[0], 1, 1, img_size_x, img_size_y, ra, mean_declination, mean_pa,
                               mean_scale_x, mean_scale_y, utc])
            image_list.sort(sort_on_utc)

# Start printing our new configuration file
# First, display any metadata headers that we're piping from the input configuration
for line in config_out_lines:
    print(line.strip())

# Then display a list of the orientations we've inferred for each image
for i in range(len(fits)):
    for j in range(len(fits[i])):
        [add, filename, weight, expcomp, img_size_x, img_size_y, ra, dec, pa, scalex, scaley, utc] = fits[i][j]
        # Filename, weight, expcomp, Central RA, Central Dec, position angle, scalex, scaley
        print(("ADD %-93s %4.1f %4.1f %4d %4d %10.5f %10.5f %10.5f %10.5f %10.5f"
               % (filename, weight, expcomp, img_size_x, img_size_y, ra, dec, pa, scalex, scaley)
               ))
