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
import os
import time
import re
import subprocess
import math
import numpy as np

from pigazing_helpers.obsarchive import obsarchive_model as mp, obsarchive_db
from pigazing_helpers import connect_db, dcf_ast, gnomonic_project, hardware_properties
from pigazing_helpers.settings_read import settings, installation_info


# Return the dimensions of an image
def image_dimensions(f):
    d = subprocess.check_output(["identify", f]).split()[2].split("x")
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
    deg = math.pi / 180
    rad = 180 / math.pi

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

    # Divide up time interval into 30 minute blocks
    block_size = 1800
    time_blocks = np.arange(start=utc_min, stop=utc_max, step=block_size)

    for utc_block_min in time_blocks:
        utc_block_max = utc_block_min + block_size

        # Fetch observatory status
        obstory_status = db.get_obstory_status(obstory_id=obstory_id, time=utc_block_max)
        lens_name = obstory_status['lens']
        lens_props = hw.lens_data[lens_name]

        # This is an estimate of the *maximum* angular width we expect images to have.
        # It should be within a factor of two of correct!
        estimated_image_scale = lens_props.fov


        # Search for background-subtracted time lapse photography within this range
    search = mp.FileRecordSearch(obstory_ids=[obstory_id], semantic_type="pigazing:timelapse/frame/bgrdSub",
                                 time_min=utc_min, time_max=utc_max, limit=1000000)
    files = db.search_files(search)
    files = files['files']

    # When passing images to astrometry.net, only work on the central portion, as this will have least bad distortion
    fraction_x = 0.4
    fraction_y = 0.4

    # Path the binary barrel-correction tool
    barrel_correct = os.path.join(settings['imageProcessorPath'], "barrel")

    # Fetch observatory status
    obstory_info = db.get_obstory_from_id(obstory_id)
    obstory_status = None
    if obstory_info and ('name' in obstory_info):
        obstory_status = db.get_obstory_status(obstory_id=obstory_id, time=utc_now)
    if not obstory_status:
        logging.info("%s Aborting -- no observatory status available." % log_prefix)
        db.close_db()
        return
    obstory_name = obstory_info['name']

    # Search for background-subtracted time lapse photography within this range
    search = mp.FileRecordSearch(obstory_ids=[obstory_id], semantic_type="pigazing:timelapse/frame/bgrdSub",
                                 time_min=utc_min, time_max=utc_max, limit=1000000)
    files = db.search_files(search)
    files = files['files']

    # Filter out files where the sky clarity is good and the Sun is well below horizon
    acceptable_files = []
    for f in files:
        if db.get_file_metadata(f.id, 'pigazing:skyClarity') < 27:
            continue
        if db.get_file_metadata(f.id, 'pigazing:sunAlt') > -4:
            continue
        acceptable_files.append(f)

    log_msg = ("%s %d still images in search period. %d meet sky quality requirements." %
               (log_prefix, len(files), len(acceptable_files)))

    # If we don't have enough images, we can't proceed to get a secure orientation fit
    if len(acceptable_files) < 6:
        logging.info("%s Not enough suitable images." % log_msg)
        db.close_db()
        return
    logging.info(log_msg)

    # We can't afford to run astrometry.net on too many images, so pick the 20 best ones
    acceptable_files.sort(key=lambda f: db.get_file_metadata(f.id, 'pigazing:skyClarity'))
    acceptable_files.reverse()
    acceptable_files = acceptable_files[0:20]

    # Make a temporary directory to store files in.
    # This is necessary as astrometry.net spams the cwd with lots of temporary junk
    cwd = os.getcwd()
    pid = os.getpid()
    tmp = "/tmp/dcf21_orientationCalc_%d" % pid
    # logging.info("Created temporary directory <%s>" % tmp)
    os.system("mkdir %s" % tmp)
    os.chdir(tmp)

    # Loop over selected images and use astrometry.net to find their orientation
    fits = []
    fit_list = []
    alt_az_list = []
    count = 0
    for f in acceptable_files:
        img_name = f.file_name
        fit_obj = {'f': f, 'i': count, 'fit': False}
        fits.append(fit_obj)
        filename = db.file_path_for_id(f.id)

        if not os.path.exists(filename):
            logging.info("%s Error! File <%s> is missing!" % (log_prefix, filename))
            continue

        # 1. Copy image into working directory
        os.system("cp %s %s_tmp.png" % (filename, img_name))

        # 2. Barrel-correct image
        os.system("%s %s_tmp.png %.6f %.6f %.6f %s_tmp2.png" % (barrel_correct, img_name,
                                                                obstory_status['lens_barrel_a'],
                                                                obstory_status['lens_barrel_b'],
                                                                obstory_status['lens_barrel_c'],
                                                                img_name))

        # 3. Pass only central portion of image to astrometry.net. It's not very reliable with wide-field images
        d = image_dimensions("%s_tmp2.png" % img_name)
        os.system(
                "convert %s_tmp2.png -colorspace sRGB -define png:format=png24 -crop %dx%d+%d+%d +repage %s_tmp3.png"
                % (img_name,
                   fraction_x * d[0], fraction_y * d[1],
                   (1 - fraction_x) * d[0] / 2, (1 - fraction_y) * d[1] / 2,
                   img_name))

        fit_obj['fname_processed'] = '%s_tmp3.png' % img_name
        fit_obj['fname_original'] = '%s_tmp.png' % img_name
        fit_obj['dims'] = d  # Dimensions of *original* image

        count += 1

    # Now pass processed image to astrometry.net for alignment
    for fit in fits:
        f = fit['f']

        # Check that we've not run out of time
        if utc_must_stop and (time.time() > utc_must_stop):
            logging.info("%s We have run out of time! Aborting." % log_prefix)
            continue

        log_msg = ("Processed image <%s> from time <%s> -- skyClarity=%.1f. " %
                   (f.id, dcf_ast.date_string(f.file_time),
                    db.get_file_metadata(f.id, 'pigazing:skyClarity')))

        # How long should we allow astrometry.net to run for?
        if settings['i_am_a_rpi']:
            timeout = "6m"
        else:
            timeout = "50s"

        # Run astrometry.net. Insert --no-plots on the command line to speed things up.
        astrometry_start_time = time.time()
        estimated_width = 2 * math.atan(math.tan(estimated_image_scale / 2 * deg) * fraction_x) * rad
        os.system("timeout %s /usr/local/astrometry/bin/solve-field --no-plots --crpix-center --scale-low %.1f "
                  "--scale-high %.1f --odds-to-tune-up 1e4 --odds-to-solve 1e7 --overwrite %s > txt"
                  % (timeout,
                     estimated_width * 0.6,
                     estimated_width * 1.2,
                     fit['fname_processed']))
        astrometry_time_taken = time.time() - astrometry_start_time
        log_msg += ("Astrometry.net took %d sec. " % astrometry_time_taken)

        # Parse the output from astrometry.net
        fit_text = open("txt").read()
        # logging.info(fit_text)
        test = re.search(r"\(RA H:M:S, Dec D:M:S\) = \(([\d-]*):(\d\d):([\d.]*), [+]?([\d-]*):(\d\d):([\d\.]*)\)",
                         fit_text)
        if not test:
            logging.info("%s FAIL(POS): %s" % (log_prefix, log_msg))
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
            logging.info("%s FAIL(PA ): %s" % (log_prefix, log_msg))
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
            logging.info("%s FAIL(SIZ): %s" % (log_prefix, log_msg))
            continue

        # Expand reported size of image to whole image, not just the central tile we sent to astrometry.net
        scale_x = 2 * math.atan(math.tan(float(test.group(1)) / 2 * deg) * (1 / fraction_x)) * rad
        scale_y = 2 * math.atan(math.tan(float(test.group(2)) / 2 * deg) * (1 / fraction_y)) * rad

        # Work out alt-az of reported (RA,Dec) using known location of camera. Fits returned in degrees.
        alt_az = dcf_ast.alt_az(ra, dec, fit['f'].file_time,
                                  obstory_status['latitude'], obstory_status['longitude'])

        # Get celestial coordinates of the local zenith
        ra_dec_zenith = dcf_ast.get_zenith_position(obstory_status['latitude'],
                                                      obstory_status['longitude'],
                                                      fit['f'].file_time)
        ra_zenith = ra_dec_zenith['ra']
        dec_zenith = ra_dec_zenith['dec']

        # Work out the position angle of the zenith, counterclockwise from north, as measured at centre of frame
        zenith_pa = gnomonic_project.position_angle(ra, dec, ra_zenith, dec_zenith)

        # Calculate the position angle of the zenith, clockwise from vertical, at the centre of the frame
        # If the camera is roughly upright, this ought to be close to zero!
        camera_tilt = zenith_pa - celestial_pa
        while camera_tilt < -180:
            camera_tilt += 360
        while camera_tilt > 180:
            camera_tilt -= 360

        logging.info("%s PASS     : %s" % (log_prefix, log_msg))
        logging.info("%s FIT      : RA: %7.2fh. Dec %7.2f deg. PA %6.1f deg. ScaleX %6.1f. ScaleY %6.1f. "
                "Zenith at (%.2f h,%.2f deg). PA Zenith %.2f deg. "
                "Alt: %7.2f deg. Az: %7.2f deg. Tilt: %7.2f deg." %
                (log_prefix, ra, dec, celestial_pa, scale_x, scale_y, ra_zenith, dec_zenith, zenith_pa,
                 alt_az[0], alt_az[1], camera_tilt))

        # Store information about fit
        fit.update({'fit': True, 'ra': ra, 'dec': dec, 'pa': celestial_pa, 'sx': scale_x, 'sy': scale_y,
                    'camera_tilt': camera_tilt})
        fit_list.append(fit)
        alt_az_list.append(alt_az)

    # Average the resulting fits
    if len(fit_list) < 4:
        logging.info("%s ABORT    : astrometry.net only managed to fit %2d images." % (log_prefix, len(fit_list)))
        db.close_db()
        os.chdir(cwd)
        os.system("rm -Rf %s" % tmp)
        return

    pa_list = [i['camera_tilt'] * deg for i in fits if i['fit']]
    pa_best = dcf_ast.mean_angle(pa_list)[0]
    scale_x_list = [i['sx'] * deg for i in fits if i['fit']]
    scale_x_best = dcf_ast.mean_angle(scale_x_list)[0]
    scale_y_list = [i['sy'] * deg for i in fits if i['fit']]
    scale_y_best = dcf_ast.mean_angle(scale_y_list)[0]

    # Convert alt-az fits into radians
    alt_az_list_r = [[i * deg for i in j] for j in alt_az_list]
    [alt_az_best, alt_az_error] = dcf_ast.mean_angle_2d(alt_az_list_r)

    # Print fit information
    success = (alt_az_error * rad < 0.6)
    if success:
        adjective = "SUCCESSFUL"
    else:
        adjective = "REJECTED"
    logging.info("%s %s ORIENTATION FIT (from %2d images). "
            "Alt: %.2f deg. Az: %.2f deg. PA: %.2f deg. ScaleX: %.2f deg. ScaleY: %.2f deg. "
            "Uncertainty: %.2f deg." % (log_prefix, adjective, len(fit_list),
                                        alt_az_best[0] * rad,
                                        alt_az_best[1] * rad,
                                        pa_best * rad,
                                        scale_x_best * rad,
                                        scale_y_best * rad,
                                        alt_az_error * rad))

    # Update observatory status
    if success:
        user = settings['pigazingUser']
        utc = utc_to_study
        db.register_obstory_metadata(obstory_name, "orientation_altitude", alt_az_best[0] * rad, utc, user)
        db.register_obstory_metadata(obstory_name, "orientation_azimuth", alt_az_best[1] * rad, utc, user)
        db.register_obstory_metadata(obstory_name, "orientation_error", alt_az_error * rad, utc, user)
        db.register_obstory_metadata(obstory_name, "orientation_pa", pa_best * rad, utc, user)
        db.register_obstory_metadata(obstory_name, "orientation_width_x_field", scale_x_best * rad, utc, user)
        db.register_obstory_metadata(obstory_name, "orientation_width_y_field", scale_y_best * rad, utc, user)
    db.commit()
    db.close_db()

    # Clean up and exit
    os.chdir(cwd)
    os.system("rm -Rf %s" % tmp)
    return


def flush_orientation(obstory_id, utc_min, utc_max):
    # Open connection to database
    [db0, conn] = connect_db.connect_db()

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

    parser.add_argument('--observatory', dest='obstory_id', default=None,
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
