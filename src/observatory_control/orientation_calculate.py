#!../../virtualenv/bin/python3
# -*- coding: utf-8 -*-
# orientation_calculate.py
#
# -------------------------------------------------
# Copyright 2015-2018 Dominic Ford
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


import os
import sys
import time
import re
import subprocess
import math

import pigazing_db
import pigazing_model as mp

from pigazing_helpers import dcf_ast
import mod_gnomonic
import mod_log
from mod_log import log_txt
import mod_settings
import installation_info


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


def orientation_calc(obstory_id, utc_to_study, utc_now, utc_must_stop=0):
    log_prefix = "[%12s %s]" % (obstory_id, dcf_ast.date_string(utc_to_study))

    logger.info("%s Starting calculation of camera alignment" % log_prefix)

    # Mathematical constants
    deg = math.pi / 180
    rad = 180 / math.pi

    # This is an estimate of the *maximum* angular width we expect images to have.
    # It should be within a factor of two of correct!
    estimated_image_scale = installation_info.local_conf['estimatedImageScale']

    # When passing images to astrometry.net, only work on the central portion, as this will have least bad distortion
    fraction_x = 0.4
    fraction_y = 0.4

    # Path the binary barrel-correction tool
    barrel_correct = os.path.join(mod_settings.settings['stackerPath'], "barrel")

    # Calculate time span to use images from
    utc_min = utc_to_study
    utc_max = utc_to_study + 3600 * 24
    db = pigazing_db.MeteorDatabase(mod_settings.settings['dbFilestore'])

    # Fetch observatory status
    obstory_info = db.get_obstory_from_id(obstory_id)
    obstory_status = None
    if obstory_info and ('name' in obstory_info):
        obstory_status = db.get_obstory_status(obstory_name=obstory_info['name'], time=utc_now)
    if not obstory_status:
        logger.info("%s Aborting -- no observatory status available." % log_prefix)
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
        logger.info("%s Not enough suitable images." % log_msg)
        db.close_db()
        return
    logger.info(log_msg)

    # We can't afford to run astrometry.net on too many images, so pick the 20 best ones
    acceptable_files.sort(key=lambda f: db.get_file_metadata(f.id, 'pigazing:skyClarity'))
    acceptable_files.reverse()
    acceptable_files = acceptable_files[0:20]

    # Make a temporary directory to store files in.
    # This is necessary as astrometry.net spams the cwd with lots of temporary junk
    cwd = os.getcwd()
    pid = os.getpid()
    tmp = "/tmp/dcf21_orientationCalc_%d" % pid
    # logger.info("Created temporary directory <%s>" % tmp)
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
            logger.info("%s Error! File <%s> is missing!" % (log_prefix, filename))
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
        if utc_must_stop and (mod_log.get_utc() > utc_must_stop):
            logger.info("%s We have run out of time! Aborting." % log_prefix)
            continue

        log_msg = ("Processed image <%s> from time <%s> -- skyClarity=%.1f. " %
                   (f.id, dcf_ast.date_string(f.file_time),
                    db.get_file_metadata(f.id, 'pigazing:skyClarity')))

        # How long should we allow astrometry.net to run for?
        if mod_settings.settings['i_am_a_rpi']:
            timeout = "6m"
        else:
            timeout = "50s"

        # Run astrometry.net. Insert --no-plots on the command line to speed things up.
        astrometry_start_time = mod_log.get_utc()
        estimated_width = 2 * math.atan(math.tan(estimated_image_scale / 2 * deg) * fraction_x) * rad
        os.system("timeout %s /usr/local/astrometry/bin/solve-field --no-plots --crpix-center --scale-low %.1f "
                  "--scale-high %.1f --odds-to-tune-up 1e4 --odds-to-solve 1e7 --overwrite %s > txt"
                  % (timeout,
                     estimated_width * 0.6,
                     estimated_width * 1.2,
                     fit['fname_processed']))
        astrometry_time_taken = mod_log.get_utc() - astrometry_start_time
        log_msg += ("Astrometry.net took %d sec. " % astrometry_time_taken)

        # Parse the output from astrometry.net
        fit_text = open("txt").read()
        # logger.info(fit_text)
        test = re.search(r"\(RA H:M:S, Dec D:M:S\) = \(([\d-]*):(\d\d):([\d.]*), [+]?([\d-]*):(\d\d):([\d\.]*)\)",
                         fit_text)
        if not test:
            logger.info("%s FAIL(POS): %s" % (log_prefix, log_msg))
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
            logger.info("%s FAIL(PA ): %s" % (log_prefix, log_msg))
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
            logger.info("%s FAIL(SIZ): %s" % (log_prefix, log_msg))
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

        logger.info("%s PASS     : %s" % (log_prefix, log_msg))
        logger.info("%s FIT      : RA: %7.2fh. Dec %7.2f deg. PA %6.1f deg. ScaleX %6.1f. ScaleY %6.1f. "
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
        logger.info("%s ABORT    : astrometry.net only managed to fit %2d images." % (log_prefix, len(fit_list)))
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
    logger.info("%s %s ORIENTATION FIT (from %2d images). "
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
        user = mod_settings.settings['pigazingUser']
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


def reprocess_all_data(obstory_id):
    db = pigazing_db.MeteorDatabase(mod_settings.settings['dbFilestore'])
    db.con.execute("SELECT m.time FROM archive_metadata m "
                   "INNER JOIN archive_observatories l ON m.observatory = l.uid "
                   "AND l.publicId = %s AND m.time>0 "
                   "ORDER BY m.time ASC LIMIT 1",
                   (obstory_id,))
    first_seen = 0
    results = db.con.fetchall()
    if results:
        first_seen = results[0]['time']
    db.con.execute("SELECT m.time FROM archive_metadata m "
                   "INNER JOIN archive_observatories l ON m.observatory = l.uid "
                   "AND l.publicId = %s AND m.time>0 "
                   "ORDER BY m.time DESC LIMIT 1",
                   (obstory_id,))
    last_seen = 0
    results = db.con.fetchall()
    if results:
        last_seen = results[0]['time']
    day = 86400
    utc = math.floor(first_seen / day) * day + day / 2
    while utc < last_seen:
        orientation_calc(obstory_id=obstory_id,
                         utc_to_study=utc,
                         utc_now=mod_log.get_utc(),
                         utc_must_stop=0)
        utc += day


# If we're called as a script, run the method orientationCalc()
if __name__ == "__main__":
    _obstory_name = installation_info.local_conf['observatoryName']
    _utc_now = mod_log.get_utc()
    if len(sys.argv) > 1:
        _obstory_name = sys.argv[1]
    if len(sys.argv) > 2:
        _utc_now = float(sys.argv[2])
    _utc_to_study = _utc_now - 3600 * 24  # By default, study images taken over past 24 hours
    mod_log.set_utc_offset(_utc_now - time.time())
    orientation_calc(obstory_id=_obstory_name,
                     utc_to_study=_utc_to_study,
                     utc_now=_utc_now,
                     utc_must_stop=0)
