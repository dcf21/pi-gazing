#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# orientation_calculate.py
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
Use astrometry.net to calculate the orientation of a Pi Gazing observatory,
based on the positions of stars in still images recorded by that camera.

Pi Gazing observatories record still images once every 4 minutes, by stacking a
large number of video frames. Each image is rated according to its sky clarity
(estimated by the number of point sources in the image). We assume that each
observatory has a fixed pointing within any given night, and use all images
within that 24-hour period (with good sky clarity) to estimate the camera's
orientation.

When astrometry.net succeeds, we update the metadata associated with each
individual image to reflect the output of the plate solver. These metadata
fields are all prefixed <orientation:...>.
"""

import argparse
import json
import logging
import math
import os
import re
import subprocess
import time
from math import pi, hypot
from operator import itemgetter
from PIL import Image

import dask
import numpy as np
from pigazing_helpers import connect_db, gnomonic_project, hardware_properties
from pigazing_helpers.dcf_ast import date_string, ra_dec_from_j2000, ra_dec_to_j2000
from pigazing_helpers.obsarchive import obsarchive_model as mp, obsarchive_db, obsarchive_sky_area
from pigazing_helpers.obsarchive.obsarchive_sky_area import get_sky_area
from pigazing_helpers.settings_read import settings, installation_info
from pigazing_helpers.sunset_times import alt_az, get_zenith_position

# Mathematical constants
hours = pi / 12
deg = pi / 180
rad = 180 / pi

block_size = 120  # We fit the best image within ever 120 second period of time (i.e. all images!)
minimum_sky_clarity = 300  # We only try to fit images with a sky clarity of at least 300

hipparcos_catalogue = None


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


def sgn(x):
    """
    Return the sign of a numerical value.

    :param x:
        The number to test
    :return:
        -1 if the number is less than zero
        0 if the number is zero
        1 if the number is greater than zero
    """
    if x < 0:
        return -1
    if x > 0:
        return 1
    return 0


def orientation_calc(obstory_id, utc_min, utc_max, utc_must_stop=None):
    """
    Use astrometry.net to determine the orientation of a particular observatory within each night within the time
    period between the unix times <utc_min> and <utc_max>.

    :param obstory_id:
        The ID of the observatory we want to determine the orientation for.
    :type obstory_id:
        str
    :param utc_min:
        The start of the time period in which we should determine the observatory's orientation (unix time).
    :type utc_min:
        float
    :param utc_max:
        The end of the time period in which we should determine the observatory's orientation (unix time).
    :type utc_max:
        float
    :param utc_must_stop:
        The unix time after which we must abort and finish work as quickly as possible.
    :type utc_must_stop:
        float
    :return:
        None
    """

    # Open connection to database
    [db0, conn] = connect_db.connect_db()

    # Open connection to image archive
    db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                           db_host=installation_info['mysqlHost'],
                                           db_user=installation_info['mysqlUser'],
                                           db_password=installation_info['mysqlPassword'],
                                           db_name=installation_info['mysqlDatabase'],
                                           obstory_id=installation_info['observatoryId'])

    logging.info("Starting calculation of camera alignment for <{}>".format(obstory_id))

    # Reduce time window we are searching to the interval in which observations are present (to save time)
    utc_max, utc_min = reduce_time_window(conn=conn, obstory_id=obstory_id, utc_max=utc_max, utc_min=utc_min)

    # Close database handles, so they don't time out during long-running calculations
    db.commit()
    db.close_db()
    db0.commit()
    conn.close()
    db0.close()

    # Run astrometry.net on any observations we find within the requested time window
    successful_fits = analyse_observations(obstory_id=obstory_id, utc_max=utc_max, utc_min=utc_min,
                                           utc_must_stop=utc_must_stop)

    # Report how many fits we achieved
    logging.info("Total of {:d} images successfully fitted.".format(successful_fits))

    return


def reduce_time_window(conn, obstory_id, utc_max, utc_min):
    """
    Reduce the time period we are asked to analyse, to remove any time at the start or end with no observations.
    This is a time-saving measure to avoid making lots of database queries for days with no observations.

    :param conn:
        Database connection object.
    :param obstory_id:
        Observatory publicId.
    :type obstory_id:
        str
    :param utc_max:
        Unix time of the end of the time period (unix time).
    :type utc_max:
        float
    :param utc_min:
        Unix time of the beginning of the time period (unix time).
    :type utc_min:
        float
    :return:
        The new time span we are to analyse [start, end].
    """

    # Search for the earliest observation within the requested time span
    conn.execute("""
SELECT obsTime
FROM archive_observations
WHERE obsTime BETWEEN %s AND %s
    AND observatory=(SELECT uid FROM archive_observatories WHERE publicId=%s)
ORDER BY obsTime ASC LIMIT 1
""", (utc_min, utc_max, obstory_id))
    results = conn.fetchall()

    # If there were no observations, then this was not a sensible query to make
    if len(results) == 0:
        logging.warning("No observations within requested time window.")
        raise IndexError

    # Update the start time of the search window to 1 second before the earliest observation
    utc_min = results[0]['obsTime'] - 1

    # Search for the latest observation within the requested time span
    conn.execute("""
SELECT obsTime
FROM archive_observations
WHERE obsTime BETWEEN %s AND %s
    AND observatory=(SELECT uid FROM archive_observatories WHERE publicId=%s)
ORDER BY obsTime DESC LIMIT 1
""", (utc_min, utc_max, obstory_id))
    results = conn.fetchall()

    # Update the end time of the search window to 1 second after the latest observation
    utc_max = results[0]['obsTime'] + 1

    # Return new time span
    return utc_max, utc_min


def estimate_fit_quality(image_file, item, fit_parameters):
    """
    Estimate the quality of an astrometric fit to an image, by taking an aperture around the brightest stars in
    the image, and measuring the deviation of the centroid of those pixels from the middle.

    :param image_file:
        Filename of the image fitted.
    :type image_file:
        str
    :param item:
        Dictionary describing the image we are to fit (the image's database record).
    :type item:
        dict
    :param fit_parameters:
        Dictionary of astrometric parameters fitted to the image
    :type fit_parameters:
        dict
    :return:
        Numerical metric of the quality of fit
    """

    global hipparcos_catalogue

    # Constants
    margin = 50  # Do not measure stars within this margin of the edges
    max_radius = 0.9  # Do not measure stars outside this number of image-widths of the centre
    max_apertures = 25  # Maximum number of stars to measure
    aperture_radius = 10  # Radius of aperture, pixels
    minimum_bright_pixels = 5  # Need at least this many bright pixels within each aperture

    # Read Hipparcos catalogue of stars brighter than mag 5.5
    if hipparcos_catalogue is None:
        # Read Hipparcos catalogue of stars brighter than mag 5.5
        hipparcos_catalogue = []
        with open("hipparcos_catalogue.json") as f:
            for line in f:
                line = line.strip()
                if len(line) == 0:
                    continue
                id, ra, dec, mag = json.loads(line)
                hipparcos_catalogue.append([int(id), float(ra), float(dec), float(mag)])

    # Open image
    image = Image.open(image_file)
    size_x, size_y = image.size

    # Look up radial distortion model for the lens we are using
    lens_barrel_parameters = item['obstory_status'].get('calibration:lens_barrel_parameters',
                                                        item['lens_props'].barrel_parameters)

    # Identify brightest stars in image
    bright_stars = []
    for hipparcos_id, ra, dec, mag in hipparcos_catalogue:
        fit_ok = True
        # Do gnomonic projection without radial correction first, to discard stars a long way outside FoV
        # Radial distortion polynomials may be badly behaved at extreme radii
        for projection_pass in [0, 1]:
            star_position = gnomonic_project.gnomonic_project(
                ra=ra * deg, dec=dec * deg,
                ra0=fit_parameters['ra'] * hours, dec0=fit_parameters['dec'] * deg,
                size_x=size_x, size_y=size_y,
                scale_x=fit_parameters['scale_x'] * deg, scale_y=fit_parameters['scale_y'] * deg,
                pos_ang=fit_parameters['pa'] * deg,
                barrel_k1=lens_barrel_parameters[2] if projection_pass>0 else 0,
                barrel_k2=lens_barrel_parameters[3] if projection_pass>0 else 0,
                barrel_k3=lens_barrel_parameters[4] if projection_pass>0 else 0
            )

            # Check if star is within field of view
            if (
                    (not np.isfinite(star_position[0])) or
                    star_position[0] < margin or
                    star_position[0] > size_x - margin or
                    star_position[1] < margin or
                    star_position[1] > size_y - margin
            ):
                fit_ok = False

        if not fit_ok:
            continue

        distance_from_centre = hypot(star_position[0] - size_x / 2, star_position[1] - size_y / 2)

        if distance_from_centre > size_x * 0.5 * max_radius:
            continue

        # Star is within field
        bright_stars.append([
            star_position[0],
            star_position[1],
            hipparcos_id
        ])

        # Check if we have enough stars
        if len(bright_stars) >= max_apertures:
            break

    # Loop over apertures
    offset_list = []
    for aperture in bright_stars:
        sum_x = sum_y = bright_pixel_count = 0
        brightness_count = 1e-8
        for x in range(round(aperture[0] - aperture_radius), round(aperture[0] + aperture_radius)):
            for y in range(round(aperture[1] - aperture_radius), round(aperture[1] + aperture_radius)):
                # Check if pixel inside aperture
                radius = hypot(x-aperture[0], y-aperture[1])
                if radius > aperture_radius:
                    continue

                # Fetch pixel brightness
                brightness = image.getpixel((x, y))

                # Update counters
                if brightness > 80 * 256:
                    bright_pixel_count += 1

                brightness_count += brightness
                sum_x += x * brightness
                sum_y += y * brightness

        # Calculate centroid
        centroid_x = sum_x / brightness_count
        centroid_y = sum_y / brightness_count
        offset = hypot(centroid_x - aperture[0], centroid_y - aperture[1])
        # logging.info("HIP{:6d} -- ({:4.0f},{:4.0f}) -- offset {:5.1f} -- bright pixels {:d}".
        #              format(aperture[2], centroid_x, centroid_y, offset, bright_pixel_count))

        # Reject apertures with few bright pixels
        if bright_pixel_count < minimum_bright_pixels:
            continue

        offset_list.append(offset)

    # Deal with cases where no stars found
    offset_count = len(offset_list)
    if offset_count == 0:
        offset_list = [999]

    # Return fit quality metric
    return [np.mean(offset_list), offset_count]


@dask.delayed
def analyse_image(item_index, item, utc_must_stop, batch_size, fraction_x, fraction_y):
    """
    Analyse a single image with astrometry.net, and return the textual output returned by astrometry.net.
    We do this in a dask delayed function call to allow many images to be fitted simultaneously using all
    available CPU cores.

    :param item_index:
        The index of this image in the list <images_for_analysis>
    :type item_index:
        int
    :param item:
        Dictionary describing the image we are to fit (the image's database record).
    :type item:
        dict
    :param utc_must_stop:
        The time by which we must finish work (unix time).
    :type utc_must_stop:
        float
    :param batch_size:
        The number of images we are analysing.
    :type batch_size:
        int
    :param fraction_x:
        The fraction of the width of the image passed to astrometry.net for plate solving.
    :type fraction_x:
        float
    :param fraction_y:
        The fraction of the height of the image passed to astrometry.net for plate solving.
    :type fraction_y:
        float
    :return:
        List of [text output from astrometry.net, log messages, time taken by astrometry.net]
    """
    # Check that we've not run out of time
    if utc_must_stop and (time.time() > utc_must_stop):
        logging.info("We have run out of time! Aborting.")
        return None

    # Report progress
    logging.info("Working on image {:32s} ({:6d}/{:6d})".format(item['repositoryFname'],
                                                                item_index + 1, batch_size))

    # Path the binary barrel-correction tool
    barrel_correct = os.path.join(settings['imageProcessorPath'], "lensCorrect")

    # This is an estimate of the *maximum* angular width we expect images to have.
    # It should be within ~20% of the correct answer!
    estimated_image_scale = item['lens_props'].fov

    # Make a temporary directory to store files in.
    # This is necessary as astrometry.net spams the working directory with lots of temporary junk
    tmp = "/tmp/dcf21_orientationCalc_{}".format(item['repositoryFname'])
    # logging.info("Created temporary directory <{}>".format(tmp))
    os.system("mkdir {}".format(tmp))

    # Find image's full path
    filename = os.path.join(settings['dbFilestore'], item['repositoryFname'])

    # Make sure that image actually exists in the file repository
    if not os.path.exists(filename):
        logging.info("Error: File <{}> is missing!".format(item['repositoryFname']))
        return

    # Look up radial distortion model for the lens we are using
    lens_barrel_parameters = item['obstory_status'].get('calibration:lens_barrel_parameters',
                                                        item['lens_props'].barrel_parameters)
    if isinstance(lens_barrel_parameters, str):
        lens_barrel_parameters = json.loads(lens_barrel_parameters)

    # 1. Copy image into working directory
    # logging.info("Copying file")
    img_name = item['repositoryFname']
    command = "cp {} {}/{}_tmp.png".format(filename, tmp, img_name)
    # logging.info(command)
    os.system(command)

    # 2. Correct the radial distortion present in the image (astrometry.net assumes an ideal lens)
    # logging.info("Lens-correcting image")
    command = """
cd {8} ; \
{0} -i {1}_tmp.png --barrel-k1 {2:.12f} --barrel-k2 {3:.12f} --barrel-k3 {4:.12f} \
               --scale-x {5:.12f} --scale-y {6:.12f} -o {7}_tmp2
""".format(barrel_correct, img_name,
           lens_barrel_parameters[2], lens_barrel_parameters[3], lens_barrel_parameters[4],
           lens_barrel_parameters[0], lens_barrel_parameters[1],
           img_name, tmp)
    # logging.info(command)
    os.system(command)

    # 3. Pass only central portion of image to astrometry.net.
    #  It's not very reliable with wide-field images unless the radial distortion is very well corrected.
    # logging.info("Extracting central portion of image")
    d = image_dimensions("{}/{}_tmp2.png".format(tmp, img_name))
    command = """
cd {6} ; \
rm -f {5}_tmp3.png ; \
convert {0}_tmp2.png -colorspace sRGB -define png:format=png24 -crop {1:d}x{2:d}+{3:d}+{4:d} +repage {5}_tmp3.png
""".format(img_name,
           int(fraction_x * d[0]), int(fraction_y * d[1]),
           int((1 - fraction_x) * d[0] / 2), int((1 - fraction_y) * d[1] / 2),
           img_name,
           tmp)
    # logging.info(command)
    os.system(command)

    # How long should we allow astrometry.net to run for?
    timeout = "120s"

    # Run astrometry.net. Insert --no-plots on the command line to speed things up.
    # logging.info("Running astrometry.net")
    astrometry_start_time = time.time()
    astrometry_output = os.path.join(tmp, "txt")
    estimated_width = 2 * math.atan(math.tan(estimated_image_scale / 2 * deg) * fraction_x) * rad
    command = """
cd {5} ; \
timeout {0} solve-field --no-plots --crpix-center --scale-low {1:.1f} \
    --scale-high {2:.1f} --overwrite {3}_tmp3.png > {4} 2> /dev/null \
""".format(timeout,
           estimated_width * 0.8,
           estimated_width * 1.2,
           img_name,
           astrometry_output,
           tmp)
    # logging.info(command)
    os.system(command)

    # Report how long astrometry.net took
    astrometry_time_taken = time.time() - astrometry_start_time
    log_msg = "Astrometry.net took {:.0f} sec. ".format(astrometry_time_taken)

    # Parse the output from astrometry.net
    assert os.path.exists(astrometry_output), "Path <{}> doesn't exist".format(astrometry_output)
    fit_text = open(astrometry_output).read()
    # logging.info(fit_text)

    # Clean up
    os.system("rm -Rf {}".format(tmp))

    # Return output from astrometry.net
    return fit_text, log_msg, astrometry_time_taken


def extract_astrometry_output(db0, conn, db, item, fit_text_item, obstory_info, fraction_x, fraction_y):
    """
    Process the textual output from astrometry.net, and extract from the text the calculated sky position of the
    image.

    :param db0:
        Database connection.
    :param conn:
        Database connection object.
    :param db:
        Database interface handle.
    :type db:
        obsarchive_db.ObservationDatabase
    :param item:
        Dictionary describing the image we are to fit (the image's database record).
    :param fit_text_item:
        List of [text output from astrometry.net, log messages, time taken by astrometry.net]
    :param obstory_info:
        Dictionary of metadata about the observatory which made this observation.
    :type obstory_info:
        dict
    :param fraction_x:
        The fraction of the width of the image passed to astrometry.net for plate solving.
    :type fraction_x:
        float
    :param fraction_y:
        The fraction of the height of the image passed to astrometry.net for plate solving.
    :type fraction_y:
        float
    :return:
        Number of images for which successful orientations were determined (0 or 1)
    """

    # If astrometry.net didn't produce any text (perhaps we ran out of time and never ran it), we cannot proceed
    if fit_text_item is None:
        return 0

    # Unpack output from <analyse_image>
    fit_text, log_msg, astrometry_time_taken = fit_text_item

    # Fetch source Id for data generated by this python script (used to record data provenance in the database)
    source_id = connect_db.fetch_source_id(c=conn, source_info=("astrometry.net", "astrometry.net", "astrometry.net"))
    db0.commit()

    # Update observation database record to report that astrometry.net was run
    timestamp = time.time()
    conn.execute("""
UPDATE archive_observations
SET astrometryProcessed=%s, astrometryProcessingTime=%s, astrometrySource=%s,
    fieldWidth=NULL, fieldHeight=NULL, positionAngle=NULL, centralConstellation=NULL,
    skyArea=ST_GEOMFROMTEXT(%s), position=POINT(-999,-999),
    altAz=POINT(-999,-999), altAzPositionAngle=NULL
WHERE publicId=%s;
                     """, (timestamp, astrometry_time_taken, source_id,
                           obsarchive_sky_area.null_polygon,
                           item['observationId']))
    db0.commit()

    # Extract celestial coordinates of the centre of the frame from astrometry.net output
    test = re.search(r"\(RA H:M:S, Dec D:M:S\) = \(([\d-]*):(\d\d):([\d.]*), [+]?([\d-]*):(\d\d):([\d\.]*)\)",
                     fit_text)
    if not test:
        logging.info("FAIL(POS): {}".format(log_msg))
        return 0

    # Extract RA of centre of the image, in hours, J2000
    ra_sign = sgn(float(test.group(1)))
    ra = abs(float(test.group(1))) + float(test.group(2)) / 60 + float(test.group(3)) / 3600
    if ra_sign < 0:
        ra *= -1

    # Extract declination of centre of the image, in degrees, J2000
    dec_sign = sgn(float(test.group(4)))
    dec = abs(float(test.group(4))) + float(test.group(5)) / 60 + float(test.group(6)) / 3600
    if dec_sign < 0:
        dec *= -1
    test = re.search(r"up is [+]?([-\d\.]*) degrees (.) of N", fit_text)
    if not test:
        logging.info("FAIL(PA ): {}".format(log_msg))
        return 0

    # celestial_pa_j2000 is the position angle of the upward vector in the centre of the image, counterclockwise
    #  from celestial north (J2000).
    # * It is zero if the pole star is vertical above the centre of the image.
    # * If the pole star is in the top-right of an image, expect it to be around -45 degrees.
    celestial_pa_j2000 = float(test.group(1))
    # * This 180 degree rotation appears because when astrometry.net says "up" it means the bottom of the image!
    celestial_pa_j2000 += 180
    if test.group(2) == "W":
        celestial_pa_j2000 *= -1
    while celestial_pa_j2000 > 180:
        celestial_pa_j2000 -= 360
    while celestial_pa_j2000 < -180:
        celestial_pa_j2000 += 360
    test = re.search(r"Field size: ([\d\.]*) x ([\d\.]*) deg", fit_text)
    if not test:
        logging.info("FAIL(SIZ): {}".format(log_msg))
        return 0

    # Expand reported angular size of image to whole image, not just the central tile we sent to astrometry.net
    scale_x = 2 * math.atan(math.tan(float(test.group(1)) / 2 * deg) / fraction_x) * rad
    scale_y = 2 * math.atan(math.tan(float(test.group(2)) / 2 * deg) / fraction_y) * rad

    # Convert coordinates of the centre of the frame from J2000 (as output from astrometry.net) to epoch
    # hours / degrees at epoch
    ra_at_epoch, dec_at_epoch = ra_dec_from_j2000(ra0=ra, dec0=dec, utc_new=item['utc'])

    # Work out alt-az of reported (RA,Dec) using known location of camera. Fits returned in degrees.
    alt_az_pos = alt_az(ra=ra_at_epoch, dec=dec_at_epoch, utc=item['utc'],
                        latitude=obstory_info['latitude'], longitude=obstory_info['longitude'])

    # Get celestial coordinates of the local zenith
    ra_dec_zenith_at_epoch = get_zenith_position(latitude=obstory_info['latitude'],
                                                 longitude=obstory_info['longitude'],
                                                 utc=item['utc'])
    ra_zenith_at_epoch = ra_dec_zenith_at_epoch['ra']  # hours, epoch of observation
    dec_zenith_at_epoch = ra_dec_zenith_at_epoch['dec']  # degrees, epoch of observation

    ra_zenith_j2000, dec_zenith_j2000 = ra_dec_to_j2000(ra1=ra_zenith_at_epoch,
                                                        dec1=dec_zenith_at_epoch,
                                                        utc_old=item['utc'])

    # Work out the position angle of the zenith, counterclockwise from north, as measured at centre of frame
    # degrees, for J2000 north pole
    zenith_pa_j2000 = gnomonic_project.position_angle(ra1=ra, dec1=dec,
                                                      ra2=ra_zenith_j2000, dec2=dec_zenith_j2000)

    # Calculate the position angle of the zenith, clockwise from vertical, at the centre of the frame
    # If the camera is roughly upright, this ought to be close to zero!
    camera_tilt = zenith_pa_j2000 - celestial_pa_j2000
    while camera_tilt < -180:
        camera_tilt += 360
    while camera_tilt > 180:
        camera_tilt -= 360

    # Report whether we got a successful orientation determination
    logging.info("PASS     : {}".format(log_msg))
    logging.info("FIT      : RA: {:7.2f}h. Dec {:7.2f} deg. PA {:6.1f} deg. ScaleX {:6.1f}. ScaleY {:6.1f}. "
                 "Zenith at ({:.2f} h,{:.2f} deg). PA Zenith {:.2f} deg. "
                 "Alt: {:7.2f} deg. Az: {:7.2f} deg. Tilt: {:7.2f} deg.".format
                 (ra, dec, celestial_pa_j2000,
                  scale_x, scale_y,
                  ra_zenith_j2000, dec_zenith_j2000, zenith_pa_j2000,
                  alt_az_pos[0], alt_az_pos[1],
                  camera_tilt))

    # Find image's full path
    filename = os.path.join(settings['dbFilestore'], item['repositoryFname'])

    # Estimate quality of fit
    fit_quality = estimate_fit_quality(
        image_file=filename,
        item=item,
        fit_parameters={
            'ra': ra, 'dec': dec, 'pa': celestial_pa_j2000, 'scale_x': scale_x, 'scale_y': scale_y
        }
    )
    logging.info("QUALITY  : {}".format(fit_quality))

    # Get a polygon representing the sky area of this image
    sky_area = get_sky_area(ra=ra, dec=dec, pa=celestial_pa_j2000, scale_x=scale_x, scale_y=scale_y)

    # Update observation database record to reflect the orientation returned by astrometry.net
    timestamp = time.time()
    conn.execute("""
UPDATE archive_observations SET position=POINT(%s,%s), positionAngle=%s,
                                altAz=POINT(%s,%s), altAzPositionAngle=%s,
                                fieldWidth=%s, fieldHeight=%s,
                                astrometryProcessed=%s, astrometryProcessingTime=%s,
                                skyArea=ST_GEOMFROMTEXT(%s)
WHERE publicId=%s;
                     """, (ra, dec, celestial_pa_j2000,
                           alt_az_pos[1], alt_az_pos[0], camera_tilt,
                           scale_x, scale_y,
                           timestamp, astrometry_time_taken,
                           sky_area,
                           item['observationId']))
    db0.commit()

    # Update metadata accompanying this image to reflect the orientation determination
    user = settings['pigazingUser']
    db.set_observation_metadata(user_id=user, observation_id=item['observationId'], utc=timestamp,
                                meta=mp.Meta(key="orientation:ra", value=ra))
    db.set_observation_metadata(user_id=user, observation_id=item['observationId'], utc=timestamp,
                                meta=mp.Meta(key="orientation:dec", value=dec))
    db.set_observation_metadata(user_id=user, observation_id=item['observationId'], utc=timestamp,
                                meta=mp.Meta(key="orientation:pa", value=celestial_pa_j2000))
    db.set_observation_metadata(user_id=user, observation_id=item['observationId'], utc=timestamp,
                                meta=mp.Meta(key="orientation:altitude", value=alt_az_pos[0]))
    db.set_observation_metadata(user_id=user, observation_id=item['observationId'], utc=timestamp,
                                meta=mp.Meta(key="orientation:azimuth", value=alt_az_pos[1]))
    db.set_observation_metadata(user_id=user, observation_id=item['observationId'], utc=timestamp,
                                meta=mp.Meta(key="orientation:tilt", value=camera_tilt))
    db.set_observation_metadata(user_id=user, observation_id=item['observationId'], utc=timestamp,
                                meta=mp.Meta(key="orientation:width_x_field", value=scale_x))
    db.set_observation_metadata(user_id=user, observation_id=item['observationId'], utc=timestamp,
                                meta=mp.Meta(key="orientation:width_y_field", value=scale_y))
    db.set_observation_metadata(user_id=user, observation_id=item['observationId'], utc=timestamp,
                                meta=mp.Meta(key="orientation:fit_quality", value=json.dumps(fit_quality)))
    db.commit()

    # Return number of successful fits
    return 1


def analyse_observations(obstory_id, utc_max, utc_min, utc_must_stop):
    """
    Analyse still images recorded by the camera with publicId <obstoryId> within the specified time period, to
    determine the orientation of the camera on the sky. Where we manage to successfully determine the orientation
    of an image, this metadata is added to the image's database record.

    :param obstory_id:
        Observatory publicId.
    :type obstory_id:
        str
    :param utc_max:
        Unix time of the end of the time period (unix time).
    :type utc_max:
        float
    :param utc_min:
        Unix time of the beginning of the time period (unix time).
    :type utc_min:
        float
    :param utc_must_stop:
        The time by which we must finish work (unix time).
    :type utc_must_stop:
        float
    :return:
        The number of images successfully fitted.
    """

    # Open connection to database
    [db0, conn] = connect_db.connect_db()

    # Open connection to image archive
    db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                           db_host=installation_info['mysqlHost'],
                                           db_user=installation_info['mysqlUser'],
                                           db_password=installation_info['mysqlPassword'],
                                           db_name=installation_info['mysqlDatabase'],
                                           obstory_id=installation_info['observatoryId'])

    # When passing images to astrometry.net, only work on the central portion, as corners may be distorted
    # (this is a problem if radial distortion is not fixed, but can use whole image if distortion is well modelled)
    fraction_x = 0.9
    fraction_y = 0.9

    # Count how many images we manage to successfully fit
    successful_fits = 0

    # Read properties of known lenses, which give us the default radial distortion models to assume for them
    hw = hardware_properties.HardwareProps(
        path=os.path.join(settings['pythonPath'], "..", "configuration_global", "camera_properties")
    )

    logging.info("Searching for images within period {} to {}".format(date_string(utc_min), date_string(utc_max)))

    # Create a list of all of the two-minute time intervals in which we are to analyse the best image
    time_blocks = list(np.arange(start=utc_min, stop=utc_max, step=block_size))

    # Fetch observatory's database record
    obstory_info = db.get_obstory_from_id(obstory_id)

    # Build list of images we are to analyse
    images_for_analysis = []

    # Loop over all the two-minute intervals in which we are to fit the best image
    for block_index, utc_block_min in enumerate(time_blocks[:-1]):
        # End time for this time block
        utc_block_max = time_blocks[block_index + 1]

        # Search for background-subtracted time lapse image with best sky clarity, and no existing orientation fit,
        # within this time period
        conn.execute("""
SELECT ao.obsTime, ao.publicId AS observationId, f.repositoryFname, am.floatValue AS skyClarity
FROM archive_files f
INNER JOIN archive_observations ao on f.observationId = ao.uid
INNER JOIN archive_metadata am ON f.uid = am.fileId AND
    am.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="pigazing:skyClarity")
WHERE ao.obsTime BETWEEN %s AND %s
    AND ao.observatory=(SELECT uid FROM archive_observatories WHERE publicId=%s)
    AND f.semanticType=(SELECT uid FROM archive_semanticTypes WHERE name="pigazing:timelapse/backgroundSubtracted")
    AND am.floatValue > %s
    AND ao.astrometryProcessed IS NULL
ORDER BY am.floatValue DESC LIMIT 1
""", (utc_block_min, utc_block_max, obstory_id, minimum_sky_clarity))
        results = conn.fetchall()

        # If we found an image, add it to the list of images we are to process
        if len(results) > 0:

            # Fetch observatory status at time of observation
            obstory_status = None
            if obstory_info and ('name' in obstory_info):
                obstory_status = db.get_obstory_status(obstory_id=obstory_id, time=results[0]['obsTime'])
            if not obstory_status:
                logging.info("Aborting -- no observatory status available.")
                continue

            # Fetch properties of the lens being used at the time of the observation
            lens_name = obstory_status['lens']
            lens_props = hw.lens_data[lens_name]

            # Add image to the list of images we are to process
            images_for_analysis.append({
                'utc': results[0]['obsTime'],
                'skyClarity': results[0]['skyClarity'],
                'repositoryFname': results[0]['repositoryFname'],
                'observationId': results[0]['observationId'],
                'obstory_info': obstory_info,
                'obstory_status': obstory_status,
                'lens_props': lens_props
            })

    # Sort the images we are to process into order of descending sky clarity (best image first)
    images_for_analysis.sort(key=itemgetter("skyClarity"))
    images_for_analysis.reverse()

    # Display logging list of the images we are going to work on
    logging.info("Estimating the orientation of {:d} images:".format(len(images_for_analysis)))
    # for item in images_for_analysis:
    #     logging.info("{:17s} {:04.0f} {:32s}".format(date_string(item['utc']),
    #                                                  item['skyClarity'],
    #                                                  item['repositoryFname']))

    # Analyse each image in turn
    dask_tasks = []
    dask_group_items = []
    for item_index, item in enumerate(images_for_analysis):

        # Queue up the astrometry.net runs we are going to do, and run them in parallel with dask
        dask_group_items.append(item)
        dask_tasks.append(analyse_image(item_index=item_index, item=item,
                                        utc_must_stop=utc_must_stop, batch_size=len(images_for_analysis),
                                        fraction_x=fraction_x, fraction_y=fraction_y))

        # Run dask tasks in small groups (if groups are too big, we run out of space in /tmp due to imperfect clean-up)
        dask_group_size = 200
        if len(dask_tasks) >= dask_group_size:
            # Run tasks
            dask_group_output = dask.compute(*dask_tasks)

            # Extract results from astrometry.net
            for item, fit_text_item in zip(dask_group_items, dask_group_output):
                successful_fits += extract_astrometry_output(
                    db0=db0, conn=conn, db=db,
                    item=item, fit_text_item=fit_text_item,
                    obstory_info=obstory_info,
                    fraction_x=fraction_x, fraction_y=fraction_y
                )
            dask_tasks = []
            dask_group_items = []

            # Clean up spurious files which astrometry.net leaves in /tmp
            os.system("rm -Rf /tmp/tmp.*")

    # Run final group of tasks
    dask_group_output = dask.compute(*dask_tasks)

    # Extract results from astrometry.net
    for item, fit_text_item in zip(dask_group_items, dask_group_output):
        successful_fits += extract_astrometry_output(
            db0=db0, conn=conn, db=db,
            item=item, fit_text_item=fit_text_item,
            obstory_info=obstory_info,
            fraction_x=fraction_x, fraction_y=fraction_y
        )

    # Clean up spurious files which astrometry.net leaves in /tmp
    os.system("rm -Rf /tmp/tmp.*")

    # Close database handles
    db.commit()
    db.close_db()
    db0.commit()
    conn.close()
    db0.close()
    return successful_fits


def flush_orientation(obstory_id, utc_min, utc_max):
    """
    Remove all orientation data for a particular observatory within a specified time period.

    :param obstory_id:
        The publicId of the observatory we are to flush.
    :param utc_min:
        The earliest time for which we are to flush orientation data.
    :param utc_max:
        The latest time for which we are to flush orientation data.
    :return:
        None
    """
    # Open connection to database
    [db0, conn] = connect_db.connect_db()

    # Delete observatory metadata fields that start 'orientation:*'
    conn.execute("""
DELETE m
FROM archive_metadata m
WHERE
    fieldId IN (SELECT uid FROM archive_metadataFields WHERE metaKey LIKE 'orientation:%%') AND
    m.observatory = (SELECT uid FROM archive_observatories WHERE publicId=%s) AND
    m.time BETWEEN %s AND %s;
""", (obstory_id, utc_min, utc_max))

    # Delete observation metadata fields that start 'orientation:*'
    conn.execute("""
DELETE m
FROM archive_metadata m
INNER JOIN archive_observations o ON m.observationId = o.uid
WHERE
    fieldId IN (SELECT uid FROM archive_metadataFields WHERE metaKey LIKE 'orientation:%%') AND
    o.observatory = (SELECT uid FROM archive_observatories WHERE publicId=%s) AND
    o.obsTime BETWEEN %s AND %s;
""", (obstory_id, utc_min, utc_max))

    # Clear astrometryProcessed fields
    conn.execute("""
UPDATE archive_observations
SET astrometryProcessed=NULL, astrometryProcessingTime=NULL, astrometrySource=NULL,
    fieldWidth=NULL, fieldHeight=NULL, positionAngle=NULL, centralConstellation=NULL,
    skyArea=ST_GEOMFROMTEXT(%s), position=POINT(-999,-999),
    altAz=POINT(-999,-999), altAzPositionAngle=NULL
WHERE observatory = (SELECT x.uid FROM archive_observatories x WHERE x.publicId=%s) AND
      obsTime BETWEEN %s AND %s;
""", (obsarchive_sky_area.null_polygon, obstory_id, utc_min, utc_max))

    # Commit changes to database
    db0.commit()
    conn.close()
    db0.close()


# If we're called as a script, run the function orientation_calc()
if __name__ == "__main__":
    # Read command-line arguments
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stop-by', default=None, type=float,
                        dest='stop_by', help='The unix time when we need to exit, even if jobs are unfinished')

    # By default, study images taken over past 24 hours
    parser.add_argument('--utc-min', dest='utc_min', default=time.time() - 3600 * 24,
                        type=float,
                        help="Only use images recorded after the specified unix time")
    parser.add_argument('--utc-max', dest='utc_max', default=time.time(),
                        type=float,
                        help="Only use images recorded before the specified unix time")

    parser.add_argument('--observatory', dest='obstory_id', default=installation_info['observatoryId'],
                        help="ID of the observatory we are to calibrate")
    parser.add_argument('--flush', dest='flush', action='store_true')
    parser.add_argument('--no-flush', dest='flush', action='store_false')
    parser.set_defaults(flush=False)
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

    # If flush option was specified, then delete all existing alignment information
    if args.flush:
        flush_orientation(obstory_id=args.obstory_id,
                          utc_min=args.utc_min,
                          utc_max=args.utc_max)

    # Calculate the orientation of images
    orientation_calc(obstory_id=args.obstory_id,
                     utc_min=args.utc_min,
                     utc_max=args.utc_max,
                     utc_must_stop=args.stop_by)
