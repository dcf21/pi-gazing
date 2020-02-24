#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# calibrate_lens.py
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
This script is used to estimate the degree of lens distortion present in an image.

The best-fit parameter values are returned to the user. If they are believed to be good, you should set a status
update on the observatory setting barrel_a, barrel_b and barrel_c. Then future observations will correct for this
lens distortion.

You may also changed the values for your lens in the XML file <src/configuration_global/camera_properties> which means
that future observatories set up with your model of lens will use your barrel correction coefficients.
"""

import argparse
import logging
import math
import os
import re
import subprocess
import time
from math import pi, floor, hypot, isfinite
from operator import itemgetter

import numpy as np
import scipy.optimize
from pigazing_helpers import connect_db, hardware_properties
from pigazing_helpers.dcf_ast import date_string
from pigazing_helpers.gnomonic_project import gnomonic_project
from pigazing_helpers.obsarchive import obsarchive_db
from pigazing_helpers.settings_read import settings, installation_info

degrees = pi / 180


# Return the dimensions of an image
def image_dimensions(in_file):
    d = subprocess.check_output(["identify", "-quiet", in_file]).decode('utf-8').split()[2].split("x")
    d = [int(i) for i in d]
    return d


# Return the sign of a number
def sgn(x):
    if x < 0:
        return -1
    if x > 0:
        return 1
    return 0


fit_list = None
param_scales = None


def mismatch(params):
    global params_scales, fit_list
    ra0 = params[0] * params_scales[0]
    dec0 = params[1] * params_scales[1]
    scale_x = params[2] * params_scales[2]
    scale_y = params[3] * params_scales[3]
    pos_ang = params[4] * params_scales[4]
    bca = params[5] * params_scales[5]
    bcb = params[6] * params_scales[6]
    bcc = params[7] * params_scales[7]

    accumulator = 0
    for star in fit_list:
        pos = gnomonic_project(ra=star['ra'], dec=star['dec'], ra0=ra0, dec0=dec0,
                               size_x=1, size_y=1, scale_x=scale_x, scale_y=scale_y, pos_ang=pos_ang,
                               bca=bca, bcb=bcb, bcc=bcc)
        if not isfinite(pos[0]):
            pos[0] = -999
        if not isfinite(pos[1]):
            pos[1] = -999
        offset = pow(hypot(star['x'] - pos[0], star['y'] - pos[1]), 2)
        accumulator += offset
    # print "%10e -- %s" % (accumulator, list(params))
    return accumulator


def calibrate_lens(obstory_id, utc_min, utc_max, utc_must_stop=None):
    """
    Use astrometry.net to determine the orientation of a particular observatory.

    :param obstory_id:
        The ID of the observatory we want to determine the orientation for.
    :param utc_min:
        The start of the time period in which we should determine the observatory's orientation.
    :param utc_max:
        The end of the time period in which we should determine the observatory's orientation.
    :param utc_must_stop:
        The time by which we must finish work
    :return:
        None
    """
    global params_scales, fit_list

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

    # Mathematical constants
    deg = pi / 180
    rad = 180 / pi

    # Read properties of known lenses
    hw = hardware_properties.HardwareProps(
        path=os.path.join(settings['pythonPath'], "..", "configuration_global", "camera_properties")
    )

    # Reduce time window to where observations are present
    conn.execute("""
SELECT obsTime
FROM archive_observations
WHERE obsTime BETWEEN %s AND %s
    AND observatory=(SELECT uid FROM archive_observatories WHERE publicId=%s)
ORDER BY obsTime ASC LIMIT 1
""", (utc_min, utc_max, obstory_id))
    results = conn.fetchall()

    if len(results) == 0:
        logging.warning("No observations within requested time window.")
        return
    utc_min = results[0]['obsTime'] - 1

    conn.execute("""
SELECT obsTime
FROM archive_observations
WHERE obsTime BETWEEN %s AND %s
    AND observatory=(SELECT uid FROM archive_observatories WHERE publicId=%s)
ORDER BY obsTime DESC LIMIT 1
""", (utc_min, utc_max, obstory_id))
    results = conn.fetchall()
    utc_max = results[0]['obsTime'] + 1

    # Divide up time interval into day-long blocks
    logging.info("Searching for images within period {} to {}".format(date_string(utc_min), date_string(utc_max)))
    block_size = 86400
    minimum_sky_clarity = 500
    utc_min = (floor(utc_min / block_size + 0.5) - 0.5) * block_size  # Make sure that blocks start at noon
    time_blocks = list(np.arange(start=utc_min, stop=utc_max + block_size, step=block_size))

    # Start new block whenever we have a hardware refresh
    conn.execute("""
SELECT time FROM archive_metadata
WHERE observatory=(SELECT uid FROM archive_observatories WHERE publicId=%s)
      AND fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey='refresh')
      AND time BETWEEN %s AND %s
""", (obstory_id, utc_min, utc_max))
    results = conn.fetchall()
    for item in results:
        time_blocks.append(item['time'])

    # Make sure that start points for time blocks are in order
    time_blocks.sort()

    # Build list of images we are to analyse
    images_for_analysis = []

    for block_index, utc_block_min in enumerate(time_blocks[:-1]):
        utc_block_max = time_blocks[block_index + 1]
        logging.info("Calibrating lens within period {} to {}".format(date_string(utc_block_min),
                                                                      date_string(utc_block_max)))

        # Search for background-subtracted time lapse image with best sky clarity within this time period
        conn.execute("""
SELECT ao.obsTime, ao.publicId AS observationId, f.repositoryFname, am.floatValue AS skyClarity
FROM archive_files f
INNER JOIN archive_observations ao on f.observationId = ao.uid
INNER JOIN archive_metadata am ON f.uid = am.fileId AND
    am.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="pigazing:skyClarity")
LEFT OUTER JOIN archive_metadata am2 ON f.uid = am2.fileId AND
    am2.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="orientation:altitude")
WHERE ao.obsTime BETWEEN %s AND %s
    AND ao.observatory=(SELECT uid FROM archive_observatories WHERE publicId=%s)
    AND f.semanticType=(SELECT uid FROM archive_semanticTypes WHERE name="pigazing:timelapse/backgroundSubtracted")
    AND am.floatValue > %s
    AND am2.uid IS NULL
ORDER BY am.floatValue DESC LIMIT 1
""", (utc_block_min, utc_block_max, obstory_id, minimum_sky_clarity))
        results = conn.fetchall()

        if len(results) > 0:
            images_for_analysis.append({
                'utc': results[0]['obsTime'],
                'skyClarity': results[0]['skyClarity'],
                'repositoryFname': results[0]['repositoryFname'],
                'observationId': results[0]['observationId']
            })

    # Sort images into order of sky clarity
    images_for_analysis.sort(key=itemgetter("skyClarity"))
    images_for_analysis.reverse()

    # Display logging list of the images we are going to work on
    logging.info("Estimating the calibration of {:d} images:".format(len(images_for_analysis)))
    for item in images_for_analysis:
        logging.info("{:17s} {:04.0f} {:32s}".format(date_string(item['utc']),
                                                     item['skyClarity'],
                                                     item['repositoryFname']))

    # Analyse each image in turn
    for item_index, item in enumerate(images_for_analysis):
        logging.info("Working on image {:32s} ({:4d}/{:4d})".format(item['repositoryFname'],
                                                                    item_index + 1, len(images_for_analysis)))

        # Fetch observatory status
        obstory_info = db.get_obstory_from_id(obstory_id)
        obstory_status = None
        if obstory_info and ('name' in obstory_info):
            obstory_status = db.get_obstory_status(obstory_id=obstory_id, time=item['utc'])
        if not obstory_status:
            logging.info("Aborting -- no observatory status available.")
            continue

        # Fetch observatory status
        lens_name = obstory_status['lens']
        lens_props = hw.lens_data[lens_name]

        # This is an estimate of the *maximum* angular width we expect images to have.
        # It should be within a factor of two of correct!
        estimated_image_scale = lens_props.fov

        # Make a temporary directory to store files in.
        # This is necessary as astrometry.net spams the cwd with lots of temporary junk
        cwd = os.getcwd()
        tmp = "/tmp/dcf21_orientationCalc_{}".format(item['repositoryFname'])
        # logging.info("Created temporary directory <{}>".format(tmp))
        os.system("mkdir %s" % tmp)
        os.chdir(tmp)

        # Find image orientation orientation
        filename = os.path.join(settings['dbFilestore'], item['repositoryFname'])

        if not os.path.exists(filename):
            logging.info("Error: File <{}> is missing!".format(item['repositoryFname']))
            continue

        # 1. Copy image into working directory
        # logging.info("Copying file")
        img_name = item['repositoryFname']
        command = "cp {} {}_tmp.png".format(filename, img_name)
        # logging.info(command)
        os.system(command)

        # 2. Pass a series of small portions of image to astrometry.net.
        fraction_x = 0.15
        fraction_y = 0.15

        fit_list = []
        portion_centres = []
        portion_centres.extend([[z, z] for z in np.arange(0.1, 0.9, 0.1)])
        portion_centres.extend([[0.5, z] for z in np.arange(0.15, 0.85, 0.1)])
        portion_centres.extend([[z, 0.5] for z in np.arange(0.15, 0.85, 0.1)])
        portion_centres.extend([[z, 1 - z] for z in np.arange(0.1, 0.9, 0.1)])

        d = image_dimensions("{}_tmp.png".format(img_name))

        for image_portion in portion_centres:
            command = """
rm -f {0}_tmp3.png ; \
convert {0}_tmp.png -colorspace sRGB -define png:format=png24 -crop {1:d}x{2:d}+{3:d}+{4:d} +repage {0}_tmp3.png
""".format(img_name,
           int(fraction_x * d[0]), int(fraction_y * d[1]),
           int((image_portion[0] - fraction_x / 2) * d[0]), int((image_portion[1] - fraction_y / 2) * d[1]),
           )
            # logging.info(command)
            os.system(command)

            # Check that we've not run out of time
            if utc_must_stop and (time.time() > utc_must_stop):
                logging.info("We have run out of time! Aborting.")
                continue

            # How long should we allow astrometry.net to run for?
            timeout = "2m" if settings['i_am_a_rpi'] else "30s"

            # Run astrometry.net. Insert --no-plots on the command line to speed things up.
            # logging.info("Running astrometry.net")
            estimated_width = 2 * math.atan(math.tan(estimated_image_scale / 2 * deg) * fraction_x) * rad
            astrometry_start_time = time.time()
            command = """
timeout {0} solve-field --no-plots --crpix-center --scale-low {1:.1f} \
        --scale-high {2:.1f} --overwrite {3}_tmp3.png > txt 2> /dev/null \
""".format(timeout,
           estimated_width * 0.6,
           estimated_width * 1.2,
           img_name)
            # logging.info(command)
            os.system(command)

            # Report how long astrometry.net took
            astrometry_time_taken = time.time() - astrometry_start_time
            # log_msg = "Astrometry.net took {:.0f} sec. ".format(astrometry_time_taken)

            # Parse the output from astrometry.net
            fit_text = open("txt").read()
            # logging.info(fit_text)
            test = re.search(r"\(RA H:M:S, Dec D:M:S\) = \(([\d-]*):(\d\d):([\d.]*), [+]?([\d-]*):(\d\d):([\d\.]*)\)",
                             fit_text)
            if not test:
                logging.info("FAIL(POS): Point ({:.2f},{:.2f}).".format(image_portion[0], image_portion[1]))
                continue

            ra_sign = sgn(float(test.group(1)))
            ra = abs(float(test.group(1))) + float(test.group(2)) / 60 + float(test.group(3)) / 3600
            if ra_sign < 0:
                ra *= -1
            dec_sign = sgn(float(test.group(4)))
            dec = abs(float(test.group(4))) + float(test.group(5)) / 60 + float(test.group(6)) / 3600
            if dec_sign < 0:
                dec *= -1

            logging.info("FIT: RA: {:7.2f}h. Dec {:7.2f} deg. Point ({:.2f},{:.2f}).".format(ra, dec, image_portion[0],
                                                                                             image_portion[1]))
            fit_list.append({
                'ra': ra * pi / 12,
                'dec': dec * pi / 180,
                'x': image_portion[0],
                'y': image_portion[1]
            })

        # Clean up
        os.chdir(cwd)
        os.system("rm -Rf {}".format(tmp))

        # Solve system of equations to give best fit barrel correction
        # See <http://www.scipy-lectures.org/advanced/mathematical_optimization/> for more information about how this works
        ra0 = fit_list[0]['ra']
        dec0 = fit_list[0]['dec']
        params_scales = [pi / 4, pi / 4, pi / 4, pi / 4, pi / 4, pi / 4, 0.005, 0.005, 0.005]
        params_defaults = [ra0, dec0, pi / 4, pi / 4, 0, 0, 0, 0]
        params_initial = [params_defaults[i] / params_scales[i] for i in range(len(params_defaults))]
        params_optimised = scipy.optimize.minimize(mismatch, params_initial, method='nelder-mead',
                                                   options={'xtol': 1e-8, 'disp': True, 'maxiter': 1e8, 'maxfev': 1e8}
                                                   ).x
        params_final = [params_optimised[i] * params_scales[i] for i in range(len(params_defaults))]

        # Display best fit numbers
        headings = [["Central RA / hr", 12 / pi], ["Central Decl / deg", 180 / pi],
                    ["Image width / deg", 180 / pi], ["Image height / deg", 180 / pi],
                    ["Position angle / deg", 180 / pi],
                    ["barrel_a", 1], ["barrel_b", 1], ["barrel_c", 1]
                    ]

        print("\n\nBest fit parameters were:")
        for i in range(len(params_defaults)):
            print("{0:30s} : {1}".format(headings[i][0], params_final[i] * headings[i][1]))


def flush_calibration(obstory_id, utc_min, utc_max):
    # Open connection to database
    [db0, conn] = connect_db.connect_db()

    # Delete observatory metadata fields that start 'calibration:*'
    conn.execute("""
DELETE m
FROM archive_metadata m
WHERE
    fieldId IN (SELECT uid FROM archive_metadataFields WHERE metaKey LIKE 'calibration:%%') AND
    m.observatory = (SELECT uid FROM archive_observatories WHERE publicId=%s) AND
    m.time BETWEEN %s AND %s;
""", (obstory_id, utc_min, utc_max))

    # Delete observation metadata fields that start 'calibration:*'
    conn.execute("""
DELETE m
FROM archive_metadata m
INNER JOIN archive_observations o ON m.observationId = o.uid
WHERE
    fieldId IN (SELECT uid FROM archive_metadataFields WHERE metaKey LIKE 'calibration:%%') AND
    o.observatory = (SELECT uid FROM archive_observatories WHERE publicId=%s) AND
    o.obsTime BETWEEN %s AND %s;
""", (obstory_id, utc_min, utc_max))

    # Commit changes to database
    db0.commit()
    conn.close()
    db0.close()


# If we're called as a script, run the method orientationCalc()
if __name__ == "__main__":
    # Read commandline arguments
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
    logger.info(__doc__.strip())

    # If flush option was specified, then delete all existing alignment information
    if args.flush:
        flush_calibration(obstory_id=args.obstory_id,
                          utc_min=args.utc_min,
                          utc_max=args.utc_max)

    # Calculate the orientation of images
    calibrate_lens(obstory_id=args.obstory_id,
                   utc_min=args.utc_min,
                   utc_max=args.utc_max,
                   utc_must_stop=args.stop_by)
