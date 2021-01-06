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

import numpy
import scipy.optimize
from pigazing_helpers.gnomonic_project import gnomonic_project, ang_dist
from pigazing_helpers.settings_read import settings

degrees = pi / 180

# Parameters we use to fit the radial distortion
parameters_radial = [
    {
        'name': 'aspect',
        'title': 'Aspect ratio',
        'stored_unit': '',
        'display_scale': 1,
        'step_size': 0.1,
        'default': 1

    },
    {
        'name': 'k1',
        'title': 'barrel_k1',
        'stored_unit': '',
        'display_scale': 1,
        'step_size': 5e-2,
        'default': 0
    },
    {
        'name': 'k2',
        'title': 'barrel_k2',
        'stored_unit': '',
        'display_scale': 1,
        'step_size': 5e-4,
        'default': 0
    },
    {
        'name': 'k3',
        'title': 'barrel_k3',
        'stored_unit': '',
        'display_scale': 1,
        'step_size': 5e-6,
        'default': 0
    }
]

# Parameters we use to fit individual images
parameters_image = [
    {
        'name': 'ra',
        'title': 'Central RA / hr',
        'stored_unit': 'rad',
        'display_scale': 12 / pi,
        'step_size': pi / 4,
        'default': 0
    },
    {
        'name': 'dec',
        'title': 'Central Decl / deg',
        'stored_unit': 'rad',
        'display_scale': 180 / pi,
        'step_size': pi / 4,
        'default': 0
    },
    {
        'name': 'width',
        'title': 'Image width / deg',
        'stored_unit': 'rad',
        'display_scale': 180 / pi,
        'step_size': pi / 8,
        'default': pi / 2
    },
    {
        'name': 'pa',
        'title': 'Position angle / deg',
        'stored_unit': 'rad',
        'display_scale': 180 / pi,
        'step_size': pi / 4,
        'default': pi / 4
    }
]

# Parameters we are using in this fitting run
# fitting_parameter_indices[name] = index
fitting_parameters = {}
fitting_parameter_indices = {}
fitting_parameter_names = []
fitting_star_list = None
fitting_filename_list = []
parameters_final = []

# Read Hipparcos catalogue of stars brighter than mag 5.5
hipparcos_catalogue = json.loads(open("hipparcos_catalogue.json").read())


def mismatch(params_unnormalised):
    """
    The objective function which is optimized to fit the barrel-distortion coefficients of the image.

    :param params:
        A vector, containing trial parameter values, each normalised in units of <param_scales>
    :return:
        A measure of the mismatch of this proposed image orientation, based on the list of pixel positions and
        calculated (RA, Dec) positions contained within <fit_list>.
    """
    global fitting_filename_list, fitting_star_list, fitting_parameters, fitting_parameter_indices

    parameters_scale = [fitting_parameters[key]['step_size'] for key in fitting_parameter_names]
    params = [params_unnormalised[i] * parameters_scale[i] for i in range(len(fitting_parameter_names))]

    offset_list = []

    for index, filename in enumerate(fitting_filename_list):
        ra0 = params[fitting_parameter_indices["{}_{}".format(filename, 'ra')]]
        dec0 = params[fitting_parameter_indices["{}_{}".format(filename, 'dec')]]
        scale_x = params[fitting_parameter_indices["{}_{}".format(filename, 'width')]]
        scale_y = scale_x * params[fitting_parameter_indices['aspect']]
        pos_ang = params[fitting_parameter_indices["{}_{}".format(filename, 'pa')]]
        k1 = params[fitting_parameter_indices['k1']]
        k2 = params[fitting_parameter_indices['k2']]
        k3 = params[fitting_parameter_indices['k3']]

        for star in fitting_star_list[index]:
            pos = gnomonic_project(ra=star['ra'], dec=star['dec'], ra0=ra0, dec0=dec0,
                                   size_x=1, size_y=1, scale_x=scale_x, scale_y=scale_y, pos_ang=pos_ang,
                                   barrel_k1=k1, barrel_k2=k2, barrel_k3=k3)
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
    global parameters_final, fitting_parameter_indices

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
                filename = os.path.join("calibration_examples", calibration_file['filename'])
                calibrate_lens(filenames=[filename],
                               verbose=False
                               )

                scale_x = parameters_final[fitting_parameter_indices["{}_{}".format(filename, 'width')]]
                scale_y = scale_x * parameters_final[fitting_parameter_indices['aspect']]
                pos_ang = parameters_final[fitting_parameter_indices["{}_{}".format(filename, 'pa')]]
                k1 = parameters_final[fitting_parameter_indices['k1']]
                k2 = parameters_final[fitting_parameter_indices['k2']]
                k3 = parameters_final[fitting_parameter_indices['k3']]

                logging.info("{:8.4f} {:8.4f} {:8.4f}  --  {:10.6f} {:10.6f} {:10.6f}".format(
                    scale_x * 180 / pi,
                    scale_y * 180 / pi,
                    pos_ang * 180 / pi,
                    k1, k2, k3
                )
                )


def calibrate_lens(filenames: list, verbose: bool = True, diagnostics_run_id=None):
    global parameters_radial, parameters_image
    global fitting_parameters, fitting_parameter_indices, fitting_parameter_names
    global fitting_star_list, fitting_filename_list
    global parameters_final

    img_size_x = []
    img_size_y = []
    input_config = []
    star_list = []

    # Start creating list of parameters we are to fit
    fitting_parameters = {}
    fitting_parameter_indices = {}
    fitting_parameter_names = []
    fitting_star_list = None

    # This fitting run will require radial distortion parameters
    for item in parameters_radial:
        parameter_index = len(fitting_parameters)
        fitting_parameters[item['name']] = item.copy()
        fitting_parameters[item['name']]['image'] = None
        fitting_parameter_indices[item['name']] = parameter_index
        fitting_parameter_names.append(item['name'])

    # Read input data files, and create fitting variables associated with each image
    for filename in filenames:
        image_info = read_input_data(filename=filename, show_warnings=verbose)
        img_size_x.append(image_info[0])
        img_size_y.append(image_info[1])
        input_config.append(image_info[2])
        star_list.append(image_info[3])

        for item in parameters_image:
            parameter_index = len(fitting_parameters)
            key = "{}_{}".format(filename, item['name'])
            fitting_parameters[key] = item.copy()
            fitting_parameters[key]['image'] = filename
            fitting_parameter_indices[key] = parameter_index
            fitting_parameter_names.append(key)

    fitting_star_list = star_list
    fitting_filename_list = filenames

    # Populate the default RA / Dec associated with each image
    for index, filename in enumerate(filenames):
        ra0 = star_list[index][0]['ra']
        dec0 = star_list[index][0]['dec']
        key_ra = "{}_{}".format(filename, 'ra')
        fitting_parameters[key_ra]['default'] = ra0
        key_dec = "{}_{}".format(filename, 'dec')
        fitting_parameters[key_dec]['default'] = dec0

    # Create list of parameters we are to fit
    parameters_scale = [fitting_parameters[key]['step_size'] for key in fitting_parameter_names]

    parameters_initial = [fitting_parameters[key]['default'] / fitting_parameters[key]['step_size']
                          for key in fitting_parameter_names]

    # Solve system of equations to give best fit radial distortion
    # See <http://www.scipy-lectures.org/advanced/mathematical_optimization/> for more information about how this works
    parameters_optimised = scipy.optimize.minimize(mismatch, numpy.asarray(parameters_initial),
                                                   method='nelder-mead',
                                                   options={'xtol': 1e-8, 'disp': verbose, 'maxiter': 1e8,
                                                            'maxfev': 1e8}
                                                   ).x
    parameters_final = [parameters_optimised[i] * parameters_scale[i] for i in range(len(fitting_parameter_names))]

    # Display best fit parameter values
    if verbose:
        logging.info("Observatory: {}".format([item['observatory'] for item in input_config]))
        logging.info("Lens: {}".format([item['lens'] for item in input_config]))
        logging.info("Best fit parameters were:")
        for index, key in enumerate(fitting_parameter_names):
            logging.info("{:30s} : {:.8f}".format(
                fitting_parameters[key]['title'],
                parameters_final[index] * fitting_parameters[key]['display_scale']
            ))

        # Print barrel_parameters JSON string
        logging.info("Barrel parameters: {}".format(json.dumps([
            (parameters_final[fitting_parameter_indices[item['name']]] *
             fitting_parameters[item['name']]['display_scale'])
            for item in parameters_radial
        ])))

    # Print information about how well each star was fitted
    if verbose:
        for index, filename in enumerate(filenames):
            ra0 = parameters_final[fitting_parameter_indices["{}_{}".format(filename, 'ra')]]
            dec0 = parameters_final[fitting_parameter_indices["{}_{}".format(filename, 'dec')]]
            scale_x = parameters_final[fitting_parameter_indices["{}_{}".format(filename, 'width')]]
            scale_y = scale_x * parameters_final[fitting_parameter_indices['aspect']]
            pos_ang = parameters_final[fitting_parameter_indices["{}_{}".format(filename, 'pa')]]
            k1 = parameters_final[fitting_parameter_indices['k1']]
            k2 = parameters_final[fitting_parameter_indices['k2']]
            k3 = parameters_final[fitting_parameter_indices['k3']]

            logging.info("Image <{}>".format(filename))
            logging.info("Stars used in fitting process:")

            for star in star_list[index]:
                pos = gnomonic_project(
                    ra=star['ra'], dec=star['dec'],
                    ra0=ra0, dec0=dec0,
                    size_x=1, size_y=1,
                    scale_x=scale_x, scale_y=scale_y,
                    pos_ang=pos_ang,
                    barrel_k1=k1, barrel_k2=k2, barrel_k3=k3
                )
                distance = hypot((star['xpos'] - pos[0]) * img_size_x[index],
                                 (star['ypos'] - pos[1]) * img_size_y[index])

                logging.info("""
User-supplied position ({:4.0f},{:4.0f}). Model position ({:4.0f},{:4.0f}). Mismatch {:5.1f} pixels.
""".format(star['xpos'] * img_size_x[index],
           star['ypos'] * img_size_y[index],
           pos[0] * img_size_x[index],
           pos[1] * img_size_y[index],
           distance
           ).strip())

    # Debugging: output list of point offsets
    if diagnostics_run_id is not None:
        output_filename = "/tmp/point_offsets_{}.dat".format(diagnostics_run_id)
        with open(output_filename, "w") as output:
            output.write("# x_user_input y_user_input x_model y_model\n")
            for index, filename in enumerate(filenames):
                output.write("\n\n")
                ra0 = parameters_final[fitting_parameter_indices["{}_{}".format(filename, 'ra')]]
                dec0 = parameters_final[fitting_parameter_indices["{}_{}".format(filename, 'dec')]]
                scale_x = parameters_final[fitting_parameter_indices["{}_{}".format(filename, 'width')]]
                scale_y = scale_x * parameters_final[fitting_parameter_indices['aspect']]
                pos_ang = parameters_final[fitting_parameter_indices["{}_{}".format(filename, 'pa')]]
                k1 = parameters_final[fitting_parameter_indices['k1']]
                k2 = parameters_final[fitting_parameter_indices['k2']]
                k3 = parameters_final[fitting_parameter_indices['k3']]

                for star in star_list[index]:
                    pos = gnomonic_project(ra=star['ra'], dec=star['dec'], ra0=ra0, dec0=dec0,
                                           size_x=1, size_y=1, scale_x=scale_x, scale_y=scale_y, pos_ang=pos_ang,
                                           barrel_k1=k1, barrel_k2=k2, barrel_k3=k3)
                    output.write("{:4.0f} {:4.0f}    {:4.0f} {:4.0f}\n".format(star['xpos'] * img_size_x[index],
                                                                               star['ypos'] * img_size_y[index],
                                                                               pos[0] * img_size_x[index],
                                                                               pos[1] * img_size_y[index]))

    # Debugging: print graph of radial distortion
    if diagnostics_run_id is not None:
        output_filename = "/tmp/radial_distortion_{}.dat".format(diagnostics_run_id)
        with open(output_filename, "w") as output:
            output.write("# x/pixel, y/pixel, offset/pixel, radius/pixel , Angular distance/rad , "
                         "Tangent-space distance , Barrel-corrected tan-space dist\n")

            for index, filename in enumerate(filenames):
                output.write("\n\n")
                ra0 = parameters_final[fitting_parameter_indices["{}_{}".format(filename, 'ra')]]
                dec0 = parameters_final[fitting_parameter_indices["{}_{}".format(filename, 'dec')]]
                scale_x = parameters_final[fitting_parameter_indices["{}_{}".format(filename, 'width')]]
                scale_y = scale_x * parameters_final[fitting_parameter_indices['aspect']]
                pos_ang = parameters_final[fitting_parameter_indices["{}_{}".format(filename, 'pa')]]
                k1 = parameters_final[fitting_parameter_indices['k1']]
                k2 = parameters_final[fitting_parameter_indices['k2']]
                k3 = parameters_final[fitting_parameter_indices['k3']]

                for star in star_list[index]:
                    pos = gnomonic_project(ra=star['ra'], dec=star['dec'], ra0=ra0, dec0=dec0,
                                           size_x=1, size_y=1, scale_x=scale_x, scale_y=scale_y, pos_ang=pos_ang,
                                           barrel_k1=k1, barrel_k2=k2, barrel_k3=k3)

                    # Error in the projected position of this star (pixels)
                    offset = hypot((star['xpos'] - pos[0]) * img_size_x[index],
                                   (star['ypos'] - pos[1]) * img_size_y[index])

                    # Angular distance of this star from the centre of the field (rad)
                    angular_distance = ang_dist(ra1=star['ra'], dec1=star['dec'], ra0=ra0, dec0=dec0)

                    # Pixel distance of this star from the centre of the field (pixels)
                    pixel_distance = hypot((star['xpos'] - 0.5) * img_size_x[index],
                                           (star['ypos'] - 0.5) * img_size_y[index])
                    pixel_distance_square_pixels = hypot((star['xpos'] - 0.5) * img_size_x[index],
                                                         (star['ypos'] - 0.5) * img_size_x[index] *
                                                         tan(scale_y / 2.) / tan(scale_x / 2.))

                    # Distance of this star from the centre of the field (tangent space)
                    tan_distance = tan(angular_distance)

                    # Apply barrel correction to the radial distance of this star in tangent space
                    r = tan_distance / tan(scale_x / 2)
                    bc_kn = 1. - k1 - k2 - k3
                    r2 = r * (bc_kn + k1 * (r ** 2) + k2 * (r ** 4) + k3 * (r ** 6))

                    barrel_corrected_tan_dist = r2 * img_size_x[index] / 2

                    output.write("{:4.0f} {:4.0f} {:8.4f} {:8.4f} {:8.4f} {:8.4f} {:8.4f}\n".format(
                        star['xpos'] * img_size_x[index],
                        star['ypos'] * img_size_y[index],
                        offset,
                        pixel_distance_square_pixels,
                        angular_distance * 180 / pi,
                        tan_distance / tan(scale_x / 2) * img_size_x[index] / 2,
                        barrel_corrected_tan_dist
                    ))

        # Write pyxplot script to plot quality of fit
        output_filename = "/tmp/radial_distortion_{}.ppl".format(diagnostics_run_id)
        with open(output_filename, "w") as output:
            output.write("""
set width 30 ; set term png dpi 200
set output '/tmp/radial_distortion_{0}_a.png'
""".format(diagnostics_run_id))
            for index, filename in enumerate(filenames):
                output.write("""
f_{1}(x) = a + b * x ** 2 + c * x ** 4
fit f_{1}() withouterrors '/tmp/radial_distortion_{0}.dat' using 4:$6/$4 index {1} via a, b, c
""".format(diagnostics_run_id, index))
            output.write("plot ")
            for index, filename in enumerate(filenames):
                output.write("""\
'/tmp/radial_distortion_{0}.dat' using 4:$6/$4 index {1}, f_{1}(x), \
""".format( diagnostics_run_id, index))
            output.write("1\n")
            output.write("""
set output '/tmp/radial_distortion_{0}_b.png'
""".format(diagnostics_run_id))
            output.write("plot ")
            for index, filename in enumerate(filenames):
                output.write("""\
'/tmp/radial_distortion_{0}.dat' using 4:$7/$4 index {1}, \
'/tmp/radial_distortion_{0}.dat' using 4:$6/$4/f_{1}($4) index {1}, \
""".format(diagnostics_run_id, index))
            output.write("1\n")

        # Run pyxplot
        os.system("pyxplot /tmp/radial_distortion_{}.ppl".format(diagnostics_run_id))


# If we're called as a script, run the function calibrate_lens()
if __name__ == "__main__":
    # Read commandline arguments
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument('--filename', dest='filenames', action='append',
                        help="The filename of the calibration file(s) we are to use")
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
    elif args.filenames:
        calibrate_lens(filenames=args.filenames, diagnostics_run_id=0)
