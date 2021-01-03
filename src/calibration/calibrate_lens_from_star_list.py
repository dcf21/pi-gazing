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
be good, you should set a status update on the observatory setting
<barrel_parameters>. Then future observations will correct for this lens
distortion.

You may also changed the values for your lens in the XML file
<src/configuration_global/camera_properties> which means that future
observatories set up with your model of lens will use your barrel correction
coefficients.
"""

import argparse
import glob
import json
import logging
import os
from math import hypot, pi, isfinite, tan

import scipy.optimize
from pigazing_helpers.gnomonic_project import gnomonic_project, ang_dist
from pigazing_helpers.settings_read import settings

degrees = pi / 180

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
            7) The barrel-distortion coefficient K3
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
    bc_k3 = params[7] * parameter_scales[7]

    offset_list = []
    for star in star_list:
        pos = gnomonic_project(ra=star['ra'], dec=star['dec'], ra0=ra0, dec0=dec0,
                               size_x=1, size_y=1, scale_x=scale_x, scale_y=scale_y, pos_ang=pos_ang,
                               barrel_k1=bc_k1, barrel_k2=bc_k2, barrel_k3=bc_k3)
        if not (isfinite(pos[0]) and isfinite(pos[1])):
            return float('NaN')
        offset = pow(hypot(star['xpos'] - pos[0], star['ypos'] - pos[1]), 2)
        offset_list.append(offset)

    # Sort offsets into order of magnitude
    offset_list.sort()

    # Sum the offsets
    accumulator = sum(offset_list)

    # Debugging
    # logging.info("{:10e} -- {}".format(accumulator, list(params)))

    # Return result
    return accumulator


def read_input_data(filename: str, show_warnings: bool = True):
    # Read input list of stars whose positions we know
    input_config = json.loads(open(filename).read())
    # Get dimensions of the image we are dealing with
    img_size_x = input_config['size_x']
    img_size_y = input_config['size_y']
    # Look up positions of each star, based on listed Hipparcos catalogue numbers
    star_list = []
    for star in input_config['star_list']:
        hipparcos_id = str(star[2])
        if hipparcos_id not in hipparcos_catalogue:
            if show_warnings:
                logging.info("Could not find star {:s}".format(hipparcos_id))
            continue
        [ra, dec] = hipparcos_catalogue[hipparcos_id]
        star_list.append({
            'xpos': int(star[0]) / img_size_x,
            'ypos': int(star[1]) / img_size_y,
            'ra': ra * degrees,
            'dec': dec * degrees
        })
    return img_size_x, img_size_y, input_config, star_list


def list_calibration_files(fit_all: bool = False):
    calibration_files = {}
    inputs = glob.glob("calibration_examples/*.json")
    inputs.sort()

    for filename in inputs:
        img_size_x, img_size_y, input_config, star_list = read_input_data(filename=filename, show_warnings=False)
        setup = "{}/{}".format(input_config['observatory'], input_config['lens'])
        star_count = len(star_list)

        if setup not in calibration_files:
            calibration_files[setup] = []

        calibration_files[setup].append({
            'filename': os.path.split(filename)[1],
            'star_count': star_count
        })

    setups = list(calibration_files.keys())
    setups.sort()

    for setup in setups:
        logging.info("* {}".format(setup))
        for calibration_file in calibration_files[setup]:
            logging.info("    {} ({:3d} stars)".format(calibration_file['filename'], calibration_file['star_count']))

            if fit_all:
                ra0, dec0, scale_x, scale_y, pos_ang, bc_k1, bc_k2, bc_k3 = calibrate_lens(
                    filename=os.path.join("calibration_examples", calibration_file['filename']),
                    verbose=False)
                logging.info(
                    "{:8.4f} {:8.4f} {:8.4f}  --  {:10.6f} {:10.6f} {:10.6f}".format(scale_x * 180 / pi,
                                                                                     scale_y * 180 / pi,
                                                                                     pos_ang * 180 / pi,
                                                                                     bc_k1, bc_k2, bc_k3
                                                                                     )
                )


def calibrate_lens(filename: str, verbose: bool = True):
    global parameter_scales, star_list

    img_size_x, img_size_y, input_config, star_list = read_input_data(filename=filename, show_warnings=verbose)

    # Solve system of equations to give best fit barrel correction
    # See <http://www.scipy-lectures.org/advanced/mathematical_optimization/> for more information about how this works
    ra0 = star_list[0]['ra']
    dec0 = star_list[0]['dec']
    parameter_scales = [pi / 4, pi / 4, pi / 4, pi / 4, pi / 4, 5e-2, 5e-4, 5e-6]
    parameter_defaults = [ra0, dec0, pi / 4, pi / 4, pi / 4, 0, 0, 0]
    parameter_initial = [parameter_defaults[i] / parameter_scales[i] for i in range(len(parameter_defaults))]
    parameter_optimised = scipy.optimize.minimize(mismatch, parameter_initial, method='nelder-mead',
                                                  options={'xtol': 1e-8, 'disp': verbose, 'maxiter': 1e8, 'maxfev': 1e8}
                                                  ).x
    parameter_final = [parameter_optimised[i] * parameter_scales[i] for i in range(len(parameter_defaults))]

    # Display best fit numbers
    headings = [["Central RA / hr", 12 / pi], ["Central Decl / deg", 180 / pi],
                ["Image width / deg", 180 / pi], ["Image height / deg", 180 / pi],
                ["Position angle / deg", 180 / pi],
                ["barrel_k1", 1], ["barrel_k2", 1], ["barrel_k3", 1]
                ]

    if verbose:
        logging.info("Lens: {}".format(input_config['lens']))
        logging.info("Best fit parameters were:")
        for i in range(len(parameter_defaults)):
            logging.info("{:30s} : {:.8f}".format(headings[i][0], parameter_final[i] * headings[i][1]))

        # Print barrel_parameters JSON string
        logging.info("Barrel parameters: {}".format(json.dumps([
            parameter_final[2] * 180 / pi,
            parameter_final[3] * 180 / pi,
            parameter_final[5],
            parameter_final[6],
            parameter_final[7],
        ])))

    # Print information about how well each star was fitted
    [ra0, dec0, scale_x, scale_y, pos_ang, bc_k1, bc_k2, bc_k3] = parameter_final
    if verbose:
        logging.info("Stars used in fitting process:")
        for star in star_list:
            pos = gnomonic_project(ra=star['ra'], dec=star['dec'], ra0=ra0, dec0=dec0,
                                   size_x=1, size_y=1, scale_x=scale_x, scale_y=scale_y, pos_ang=pos_ang,
                                   barrel_k1=bc_k1, barrel_k2=bc_k2, barrel_k3=bc_k3)
            distance = hypot((star['xpos'] - pos[0]) * img_size_x, (star['ypos'] - pos[1]) * img_size_y)
            logging.info("""
User-supplied position ({:4.0f},{:4.0f}). Model position ({:4.0f},{:4.0f}). Mismatch {:5.1f} pixels.
""".format(star['xpos'] * img_size_x,
           star['ypos'] * img_size_y,
           pos[0] * img_size_x,
           pos[1] * img_size_y,
           distance).strip())

    # Debugging: print list of point offsets
    with open("/tmp/point_offsets.dat", "w") as output:
        for star in star_list:
            pos = gnomonic_project(ra=star['ra'], dec=star['dec'], ra0=ra0, dec0=dec0,
                                   size_x=1, size_y=1, scale_x=scale_x, scale_y=scale_y, pos_ang=pos_ang,
                                   barrel_k1=bc_k1, barrel_k2=bc_k2, barrel_k3=bc_k3)
            output.write("{:4.0f} {:4.0f}    {:4.0f} {:4.0f}\n".format(star['xpos'] * img_size_x,
                                                                       star['ypos'] * img_size_y,
                                                                       pos[0] * img_size_x,
                                                                       pos[1] * img_size_y))

    # Debugging: print graph of radial distortion
    with open("/tmp/radial_distortion.dat", "w") as output:
        output.write(
            "# x/pixel, y/pixel, offset/pixel, radius/pixel , Angular distance/rad , Tangent-space distance , Barrel-corrected tan-space dist")
        for star in star_list:
            pos = gnomonic_project(ra=star['ra'], dec=star['dec'], ra0=ra0, dec0=dec0,
                                   size_x=1, size_y=1, scale_x=scale_x, scale_y=scale_y, pos_ang=pos_ang,
                                   barrel_k1=bc_k1, barrel_k2=bc_k2, barrel_k3=bc_k3)

            # Error in the projected position of this star (pixels)
            offset = hypot((star['xpos'] - pos[0]) * img_size_x, (star['ypos'] - pos[1]) * img_size_y)

            # Angular distance of this star from the centre of the field (rad)
            angular_distance = ang_dist(ra1=star['ra'], dec1=star['dec'], ra0=ra0, dec0=dec0)

            # Pixel distance of this star from the centre of the field (pixels)
            pixel_distance = hypot((star['xpos'] - 0.5) * img_size_x, (star['ypos'] - 0.5) * img_size_y)
            pixel_distance_square_pixels = hypot((star['xpos'] - 0.5) * img_size_x,
                                                 (star['ypos'] - 0.5) * img_size_x * tan(scale_y / 2.) / tan(
                                                     scale_x / 2.))

            # Distance of this star from the centre of the field (tangent space)
            tan_distance = tan(angular_distance)

            # Apply barrel correction to the radial distance of this star in tangent space
            r = tan_distance / tan(scale_x / 2)
            bc_kn = 1. - bc_k1 - bc_k2 - bc_k3
            r2 = r * (bc_kn + bc_k1 * (r ** 2) + bc_k2 * (r ** 4) + bc_k3 * (r ** 6))

            barrel_corrected_tan_dist = r2 * img_size_x / 2

            output.write("{:4.0f} {:4.0f} {:8.4f} {:8.4f} {:8.4f} {:8.4f} {:8.4f}\n".format(
                star['xpos'] * img_size_x,
                star['ypos'] * img_size_y,
                offset,
                pixel_distance_square_pixels,
                angular_distance * 180 / pi,
                tan_distance / tan(scale_x / 2) * img_size_x / 2,
                barrel_corrected_tan_dist
            ))

    # Return final best-fit parameters
    return ra0, dec0, scale_x, scale_y, pos_ang, bc_k1, bc_k2, bc_k3


# If we're called as a script, run the function calibrate_lens()
if __name__ == "__main__":
    # Read commandline arguments
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument('--filename', dest='filename', default=None,
                        help="The filename of the calibration file we are to use")
    parser.add_argument('--list', dest='list', action='store_true', help="List all available calibration files")
    parser.add_argument('--no-list', dest='list', action='store_false')
    parser.set_defaults(list=False)
    parser.add_argument('--fit-all', dest='fit_all', action='store_true', help="Fit all available calibration files")
    parser.add_argument('--no-fit-all', dest='fit_all', action='store_false')
    parser.set_defaults(fit_all=False)
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
    if args.list:
        list_calibration_files(fit_all=False)
    elif args.fit_all:
        list_calibration_files(fit_all=True)
    elif args.filename is not None:
        calibrate_lens(filename=args.filename)
