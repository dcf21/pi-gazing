#!../../virtualenv/bin/python3
# -*- coding: utf-8 -*-
# align_gnomonic.py
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
This takes a series of images and uses astrometry.net to try and work out where there are in the sky
The command line syntax is:

./align_gnomonic.py <barrel_a> <barrel_b> <barrel_c> <filename_list>

The script will then output to stdout a configuration file which can be used by the C program <stack> to stack
the images together

This script is not normally used by Pi Gazing -- the observatory control software uses
<observatoryControl/orientationCalc.py> instead to work out where each camera is pointing.
"""

import math
import os
import re
import sys
import time

import mod_gnomonic


def sgn(val):
    if val < 0:
        return -1
    if val > 0:
        return 1
    return 0


barrel_a = sys.argv[1]
barrel_b = sys.argv[2]
barrel_c = sys.argv[3]
filenames = sys.argv[4:]
filenames.sort()

cwd = os.getcwd()
pid = os.getpid()
tmp = "/tmp/align_gnomonic_%d" % pid
os.system("mkdir %s" % tmp)
os.chdir(tmp)

python_path = os.path.split(os.path.abspath(__file__))[0]

binary_barrel_correct = os.path.join(python_path, "bin", "barrel")
binary_subtract_imgs = os.path.join(python_path, "bin", "subtract")

fits = []

count = 0

# Loop over each image in the group we have been given
for f in filenames:
    logger.info("Working on <%s>" % f)
    count += 1
    f = os.path.join(cwd, f)
    os.system("rm -f *")

    # First correct for the barrel distortion present in each image
    os.system("%s %s %.6f %.6f %.6f tmp2.png" % (binary_barrel_correct, f, barrel_a, barrel_b, barrel_c))

    # Then subtract the sky background
    os.system("%s tmp2.png /tmp/average.png tmp3.png" % (binary_subtract_imgs))

    # Crop out the central region of each image. This line probably ought to be commented out.
    os.system("convert tmp3.png -crop 360x240+180+120 +repage tmp.png")

    # Pass each image to astrometry.net. Use the --no-plots command-line option to speed things up
    os.system("timeout 5m solve-field --no-plots --crpix-center --overwrite tmp.png > txt")

    # Read the output produced by astrometry.net
    fit_text = open("txt").read()
    test = re.search(r"\(RA H:M:S, Dec D:M:S\) = \(([\d-]*):(\d\d):([\d.]*), [+]?([\d-]*):(\d\d):([\d\.]*)\)", fit_text)
    if not test:
        logger.info("Cannot read central RA and Dec from %s" % f)
        continue

    # Read the central RA and Dec returned by astrometry.net
    ra_sign = sgn(float(test.group(1)))
    ra = abs(float(test.group(1))) + float(test.group(2)) / 60 + float(test.group(3)) / 3600
    if (ra_sign < 0): ra *= -1
    decl_sign = sgn(float(test.group(4)))
    dec = abs(float(test.group(4))) + float(test.group(5)) / 60 + float(test.group(6)) / 3600
    if (decl_sign < 0): dec *= -1
    test = re.search(r"up is [+]?([-\d\.]*) degrees (.) of N", fit_text)
    if not test:
        logger.info("Cannot read position angle from %s" % f)
        continue

    # This 180 degree rotation appears to be a bug in astrometry.net (pos angles relative to south, not north)
    pos_ang = float(test.group(1)) + 180
    while pos_ang > 180:
        pos_ang -= 360
    if test.group(2) == "W":
        pos_ang *= -1
    test = re.search(r"Field size: ([\d\.]*) x ([\d\.]*) deg", fit_text)
    if not test:
        logger.info("Cannot read field size from %s" % f)
        continue
    scale_x = float(test.group(1))
    scale_y = float(test.group(2))
    image_dimensions = gnomonic_project.image_dimensions(f)
    fits.append([f, ra, dec, pos_ang, scale_x, scale_y, image_dimensions])

i = int(math.floor(len(fits) / 2))

# Start printing a configuration file.
# Begin with some headers defining what we know about the camera that took this group of images
print("SET output /tmp/output.png")
print("SET barrel_a %s" % barrel_a)
print("SET barrel_b %s" % barrel_b)
print("SET barrel_c %s" % barrel_c)
print("SET latitude 0")
print("SET longitude 0")
print("SET utc %10d" % (gnomonic_project.image_time(fits[i][0])))

# Output files consist of one line for each image file, with the following values separated by spaces
# Exposure compensation, x_size, y_size, Central RA, Central Dec, position angle, scale_x, scale_y
print(("%-102s %4.1f %4d %4d %10.5f %10.5f %10.5f %10.5f %10.5f"
       % ("GNOMONIC", 1, fits[i][6][0], fits[i][6][1], fits[i][1], fits[i][2], fits[i][3], fits[i][4], fits[i][5])
       ))
for i in range(len(fits)):
    image_dimensions = gnomonic_project.image_dimensions(fits[i][0])
    # Filename, weight, exposure compensation, Central RA, Central Dec, position angle, scale_x, scale_y
    print(("ADD %-93s %4.1f %4.1f %4d %4d %10.5f %10.5f %10.5f %10.5f %10.5f"
           % (fits[i][0], 1, 1, image_dimensions[0], image_dimensions[1],
              fits[i][1], fits[i][2], fits[i][3], fits[i][4], fits[i][5])
           ))

# Delete temporary directory
os.system("rm -Rf %s" % tmp)
