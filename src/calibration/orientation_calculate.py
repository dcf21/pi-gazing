#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# orientation_calculate.py
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
Use astrometry.net to calculate the orientation of the camera based on recent images
"""

import argparse
import logging
import math
import os
import re
import subprocess
import time
from math import pi, floor
from operator import itemgetter

import numpy as np
from pigazing_helpers import connect_db, gnomonic_project, hardware_properties
from pigazing_helpers.dcf_ast import date_string
from pigazing_helpers.obsarchive import obsarchive_model as mp, obsarchive_db
from pigazing_helpers.settings_read import settings, installation_info
from pigazing_helpers.sunset_times import alt_az, get_zenith_position, mean_angle, mean_angle_2d


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


def orientation_calc(obstory_id, utc_min, utc_max, utc_must_stop=None):
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

    # Divide up time interval into 15 minute blocks
    logging.info("Searching for images within period {} to {}".format(date_string(utc_min), date_string(utc_max)))
    block_size = 900
    minimum_sky_clarity = 500
    time_blocks = list(np.arange(start=utc_min, stop=utc_max, step=block_size))

    # Build list of images we are to analyse
    images_for_analysis = []

    for block_index, utc_block_min in enumerate(time_blocks[:-1]):
        utc_block_max = time_blocks[block_index + 1]

        # Search for background-subtracted time lapse image with best sky clarity, and no existing orientation fit,
        # within this time period
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
    logging.info("Estimating the orientation of {:d} images:".format(len(images_for_analysis)))
    for item in images_for_analysis:
        logging.info("{:17s} {:04.0f} {:32s}".format(date_string(item['utc']),
                                                     item['skyClarity'],
                                                     item['repositoryFname']))

    # When passing images to astrometry.net, only work on the central portion, as this will have least bad distortion
    fraction_x = 0.4
    fraction_y = 0.4

    # Path the binary barrel-correction tool
    barrel_correct = os.path.join(settings['imageProcessorPath'], "lensCorrect")

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

        # Look up barrel distortion
        lens_barrel_a = obstory_status.get('calibration:lens_barrel_a', lens_props.barrel_a)
        lens_barrel_b = obstory_status.get('calibration:lens_barrel_b', lens_props.barrel_b)
        lens_barrel_c = obstory_status.get('calibration:lens_barrel_c', lens_props.barrel_c)

        # 1. Copy image into working directory
        # logging.info("Copying file")
        img_name = item['repositoryFname']
        command = "cp {} {}_tmp.png".format(filename, img_name)
        # logging.info(command)
        os.system(command)

        # 2. Barrel-correct image
        # logging.info("Lens-correcting image")
        command = "{} -i {}_tmp.png -a {:.6f} -b {:.6f} -c {:.6f} -o {}_tmp2".format(barrel_correct, img_name,
                                                                                     lens_barrel_a,
                                                                                     lens_barrel_b,
                                                                                     lens_barrel_c,
                                                                                     img_name)
        # logging.info(command)
        os.system(command)

        # 3. Pass only central portion of image to astrometry.net. It's not very reliable with wide-field images
        # logging.info("Extracting central portion of image")
        d = image_dimensions("%s_tmp2.png" % img_name)
        command = """
convert {}_tmp2.png -colorspace sRGB -define png:format=png24 -crop {:d}x{:d}+{:d}+{:d} +repage {}_tmp3.png
""".format(img_name,
           int(fraction_x * d[0]), int(fraction_y * d[1]),
           int((1 - fraction_x) * d[0] / 2), int((1 - fraction_y) * d[1] / 2),
           img_name)
        # logging.info(command)
        os.system(command)

        # Check that we've not run out of time
        if utc_must_stop and (time.time() > utc_must_stop):
            logging.info("We have run out of time! Aborting.")
            continue

        # How long should we allow astrometry.net to run for?
        timeout = "2m" if settings['i_am_a_rpi'] else "30s"

        # Run astrometry.net. Insert --no-plots on the command line to speed things up.
        logging.info("Running astrometry.net")
        astrometry_start_time = time.time()
        estimated_width = 2 * math.atan(math.tan(estimated_image_scale / 2 * deg) * fraction_x) * rad
        command = """
timeout {} solve-field --no-plots --crpix-center --scale-low {:.1f} \
        --scale-high {:.1f} --odds-to-tune-up 1e4 --odds-to-solve 1e7 --overwrite {}_tmp3.png > txt 2> /dev/null \
""".format(timeout,
           estimated_width * 0.6,
           estimated_width * 1.2,
           img_name)
        # logging.info(command)
        os.system(command)

        # Report how long astrometry.net took
        astrometry_time_taken = time.time() - astrometry_start_time
        log_msg = "Astrometry.net took {:.0f} sec. ".format(astrometry_time_taken)

        # Parse the output from astrometry.net
        fit_text = open("txt").read()
        # logging.info(fit_text)
        test = re.search(r"\(RA H:M:S, Dec D:M:S\) = \(([\d-]*):(\d\d):([\d.]*), [+]?([\d-]*):(\d\d):([\d\.]*)\)",
                         fit_text)
        if not test:
            logging.info("FAIL(POS): {}".format(log_msg))
            continue

        ra_sign = sgn(float(test.group(1)))
        ra = abs(float(test.group(1))) + float(test.group(2)) / 60 + float(test.group(3)) / 3600
        if ra_sign < 0:
            ra *= -1
        dec_sign = sgn(float(test.group(4)))
        dec = abs(float(test.group(4))) + float(test.group(5)) / 60 + float(test.group(6)) / 3600
        if dec_sign < 0:
            dec *= -1
        test = re.search(r"up is [+]?([-\d\.]*) degrees (.) of N", fit_text)
        if not test:
            logging.info("FAIL(PA ): {}".format(log_msg))
            continue

        # celestial_pa is the position angle of the upward vector in the centre of the image, counterclockwise
        #  from celestial north.
        # * It is zero if the pole star is vertical above the centre of the image.
        # * If the pole star is in the top-right of an image, expect it to be around -45 degrees.
        celestial_pa = float(test.group(1))
        # * This 180 degree rotation appears because when astrometry.net says "up" it means the bottom of the image!
        celestial_pa += 180
        if test.group(2) == "W":
            celestial_pa *= -1
        while celestial_pa > 180:
            celestial_pa -= 360
        while celestial_pa < -180:
            celestial_pa += 360
        test = re.search(r"Field size: ([\d\.]*) x ([\d\.]*) deg", fit_text)
        if not test:
            logging.info("FAIL(SIZ): {}".format(log_msg))
            continue

        # Expand reported size of image to whole image, not just the central tile we sent to astrometry.net
        scale_x = 2 * math.atan(math.tan(float(test.group(1)) / 2 * deg) * (1 / fraction_x)) * rad
        scale_y = 2 * math.atan(math.tan(float(test.group(2)) / 2 * deg) * (1 / fraction_y)) * rad

        # Work out alt-az of reported (RA,Dec) using known location of camera. Fits returned in degrees.
        alt_az_pos = alt_az(ra=ra, dec=dec, utc=item['utc'],
                            latitude=obstory_info['latitude'], longitude=obstory_info['longitude'])

        # Get celestial coordinates of the local zenith
        ra_dec_zenith = get_zenith_position(latitude=obstory_info['latitude'],
                                            longitude=obstory_info['longitude'],
                                            utc=item['utc'])
        ra_zenith = ra_dec_zenith['ra']
        dec_zenith = ra_dec_zenith['dec']

        # Work out the position angle of the zenith, counterclockwise from north, as measured at centre of frame
        zenith_pa = gnomonic_project.position_angle(ra1=ra, dec1=dec, ra2=ra_zenith, dec2=dec_zenith)

        # Calculate the position angle of the zenith, clockwise from vertical, at the centre of the frame
        # If the camera is roughly upright, this ought to be close to zero!
        camera_tilt = zenith_pa - celestial_pa
        while camera_tilt < -180:
            camera_tilt += 360
        while camera_tilt > 180:
            camera_tilt -= 360

        logging.info("PASS     : {}".format(log_msg))
        logging.info("FIT      : RA: {:7.2f}h. Dec {:7.2f} deg. PA {:6.1f} deg. ScaleX {:6.1f}. ScaleY {:6.1f}. "
                     "Zenith at ({:.2f} h,{:.2f} deg). PA Zenith {:.2f} deg. "
                     "Alt: {:7.2f} deg. Az: {:7.2f} deg. Tilt: {:7.2f} deg.".format
                     (ra, dec, celestial_pa, scale_x, scale_y, ra_zenith, dec_zenith, zenith_pa,
                      alt_az_pos[0], alt_az_pos[1], camera_tilt))

        # Update observation status
        user = settings['pigazingUser']
        db.set_observation_metadata(user_id=user, observation_id=item['observationId'],
                                    meta=mp.Meta(key="orientation:ra", value=ra))
        db.set_observation_metadata(user_id=user, observation_id=item['observationId'],
                                    meta=mp.Meta(key="orientation:dec", value=dec))
        db.set_observation_metadata(user_id=user, observation_id=item['observationId'],
                                    meta=mp.Meta(key="orientation:pa", value=celestial_pa))
        db.set_observation_metadata(user_id=user, observation_id=item['observationId'],
                                    meta=mp.Meta(key="orientation:altitude", value=alt_az_pos[0]))
        db.set_observation_metadata(user_id=user, observation_id=item['observationId'],
                                    meta=mp.Meta(key="orientation:azimuth", value=alt_az_pos[1]))
        db.set_observation_metadata(user_id=user, observation_id=item['observationId'],
                                    meta=mp.Meta(key="orientation:tilt", value=camera_tilt))
        db.set_observation_metadata(user_id=user, observation_id=item['observationId'],
                                    meta=mp.Meta(key="orientation:width_x_field", value=scale_x))
        db.set_observation_metadata(user_id=user, observation_id=item['observationId'],
                                    meta=mp.Meta(key="orientation:width_y_field", value=scale_y))

        # Clean up and exit
        os.chdir(cwd)
        os.system("rm -Rf {}".format(tmp))

    # Now determine mean orientation each day
    logging.info("Averaging daily fits within period {} to {}".format(date_string(utc_min), date_string(utc_max)))
    block_size = 86400
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

    for block_index, utc_block_min in enumerate(time_blocks[:-1]):
        utc_block_max = time_blocks[block_index + 1]

        # Select observations with orientation fits
        conn.execute("""
SELECT am1.floatValue AS altitude, am2.floatValue AS azimuth, am3.floatValue AS tilt,
       am4.floatValue AS width_x_field, am5.floatValue AS width_y_field
FROM archive_observations o
INNER JOIN archive_metadata am1 ON o.uid = am1.observationId AND
    am1.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="orientation:altitude")
INNER JOIN archive_metadata am2 ON o.uid = am2.observationId AND
    am2.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="orientation:azimuth")
INNER JOIN archive_metadata am3 ON o.uid = am3.observationId AND
    am3.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="orientation:tilt")
INNER JOIN archive_metadata am4 ON o.uid = am4.observationId AND
    am4.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="orientation:width_x_field")
INNER JOIN archive_metadata am5 ON o.uid = am5.observationId AND
    am5.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="orientation:width_y_field")
WHERE
    o.observatory = (SELECT uid FROM archive_observatories WHERE publicId=%s) AND
    o.obsTime BETWEEN %s AND %s;
""", (obstory_id, utc_block_min, utc_block_max))
        results = conn.fetchall()

        logging.info("Averaging fits within period {} to {}: Found {} fits.".format(date_string(utc_block_min),
                                                                                    date_string(utc_block_max),
                                                                                    len(results)))

        # Average the fits we found
        if len(results) < 4:
            logging.info("Insufficient images to reliably average.")
            continue

        pa_list = [i['tilt'] * deg for i in results]
        camera_tilt_best = mean_angle(pa_list)[0]
        scale_x_list = [i['width_x_field'] * deg for i in results]
        scale_x_best = mean_angle(scale_x_list)[0]
        scale_y_list = [i['width_y_field'] * deg for i in results]
        scale_y_best = mean_angle(scale_y_list)[0]

        # Convert alt-az fits into radians
        alt_az_list_r = [[i['altitude'] * deg, i['azimuth'] * deg] for i in results]
        [alt_az_best, alt_az_error] = mean_angle_2d(alt_az_list_r)

        # Print fit information
        success = (alt_az_error * rad < 0.6)
        adjective = "SUCCESSFUL" if success else "REJECTED"
        logging.info("""\
{} ORIENTATION FIT from {:2d} images: Alt: {:.2f} deg. Az: {:.2f} deg. PA: {:.2f} deg. \
ScaleX: {:.2f} deg. ScaleY: {:.2f} deg. Uncertainty: {:.2f} deg.\
""".format(adjective, len(results),
           alt_az_best[0] * rad,
           alt_az_best[1] * rad,
           camera_tilt_best * rad,
           scale_x_best * rad,
           scale_y_best * rad,
           alt_az_error * rad))

        # Update observation status
        if success:
            user = settings['pigazingUser']
            db.register_obstory_metadata(obstory_id=obstory_id, key="orientation:altitude",
                                         value=alt_az_best[0] * rad,
                                         metadata_time=utc_block_min, user_created=user)
            db.register_obstory_metadata(obstory_id=obstory_id, key="orientation:azimuth",
                                         value=alt_az_best[1] * rad,
                                         metadata_time=utc_block_min, user_created=user)
            db.register_obstory_metadata(obstory_id=obstory_id, key="orientation:tilt",
                                         value=camera_tilt_best * rad,
                                         metadata_time=utc_block_min, user_created=user)
            db.register_obstory_metadata(obstory_id=obstory_id, key="orientation:width_x_field",
                                         value=scale_x_best * rad,
                                         metadata_time=utc_block_min, user_created=user)
            db.register_obstory_metadata(obstory_id=obstory_id, key="orientation:width_y_field",
                                         value=scale_y_best * rad,
                                         metadata_time=utc_block_min, user_created=user)

    # Clean up and exit
    db.commit()
    db.close_db()
    return


def flush_orientation(obstory_id, utc_min, utc_max):
    # Open connection to database
    [db0, conn] = connect_db.connect_db()

    # Delete observatory metadata fields that start 'orientation:*'
    conn.execute("""
DELETE m
FROM archive_metadata m
WHERE
    fieldId IN (SELECT uid FROM archive_metadataFields WHERE metaKey LIKE 'orientation:*') AND
    m.observatory = (SELECT uid FROM archive_observatories WHERE publicId=%s) AND
    m.time BETWEEN %s AND %s;
""", (obstory_id, utc_min, utc_max))

    # Delete observation metadata fields that start 'orientation:*'
    conn.execute("""
DELETE m
FROM archive_metadata m
INNER JOIN archive_observations o ON m.observationId = o.uid
WHERE
    fieldId IN (SELECT uid FROM archive_metadataFields WHERE metaKey LIKE 'orientation:*') AND
    o.observatory = (SELECT uid FROM archive_observatories WHERE publicId=%s) AND
    o.obsTime BETWEEN %s AND %s;
""", (obstory_id, utc_min, utc_max))

    # Commit changes to database
    db0.commit()
    conn.close()
    db0.close()


# If we're called as a script, run the method orientationCalc()
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
    logger.info(__doc__.strip())

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
