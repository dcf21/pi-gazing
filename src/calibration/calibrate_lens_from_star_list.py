#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# calibrate_lens_from_star_list.py
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

"""
This script is used to estimate the degree of lens distortion present in an
image.

It should be passed the a JSON file through stdin containing a list of stars
with known positions in the image. This file needs to be produced manually.

The JSON files in this directory provide an example of the format each input
file should take. The stars should be listed as [xpos, ypos, hipparcos number].

It then uses the Python Scientific Library's numerical optimiser (with seven
free parameters) to work out the position of the centre of the image in the
sky, the image's rotation, scale on the sky, and the radial distortion factors.

The best-fit parameter values are returned to the user. If they are believed to
be good, you should set a status update on the observatory setting barrel_k1
and barrel_k1. Then future observations will correct for this lens distortion.

You may also changed the values for your lens in the XML file
<src/configuration_global/camera_properties> which means that future
observatories set up with your model of lens will use your barrel correction
coefficients.
"""

import argparse
import logging
import os
import sys
import json
import subprocess
from math import hypot, pi, isfinite
import scipy.optimize
from pigazing_helpers import connect_db, hardware_properties
from pigazing_helpers.dcf_ast import date_string
from pigazing_helpers.gnomonic_project import gnomonic_project
from pigazing_helpers.obsarchive import obsarchive_model as mp, obsarchive_db, obsarchive_sky_area
from pigazing_helpers.settings_read import settings, installation_info

degrees = pi / 180


# Return the dimensions of an image
def image_dimensions(in_file):
    """
    Return the pixel dimensions of an image.

    :param in_file:
        The filename of the image to measure
    :type in_file:
        str
    :return:
        List of the horizontal and vertical pixel dimensions
    """
    d = subprocess.check_output(["identify", "-quiet", in_file]).decode('utf-8').split()[2].split("x")
    d = [int(i) for i in d]
    return d

# Read Hipparcos catalogue of stars brighter than mag 5.5
hipparcos_catalogue = json.loads(open("hipparcos_catalogue.json").read())


def mismatch(params):
    """
    The objective function which is optimized to fit the barrel-distortion coefficients of the image.

    :param params:
        A vector, containing values in order, each normalised in units of <param_scales>:
            0) The central RA of the image (radians)
            1) The central declination of the image (radians)
            2) The horizontal field-of-view of the image (radians)
            3) The vertical field-of-view of the image (radians)
            4) The position angle of the image; i.e. the angle of celestial north to the vertical (radians)
            5) The barrel-distortion coefficient K1
            6) The barrel-distortion coefficient K2
    :return:
        A measure of the mismatch of this proposed image orientation, based on the list of pixel positions and
        calculated (RA, Dec) positions contained within <fit_list>.
    """
    global parameter_scales, star_list
    ra0 = params[0] * parameter_scales[0]
    dec0 = params[1] * parameter_scales[1]
    scale_x = params[2] * parameter_scales[2]
    scale_y = params[3] * parameter_scales[3]
    pos_ang = params[4] * parameter_scales[4]
    bc_k1 = params[5] * parameter_scales[5]
    bc_k2 = params[6] * parameter_scales[6]

    offset_list = []
    for star in star_list:
        pos = gnomonic_project(ra=star['ra'], dec=star['dec'], ra0=ra0, dec0=dec0,
                               size_x=1, size_y=1, scale_x=scale_x, scale_y=scale_y, pos_ang=pos_ang,
                               barrel_k1=bc_k1, barrel_k2=bc_k2)
        if not isfinite(pos[0]):
            pos[0] = -999
        if not isfinite(pos[1]):
            pos[1] = -999
        offset = pow(hypot(star['x'] - pos[0], star['y'] - pos[1]), 2)
        offset_list.append(offset)

    # Sort offsets into order of magnitude
    offset_list.sort()

    # Sum the offsets
    accumulator = sum(offset_list)

    # Debugging
    # logging.info("{:10e} -- {}".format(accumulator, list(params)))

    # Return result
    return accumulator

def calibrate_lens():
    # Read input list of stars whose positions we know
    input_config = sys.stdin.read()

    # Look up positions of each star, based on listed Hipparcos catalogue numbers
    star_list = []
    for star in input_config['star_list']:
        hipp = str(star[2])
        if hipp not in hipparcos_catalogue:
            logging.info("Could not find star {:d}".format(hipp))
            continue
        [ra, dec] = hipparcos_catalogue[hipp]
        star_list.append({'xpos': int(star[0]), 'ypos': int(star[1]), 'ra': ra * degrees, 'dec': dec * degrees})

    # Get dimensions of the image we are dealing with
    image_file = input_config['image_file']
    [img_size_x, img_size_y] = image_dimensions(image_file)

    # Solve system of equations to give best fit barrel correction
    # See <http://www.scipy-lectures.org/advanced/mathematical_optimization/> for more information about how this works
    ra0 = star_list[0]['ra']
    dec0 = star_list[0]['dec']
    parameter_scales = [pi / 4, pi / 4, pi / 4, pi / 4, pi / 4, 0.05, 0.0005]
    parameter_defaults = [ra0, dec0, pi / 4, pi / 4, 0, 0, 0]
    parameter_initial = [parameter_defaults[i] / parameter_scales[i] for i in range(len(parameter_defaults))]
    parameter_optimised = scipy.optimize.minimize(mismatch, parameter_initial, method='nelder-mead',
                                               options={'xtol': 1e-8, 'disp': True, 'maxiter': 1e8, 'maxfev': 1e8}).x
    parameter_final = [parameter_optimised[i] * parameter_scales[i] for i in range(len(parameter_defaults))]

    # Display best fit numbers
    headings = [["Central RA / hr", 12 / pi], ["Central Decl / deg", 180 / pi],
                ["Image width / deg", 180 / pi], ["Image height / deg", 180 / pi],
                ["Position angle / deg", 180 / pi],
                ["barrel_k1", 1], ["barrel_k2", 1]
                ]

    logging.info("Best fit parameters were:")
    for i in range(len(parameter_defaults)):
        logging.info("{:30s} : {:s}".format(headings[i][0], parameter_final[i] * headings[i][1]))

    # Print information about how well each star was fitted
    [ra0, dec0, scale_x, scale_y, pos_ang, bca, bcb, bcc] = parameter_final
    if True:
        logging.info("Stars used in fitting process:")
        for star in star_list:
            pos = gnomonic_project(star['ra'], star['dec'], ra0, dec0,
                                   img_size_x, img_size_y, scale_x, scale_y, pos_ang,
                                   bca, bcb, bcc)
            distance = hypot(star['xpos'] - pos[0], star['ypos'] - pos[1])
            logging.info("""
User-supplied position ({:4d},{:4d}). Model position ({:4.0f},{:4.0f}). Mismatch {:5.0f} pixels.
""".format(star['xpos'], star['ypos'], pos[0], pos[1], distance).strip())


# If we're called as a script, run the function calibrate_lens()
if __name__ == "__main__":
    # Read commandline arguments
    parser = argparse.ArgumentParser(description=__doc__)
    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(level=logging.INFO,
                        format='[%(asctime)s] %(levelname)s:%(filename)s:%(message)s',
                        datefmt='%d/%m/%Y %H:%M:%S',
                        handlers=[
                            logging.FileHandler(os.path.join(settings['pythonPath'], "../datadir/pigazing.log")),
                            logging.StreamHandler()
                        ])
    logger = logging.getLogger(__name__)
    # logger.info(__doc__.strip())

    # Calculate the orientation of images
    calibrate_lens()
