#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# calibrate_lens_from_star_list.py
#
# -------------------------------------------------
# Copyright 2015-2021 Dominic Ford
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
This script models the radial lens distortion present in astronomical images.

It reads JSON files that contain lists of the pixel positions of known stars
within an image, and uses the known celestial coordinates of these stars to fit
for the orientation of the image on the sky, the field of view of the image,
and the radial distortion in the image.  These input files need to be produced
manually by comparing images recorded by the lens with a star chart or
planetarium program.

The JSON files in the directory <calibration_examples> provide examples of the
format this input file should take. Metadata such as the URL of the image being
fitted, and the name of the camera and lens, may be filled out as the user
wishes, and are copied verbatim into the output from this tool.  The position
of each star should be specified by a list of:

[x pixel position, y pixel position, hipparcos number].

This tool uses a version of the Hipparcos catalogue which is only complete to
mag 5.5, and so only stars brighter than this magnitude limit will be used in
the fitting process. When used to fit the radial distortion in a cheap CCTV
lens used in a meteor camera, the positions of roughly 100-120 stars are needed
to obtain positional accuracy of ~ 1 pixel across the field of view.

The radial distortion is modelled using a polynomial of the form:

R = r * (k0 + k1 * r^2 + k2 * r^4 + k3 * r^6)

where

R is the observed pixel distance of the star from the centre of the image,
measured in units of the half-width of the image.

r is the theoretically predicted distance of the star from the centre of the
image, measured in units of the half-width of the image, assuming an ideal
lens.

k1, k2 and k3 are free parameters.

k0 = 1 - k1 - k2 - k3. This (arbitrary) normalisation ensures that the
celestial coordinates of the points half-way down the left and right edges of
the image are unchanged by the distortion model, so that the horizontal field
of view of the image is unaffected by the radial distortion model.

-----
Usage
-----

# List all available configuration files in <calibration_examples>
./calibrate_lens_from_star_list.py --list

# Sequentially fit all available configuration files in <calibration_examples>
./calibrate_lens_from_star_list.py --fit-all

# Fit a single configuration file, with detailed diagnostics about the quality
# of fit to each individual star. This mode of operation is useful for checking
# configuration files for typos in star positions
./calibrate_lens_from_star_list.py --filename calibration_examples/20201213_023200_d680725b5f4d.png.json

# Simultanaeously fit a lens using multiple images. The images may have
# different pointings, but are assumed to share the same lens distortions
/calibrate_lens_from_star_list.py --filename calibration_examples/20201213_011600_f8134fd1f2bc.png.json --filename calibration_examples/20201231_213600_202b3e214f7a.png.json


The best-fit parameter values are returned to the user. If they are believed to
be good, you should record the lens distortion parameters in the file
<pi-gazing/configuration_global/camera_properties/lenses.xml>. Then future
analysis of images from the named lens will use the observations will correct
for this lens distortion.

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

# List of the parameters we use to fit the radial distortion
# Regardless of how many images we are asked to simultaneously fit, these parameters are assumed to take common values
# in all the images
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

# List of the parameters we use to fit the orientation of individual images on the sky
# When we fit multiple images simultaneously, each image can take different values for these parameters
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

# Read Hipparcos catalogue of stars brighter than mag 5.5
hipparcos_catalogue = json.loads(open("hipparcos_catalogue.json").read())

# Global list of the all the parameters we are currently fitting
# Since some parameters are repeated multiple times, we add prefixes to their names,
# e.g. "filename1_pa", "filename2_pa", etc

# These have to be global variables (yuck) so that the objective function <mismatch> used by the optimizer can identify
# which parameters each trial value should be assigned to.

fitting_parameters = {}  # fitting_parameters[parameter_name] = dictionary of info about the parameter (see above)
fitting_parameter_indices = {}  # fitting_parameter_indices[parameter_name] = index
fitting_parameter_names = []  # fitting_parameter_names[index] = parameter_name
fitting_star_list = None  # Ordered list of [lists of stars] within each image we are currently fitting
fitting_filename_list = []  # Filenames of all the images we are currently fitting
parameters_final = []  # The final best-fit parameters yielded by the optimisation process


def mismatch(params_unnormalised):
    """
    The objective function which is optimized to fit the radial lens distortion coefficients of the image(s).

    :param params_unnormalised:
        A vector, containing trial parameter values, each normalised in units of <param_scales>
    :return:
        A measure of the mismatch of this proposed image orientation, based on the list of pixel positions and
        calculated (RA, Dec) positions contained within <fitting_star_list>.
    """
    global fitting_filename_list, fitting_star_list, fitting_parameters, fitting_parameter_indices

    # Look up the normalisation of each trial value we have been passed
    parameters_scale = [fitting_parameters[key]['step_size'] for key in fitting_parameter_names]

    # Convert the vector of trial values from units of optimiser-steps into scientifically useful units
    params = [params_unnormalised[i] * parameters_scale[i] for i in range(len(fitting_parameter_names))]

    # Build a list of the offsets of the theoretically calculated position of every star from where the user
    # measured it to be
    offset_list = []

    # Loop over all of the images we are simultaneously fitting
    for index, filename in enumerate(fitting_filename_list):
        # Extract all of the parameters which control the orientation of this image on the sky
        ra0 = params[fitting_parameter_indices["{}_{}".format(filename, 'ra')]]  # Central RA
        dec0 = params[fitting_parameter_indices["{}_{}".format(filename, 'dec')]]  # Central declination
        scale_x = params[fitting_parameter_indices["{}_{}".format(filename, 'width')]]  # Horizontal width of image
        scale_y = scale_x * params[fitting_parameter_indices['aspect']]  # Vertical height of image
        pos_ang = params[fitting_parameter_indices["{}_{}".format(filename, 'pa')]]  # Position angle of image

        # Extract parameters which control the radial distortion of this image
        k1 = params[fitting_parameter_indices['k1']]
        k2 = params[fitting_parameter_indices['k2']]
        k3 = params[fitting_parameter_indices['k3']]

        # Loop over all the stars in this image
        for star in fitting_star_list[index]:
            # Calculating the pixel coordinates where we expect to find this star, theoretically
            pos = gnomonic_project(ra=star['ra'], dec=star['dec'], ra0=ra0, dec0=dec0,
                                   size_x=1, size_y=1, scale_x=scale_x, scale_y=scale_y, pos_ang=pos_ang,
                                   barrel_k1=k1, barrel_k2=k2, barrel_k3=k3)

            # If this star is more than 90 degrees from the centre of the field of view, no lens could possibly see it
            if not (isfinite(pos[0]) and isfinite(pos[1])):
                return float('NaN')

            # Record the square of the pixel offset between the theoretical and observed positions of this star
            offset = pow(hypot(star['xpos'] - pos[0], star['ypos'] - pos[1]), 2)
            offset_list.append(offset)

    # Sort the pixel offsets by magnitude
    offset_list.sort()

    # Sum the square offsets in the positions of all the stars
    accumulator = sum(offset_list)

    # Debugging
    # logging.info("{:10e} -- {}".format(accumulator, list(params)))

    # Return result
    return accumulator


def read_input_data(filename: str, show_warnings: bool = True):
    """
    Read a JSON input file describing the observed positions of stars in an image to be calibrated.

    :param filename:
        The filename of the JSON file we are to read
    :type filename:
        str
    :param show_warnings:
        Boolean switch indicating whether we should issue warnings about stars with unknown Hipparcos numbers (and
        which are probably fainter than mag 5.5, but which might also be typos).
    :type show_warnings:
        bool
    :return:
        [Horizontal pixel width of image, Vertical pixel width of image, Full JSON structure, List of stars]
    """
    # Read input data structure describing the image that we are to calibrate
    input_config = json.loads(open(filename).read())

    # Get dimensions of the image we are working on
    img_size_x = input_config['size_x']
    img_size_y = input_config['size_y']

    # Build a list of all the reference stars in this image
    star_list = []
    for star in input_config['star_list']:
        # Look up the Hipparcos catalogue number of this star
        hipparcos_id = str(star[2])
        if hipparcos_id not in hipparcos_catalogue:
            if show_warnings:
                logging.info("Could not find star {:s}".format(hipparcos_id))
            continue

        # Look up the celestial coordinates of this reference star (degrees)
        [ra, dec] = hipparcos_catalogue[hipparcos_id]

        # Build a list of dictionaries of metadata about each reference star
        star_list.append({
            'xpos': int(star[0]) / img_size_x,  # units of image widths
            'ypos': int(star[1]) / img_size_y,  # units of image heights
            'ra': ra * degrees,  # units of radians
            'dec': dec * degrees  # units of radians
        })

    # Return output
    return img_size_x, img_size_y, input_config, star_list


def list_calibration_files(fit_all: bool = False):
    """
    Produce a list of all the JSON configuration files available in the <calibration_examples> directory, grouping
    together configuration files which refer to the same camera/lens combination, for easy comparison.

    :param fit_all:
        Boolean flag indicating whether we should attempt to fit each configuration file as we list it.
    :type fit_all:
        bool
    :return:
        None
    """
    global parameters_final, fitting_parameter_indices

    # List of all available configuration files, indexed by camera/lens combination
    calibration_files = {}

    # Create an alphabetically-sorted list of all available JSON configuration files
    inputs = glob.glob("calibration_examples/*.json")
    inputs.sort()

    # Loop through each configuration file in turn
    for filename in inputs:
        # Read input JSON data structure
        img_size_x, img_size_y, input_config, star_list = read_input_data(filename=filename, show_warnings=False)

        # Create a string which uniquely identifies this camera/lens combination
        setup = "{}/{}".format(input_config['observatory'], input_config['lens'])
        star_count = len(star_list)

        # For each camera/lens combination, store a list of the configuration files for that setup
        if setup not in calibration_files:
            calibration_files[setup] = []

        calibration_files[setup].append({
            'filename': os.path.split(filename)[1],
            'star_count': star_count
        })

    # Create alphabetical list of all available camera/lens combinations
    setups = list(calibration_files.keys())
    setups.sort()

    # List each camera/lens combination in turn
    for i, setup in enumerate(setups):
        logging.info("* {}".format(setup))

        # For each setup, list all the available configuration files in turn
        for j, calibration_file in enumerate(calibration_files[setup]):
            logging.info("    {} ({:3d} stars)".format(calibration_file['filename'], calibration_file['star_count']))

            # If we are also fitting each configuration file, do that now, and display the best-fit parameters
            if fit_all:
                # Fit this configuration file
                filename = os.path.join("calibration_examples", calibration_file['filename'])
                calibrate_lens(filenames=[filename],
                               verbose=False,
                               diagnostics_run_id="{:d}_{:d}".format(i, j)
                               )

                # Extract the best-fit parameters which were fitted to this configuration file
                scale_x = parameters_final[fitting_parameter_indices["{}_{}".format(filename, 'width')]]
                scale_y = scale_x * parameters_final[fitting_parameter_indices['aspect']]
                pos_ang = parameters_final[fitting_parameter_indices["{}_{}".format(filename, 'pa')]]
                k1 = parameters_final[fitting_parameter_indices['k1']]
                k2 = parameters_final[fitting_parameter_indices['k2']]
                k3 = parameters_final[fitting_parameter_indices['k3']]

                # Display [horizontal angular width, vertical angular height, k1, k2, k3]
                logging.info("[{:12.8f}, {:12.8f}, {:14.10f}, {:14.10f}, {:14.10f}]".format(
                    scale_x * 180 / pi,
                    scale_y * 180 / pi,
                    k1, k2, k3
                )
                )


def calibrate_lens(filenames: list, verbose: bool = True, diagnostics_run_id=None):
    """
    Calibrate the radial distortion and sky orientation of one image, or a group of images, taken from a particular
    lens / camera setup. If multiple images are passed, they may have different orientations on the sky, but are
    assumed to share the same radial distortions.

    The best fit parameters are displayed to stdout, and also stored in the global variable <parameters_final>.

    :param filenames:
        List of the JSON files describing the images we are to calibrate.
    :type filenames:
        List<str>
    :param verbose:
        Boolean switch indicating whether we produce diagnostic messages listing the quality of fit of
        each star listed.
    :type verbose:
        bool
    :param diagnostics_run_id:
        If set, we produce a series of PNG graphs in </tmp> illustrating the quality of the fit achieved in terms
        of the radial offset of the position of each star from its theoretically predicted position. If this shows
        systematic trends away from zero, it suggests that the radial distortion has been poorly fitted. The string
        value supplied here is appended as a suffix to all the image files, to distinguish them from other runs of
        this tool.
    :type diagnostics_run_id:
        str|int
    :return:
        None
    """

    # We store the details of the list of parameters we are currently fitting in global variables (yuck!) as they
    # need to be accessed by the objective function which does the function fitting.
    global parameters_radial, parameters_image
    global fitting_parameters, fitting_parameter_indices, fitting_parameter_names
    global fitting_star_list, fitting_filename_list
    global parameters_final

    # Details of all the images we are currently fitting
    img_size_x = []  # Horizontal pixel width of each image we are fitting
    img_size_y = []  # Vertical pixel height of each image we are fitting
    input_config = []  # The full JSON structures describing each image we are fitting
    star_list = []  # Lists of the stars in each image we are fitting

    # Start creating list of parameters we are to fit
    fitting_parameters = {}  # fitting_parameters[parameter_name] = dictionary of info about the parameter (see above)
    fitting_parameter_indices = {}  # fitting_parameter_indices[parameter_name] = index
    fitting_parameter_names = []  # fitting_parameter_names[index] = parameter_name
    fitting_star_list = None  # global copy of <star_list>

    # Compile a list of all the free parameters in this fitting run
    # All fitting runs require a single set of radial distortion parameters
    # We create descriptors for these parameters in <fitting_parameters> now
    for item in parameters_radial:
        parameter_index = len(fitting_parameters)
        fitting_parameters[item['name']] = item.copy()
        fitting_parameters[item['name']]['image'] = None  # These parameters do not refer to any single image
        fitting_parameter_indices[item['name']] = parameter_index
        fitting_parameter_names.append(item['name'])

    # For every image we are fitting, we need a separate set of parameters describing the image's orientation on the sky
    # We create descriptors for these parameters now
    for filename in filenames:
        # Read the JSON description for this image
        image_info = read_input_data(filename=filename, show_warnings=verbose)

        # Add this image to the list of images we are fitting
        img_size_x.append(image_info[0])
        img_size_y.append(image_info[1])
        input_config.append(image_info[2])
        star_list.append(image_info[3])

        # Create all the parameters in <fitting_parameters> which describe the orientation of this image on the sky
        for item in parameters_image:
            # Calculate the index that this parameter will take in the vector of trial values in the optimiser
            parameter_index = len(fitting_parameters)

            # Create a unique name for this parameter. We may have multiple images, so we prepend the image's filename
            # to the parameter name, to distinguish it from other images.
            key = "{}_{}".format(filename, item['name'])

            # Create parameter
            fitting_parameters[key] = item.copy()
            fitting_parameters[key]['image'] = filename
            fitting_parameter_indices[key] = parameter_index
            fitting_parameter_names.append(key)

    # Create global list of all the images we are fitting, and the stars within each image
    fitting_star_list = star_list
    fitting_filename_list = filenames

    # Set a sensible default RA / Dec for the centre of each image
    for index, filename in enumerate(filenames):
        # Use the first reference star in each image as a guesstimate of celestial coordinates of the centre
        ra0 = star_list[index][0]['ra']
        dec0 = star_list[index][0]['dec']
        key_ra = "{}_{}".format(filename, 'ra')
        fitting_parameters[key_ra]['default'] = ra0
        key_dec = "{}_{}".format(filename, 'dec')
        fitting_parameters[key_dec]['default'] = dec0

    # Create vectors of initial values, and step sizes, for each parameter we are to fit
    parameters_scale = [fitting_parameters[key]['step_size'] for key in fitting_parameter_names]

    parameters_initial = [fitting_parameters[key]['default'] / fitting_parameters[key]['step_size']
                          for key in fitting_parameter_names]

    # Solve the system of equations
    # See <http://www.scipy-lectures.org/advanced/mathematical_optimization/> for more information about how this works
    parameters_optimised = scipy.optimize.minimize(mismatch, numpy.asarray(parameters_initial),
                                                   options={'disp': verbose, 'maxiter': 1e8}
                                                   ).x

    # Extract the best-fitting set of parameter values, in physical units (not in units of optimiser step size)
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

        # Print JSON string describing the radial distortion model
        for index, filename in enumerate(filenames):
            scale_x = parameters_final[fitting_parameter_indices["{}_{}".format(filename, 'width')]]
            scale_y = scale_x * parameters_final[fitting_parameter_indices['aspect']]
            k1 = parameters_final[fitting_parameter_indices['k1']]
            k2 = parameters_final[fitting_parameter_indices['k2']]
            k3 = parameters_final[fitting_parameter_indices['k3']]
            logging.info("Barrel parameters: [{:12.8f}, {:12.8f}, {:14.10f}, {:14.10f}, {:14.10f}]".format(
                scale_x * 180 / pi,
                scale_y * 180 / pi,
                k1, k2, k3
            )
            )

    # In verbose mode, print detailed information about how well each star was fitted
    if verbose:
        # Loop over all of the images we are fitting
        for index, filename in enumerate(filenames):
            # Extract the parameter values relevant to this image
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

            # Print the quality of fit to each star individually
            for star in star_list[index]:
                # Calculate the theoretically predicted position of this star
                pos = gnomonic_project(
                    ra=star['ra'], dec=star['dec'],
                    ra0=ra0, dec0=dec0,
                    size_x=1, size_y=1,
                    scale_x=scale_x, scale_y=scale_y,
                    pos_ang=pos_ang,
                    barrel_k1=k1, barrel_k2=k2, barrel_k3=k3
                )

                # Calculate the offset between the theoretically predicted and observed positions of this star
                distance = hypot((star['xpos'] - pos[0]) * img_size_x[index],
                                 (star['ypos'] - pos[1]) * img_size_y[index])

                # Print diagnostic details for this star
                logging.info("""
User-supplied position ({:4.0f},{:4.0f}). Model position ({:4.0f},{:4.0f}). Mismatch {:5.1f} pixels.
""".format(star['xpos'] * img_size_x[index],
           star['ypos'] * img_size_y[index],
           pos[0] * img_size_x[index],
           pos[1] * img_size_y[index],
           distance
           ).strip())

    # Debugging: output a data file listing the observed and theoretical positions of each star
    if diagnostics_run_id is not None:
        # Create diagnostic data file in /tmp
        output_filename = "/tmp/point_offsets_{}.dat".format(diagnostics_run_id)
        with open(output_filename, "w") as output:
            # Column headings
            output.write("# x_user_input y_user_input x_model y_model\n")

            # Loop over all the images we are simultaneously fitting
            for index, filename in enumerate(filenames):
                # Leave a blank line between data points from different images
                output.write("\n\n")

                # Extract the parameter values relevant to this image
                ra0 = parameters_final[fitting_parameter_indices["{}_{}".format(filename, 'ra')]]
                dec0 = parameters_final[fitting_parameter_indices["{}_{}".format(filename, 'dec')]]
                scale_x = parameters_final[fitting_parameter_indices["{}_{}".format(filename, 'width')]]
                scale_y = scale_x * parameters_final[fitting_parameter_indices['aspect']]
                pos_ang = parameters_final[fitting_parameter_indices["{}_{}".format(filename, 'pa')]]
                k1 = parameters_final[fitting_parameter_indices['k1']]
                k2 = parameters_final[fitting_parameter_indices['k2']]
                k3 = parameters_final[fitting_parameter_indices['k3']]

                # Loop over all the stars in this image
                for star in star_list[index]:
                    # Calculate the theoretically predicted position of this star
                    pos = gnomonic_project(ra=star['ra'], dec=star['dec'], ra0=ra0, dec0=dec0,
                                           size_x=1, size_y=1, scale_x=scale_x, scale_y=scale_y, pos_ang=pos_ang,
                                           barrel_k1=k1, barrel_k2=k2, barrel_k3=k3)

                    # Output the theoretically predicted and observed positions of this star
                    output.write("{:4.0f} {:4.0f}    {:4.0f} {:4.0f}\n".format(star['xpos'] * img_size_x[index],
                                                                               star['ypos'] * img_size_y[index],
                                                                               pos[0] * img_size_x[index],
                                                                               pos[1] * img_size_y[index]))

    # Debugging: output a data file listing the theoretical and observed radial positions of each star
    if diagnostics_run_id is not None:
        # Create diagnostic data file in /tmp
        logging.info("Producing diagnostic file <{}>".format(diagnostics_run_id))
        output_filename = "/tmp/radial_distortion_{}.dat".format(diagnostics_run_id)
        with open(output_filename, "w") as output:
            # Column headings
            output.write("# x/pixel, y/pixel, offset/pixel, radius/pixel , Angular distance/rad , "
                         "Tangent-space distance , Barrel-corrected tan-space dist\n")

            # Loop over all the images we are simultaneously fitting
            for index, filename in enumerate(filenames):
                # Leave a blank line between data points from different images
                output.write("\n\n")

                # Extract the parameter values relevant to this image
                ra0 = parameters_final[fitting_parameter_indices["{}_{}".format(filename, 'ra')]]
                dec0 = parameters_final[fitting_parameter_indices["{}_{}".format(filename, 'dec')]]
                scale_x = parameters_final[fitting_parameter_indices["{}_{}".format(filename, 'width')]]
                scale_y = scale_x * parameters_final[fitting_parameter_indices['aspect']]
                pos_ang = parameters_final[fitting_parameter_indices["{}_{}".format(filename, 'pa')]]
                k1 = parameters_final[fitting_parameter_indices['k1']]
                k2 = parameters_final[fitting_parameter_indices['k2']]
                k3 = parameters_final[fitting_parameter_indices['k3']]

                # Loop over all the stars in this image
                for star in star_list[index]:
                    # Calculate the theoretically predicted position of this star
                    pos = gnomonic_project(ra=star['ra'], dec=star['dec'], ra0=ra0, dec0=dec0,
                                           size_x=1, size_y=1, scale_x=scale_x, scale_y=scale_y, pos_ang=pos_ang,
                                           barrel_k1=k1, barrel_k2=k2, barrel_k3=k3)

                    # Calculate the offset in the projected position of this star (pixels)
                    offset = hypot((star['xpos'] - pos[0]) * img_size_x[index],
                                   (star['ypos'] - pos[1]) * img_size_y[index])

                    # Calculate the angular distance of this star from the centre of the field (rad)
                    angular_distance = ang_dist(ra1=star['ra'], dec1=star['dec'], ra0=ra0, dec0=dec0)

                    # Calculate the pixel distance of this star from the centre of the field
                    # (horizontal pixels; after radial distortion)
                    pixel_distance = hypot(
                        (star['xpos'] - 0.5) * img_size_x[index],
                        (star['ypos'] - 0.5) * img_size_x[index] * tan(scale_y / 2.) / tan(scale_x / 2.)
                    )

                    # Calculate the distance of this star from the centre of the field
                    # (tangent space; before radial distortion)
                    tan_distance = tan(angular_distance)

                    # Apply radial correction to the position this star in tangent space
                    r = tan_distance / tan(scale_x / 2)
                    bc_kn = 1. - k1 - k2 - k3
                    r2 = r * (bc_kn + k1 * (r ** 2) + k2 * (r ** 4) + k3 * (r ** 6))

                    # Calculate the distance of this star from the centre of the field
                    # (tangent space; after radial distortion)
                    barrel_corrected_tan_dist = r2 * tan(scale_x / 2)

                    # Display diagnostic table of calculated values
                    output.write("{:4.0f} {:4.0f} {:8.4f} {:8.4f} {:8.4f} {:8.4f} {:8.4f}\n".format(
                        star['xpos'] * img_size_x[index],
                        star['ypos'] * img_size_y[index],
                        offset,
                        pixel_distance,
                        angular_distance * 180 / pi,
                        tan_distance / tan(scale_x / 2) * img_size_x[index] / 2,
                        barrel_corrected_tan_dist / tan(scale_x / 2) * img_size_x[index] / 2
                    ))

        # Write pyxplot script to plot quality of fit
        output_filename = "/tmp/radial_distortion_{}.ppl".format(diagnostics_run_id)
        with open(output_filename, "w") as output:
            output.write("""
set width 30 ; set term png dpi 100
set xlabel 'Distance from centre of field / pixels'
set ylabel 'Observed pixel distance from centre (after distortion) - Tan space distance (before distortion)'
set output '/tmp/radial_distortion_{0}_a.png'
""".format(diagnostics_run_id))
            for index, filename in enumerate(filenames):
                output.write("""
f_{1}(x) = a + b * x ** 2
# fit f_{1}() withouterrors '/tmp/radial_distortion_{0}.dat' using 4:$6/$4 index {1} via a, b
""".format(diagnostics_run_id, index))
            output.write("plot ")
            for index, filename in enumerate(filenames):
                output.write(
                    "'/tmp/radial_distortion_{0}.dat' using 4:$6-$4 index {1}, ".format(diagnostics_run_id, index))
                # output.write("f_{1}(x), ".format(diagnostics_run_id, index))
                output.write(
                    "'/tmp/radial_distortion_{0}.dat' using 4:$6-$7 index {1}, ".format(diagnostics_run_id, index))
            output.write("-1 notitle w col green lt 2, 0 notitle w col green lt 2, 1 notitle w col green lt 2\n")
            output.write("""
set ylabel 'Observed pixel distance from centre (after distortion) - Tan space distance (after distortion)'
set output '/tmp/radial_distortion_{0}_b.png'
""".format(diagnostics_run_id))
            output.write("plot ")
            for index, filename in enumerate(filenames):
                output.write(
                    "'/tmp/radial_distortion_{0}.dat' using 4:$7-$4 index {1}, ".format(diagnostics_run_id, index))
                # output.write("'/tmp/radial_distortion_{0}.dat' using 4:$6/f_{1}($4)-$4 index {1}, ".format(diagnostics_run_id, index))
            output.write("-1 notitle w col green lt 2, 0 notitle w col green lt 2, 1 notitle w col green lt 2\n")

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
