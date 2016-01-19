#!../../virtual-env/bin/python
# orientationCalc.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# Use astrometry.net to calculate the orientation of the camera based on recent images

import os
import sys
import time
import re
import subprocess
import math

import meteorpi_db
import meteorpi_model as mp

import mod_astro
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


def orientation_calc(obstory_name, utc_to_study, utc_now, utc_must_stop=0):
    log_txt("Starting calculation of camera alignment")

    # Mathematical constants
    deg = math.pi / 180
    rad = 180 / math.pi

    # When passing images to astrometry.net, only work on the central portion, as this will have least bad distortion
    fraction_x = 0.6
    fraction_y = 0.6

    # Path the binary barrel-correction tool
    barrel_correct = os.path.join(mod_settings.settings['stackerPath'], "bin", "barrel")

    # Calculate time span to use images from
    utc_min = utc_to_study
    utc_max = utc_to_study + 3600 * 24
    db = meteorpi_db.MeteorDatabase(mod_settings.settings['dbFilestore'])

    # Fetch observatory status
    obstory_status = db.get_camera_status(camera_id=obstory_name, time=utc_now)
    if not obstory_status:
        log_txt("Aborting -- no camera status set for camera <%s>" % obstory_name)
        return

    # Search for background-subtracted time lapse photography within this range
    search = mp.FileRecordSearch(obstory_ids=[obstory_name], semantic_type="meteorpi:timelapse/frame/bgrdSub",
                                 time_min=utc_min, time_max=utc_max, limit=1000000)
    files = db.search_files(search)
    files = files['files']
    log_txt("%d candidate time-lapse images in past 24 hours" % len(files))

    # Filter out files where the sky clarity is good and the Sun is well below horizon
    acceptable_files = []
    for f in files:
        if db.get_file_metadata(f.id, 'skyClarity') < 15:
            continue
        if db.get_file_metadata(f.id, 'sunAlt') > -4:
            continue
        acceptable_files.append(f)

    log_txt("%d acceptable images found for alignment (others do not have good sky quality)" % len(acceptable_files))

    # If we don't have enough images, we can't proceed to get a secure orientation fit
    if len(acceptable_files) < 10:
        log_txt("Giving up: not enough suitable images")
        return

    # We can't afford to run astrometry.net on too many images, so pick the 20 best ones
    acceptable_files.sort(key=lambda f: db.get_file_metadata(f.id, 'skyClarity'))
    acceptable_files.reverse()
    acceptable_files = acceptable_files[0:24]

    # Make a temporary directory to store files in.
    # This is necessary as astrometry.net spams the cwd with lots of temporary junk
    cwd = os.getcwd()
    pid = os.getpid()
    tmp = "/tmp/dcf21_orientationCalc_%d" % pid
    log_txt("Created temporary directory <%s>" % tmp)
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
        log_txt("Determining orientation of image with timestamp <%s> (unix time %d) -- skyClarity=%.1f" % (
            mod_astro.time_print(f.file_time), f.file_time, db.get_file_metadata(f.id, 'skyClarity')))
        filename = f.get_path()

        # 1. Copy image into working directory
        os.system("cp %s %s_tmp.png" % (filename, img_name))

        # 2. Barrel-correct image
        os.system("%s %s_tmp.png %.6f %.6f %.6f %s_tmp2.png" % (barrel_correct, img_name,
                                                                obstory_status['lens_barrel_a'],
                                                                obstory_status['lens_barrel_b'],
                                                                obstory_status['lens_barrel_c'],
                                                                img_name))

        # 3. Pass only central portion of image to astrometry.net. It's not very reliable with wide-field images
        d = image_dimensions("%s_tmp2.png" % (img_name))
        os.system(
                "convert %s_tmp2.png -colorspace sRGB -define png:format=png24 -crop %dx%d+%d+%d +repage %s_tmp3.png"
                % (img_name,
                   fraction_x * d[0], fraction_y * d[1],
                   (1 - fraction_x) * d[0] / 2, (1 - fraction_y) * d[1] / 2,
                   img_name))

        # 4. Slightly blur image to remove grain
        os.system("convert %s_tmp3.png -colorspace sRGB -define png:format=png24 -gaussian-blur 8x2.5 %s_tmp4.png"
                  % (img_name, img_name))

        fit_obj['fname_processed'] = '%s_tmp3.png' % img_name
        fit_obj['fname_original'] = '%s_tmp.png' % img_name
        fit_obj['dims'] = d  # Dimensions of *original* image

        count += 1

    # Now pass processed image to astrometry.net for alignment
    for fit in fits:
        f = fit['f']

        # Run astrometry.net. Insert --no-plots on the command line to speed things up.
        astrometry_start_time = time.time()
        os.system("timeout 10m /usr/local/astrometry/bin/solve-field --no-plots --crpix-center --overwrite %s > txt"
                  % (fit['fname_processed']))
        astrometry_time_taken = time.time() - astrometry_start_time
        log_txt("Astrometry.net took %d seconds to analyse image at time <%s>" % (astrometry_time_taken, f.file_time))

        # Parse the output from astrometry.net
        fit_text = open("txt").read()
        test = re.search(r"\(RA H:M:S, Dec D:M:S\) = \(([\d-]*):(\d\d):([\d.]*), [+]?([\d-]*):(\d\d):([\d\.]*)\)",
                         fit_text)
        if not test:
            log_txt("Failed. Cannot read central RA and Dec from image at <%s>" % f.file_time)
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
            log_txt("Failed. Cannot read position angle from image at <%s>" % f.file_time)
            continue

        # This 180 degree rotation appears to be a bug in astrometry.net (pos angles relative to south, not north)
        posang = float(test.group(1)) + 180
        while posang > 180:
            posang -= 360
        if test.group(2) == "W":
            posang *= -1
        test = re.search(r"Field size: ([\d\.]*) x ([\d\.]*) deg", fit_text)
        if not test:
            log_txt("Failed. Cannot read field size from image at <%s>" % f.file_time)
            continue

        # Expand size of image to whole image, not just the central tile we sent to astrometry.net
        scale_x = 2 * math.atan(math.tan(float(test.group(1)) / 2 * deg) * (1 / fraction_x)) * rad
        scale_y = 2 * math.atan(math.tan(float(test.group(2)) / 2 * deg) * (1 / fraction_y)) * rad
        fit.update({'fit': True, 'ra': ra, 'dec': dec, 'pa': posang, 'sx': scale_x, 'sy': scale_y})
        log_txt("Success. RA: %7.2fh. Dec %7.2f deg. PA %6.1f deg. ScaleX %6.1f. ScaleY %6.1f." % (
            ra, dec, posang, scale_x, scale_y))
        fit_list.append(fit)

        # Work out alt-az of each fitted position from known location of camera. Fits returned in degrees.
        alt_az = mod_astro.alt_az(fit['ra'], fit['dec'], fit['f'].file_time,
                                  obstory_status['latitude'], obstory_status['longitude'])
        log_txt("Alt: %7.2f deg. Az: %7.2f deg." % (alt_az[0], alt_az[1]))
        alt_az_list.append(alt_az)

    # Average the resulting fits
    if len(fit_list) < 3:
        log_txt("Giving up: astrometry.net only managed to fit %d images." % len(fit_list))
        return None
    else:
        log_txt("astrometry.net managed to fit %d images out of %d." % (len(fit_list), len(fits)))

    pa_list = [i['pa'] * deg for i in fits if i['fit']]
    pa_best = mod_astro.mean_angle(pa_list)[0]
    scale_x_list = [i['sx'] * deg for i in fits if i['fit']]
    scale_x_best = mod_astro.mean_angle(scale_x_list)[0]
    scale_y_list = [i['sy'] * deg for i in fits if i['fit']]
    scale_y_best = mod_astro.mean_angle(scale_y_list)[0]

    # Convert alt-az fits into radians
    alt_az_list_r = [[i * deg for i in j] for j in alt_az_list]
    [alt_az_best, alt_az_error] = mod_astro.mean_angle_2d(alt_az_list_r)

    # Print fit information
    log_txt("Orientation fit. "
            "Alt: %.2f deg. Az: %.2f deg. PA: %.2f deg. ScaleX: %.2f deg. ScaleY: %.2f deg. "
            "Uncertainty: %.2f deg." % (alt_az_best[0] * rad,
                                        alt_az_best[1] * rad,
                                        pa_best * rad,
                                        scale_x_best * rad,
                                        scale_y_best * rad,
                                        alt_az_error * rad))

    # Update observatory status
    user = mod_settings.settings['meteorpiUser']
    utc = utc_to_study
    db.register_obstory_metadata(obstory_name, "orientation_altitude", alt_az_best[0] * rad, utc, user)
    db.register_obstory_metadata(obstory_name, "orientation_azimuth", alt_az_best[1] * rad, utc, user)
    db.register_obstory_metadata(obstory_name, "orientation_error", alt_az_error * rad, utc, user)
    db.register_obstory_metadata(obstory_name, "orientation_pa", pa_best * rad * rad, utc, user)
    db.register_obstory_metadata(obstory_name, "orientation_width_field", scale_x_best * rad, utc, user)

    # Output catalogue of image fits -- this is to be fed into the lens-fitting code
    f = open("imageFits.gnom", "w")
    f.write("SET output /tmp/output.png\n")
    f.write("SET barrel_a %.6f\n" % obstory_status['lens_barrel_a'])
    f.write("SET barrel_b %.6f\n" % obstory_status['lens_barrel_b'])
    f.write("SET barrel_c %.6f\n" % obstory_status['lens_barrel_c'])
    f.write("SET latitude %s\n" % obstory_status['latitude'])
    f.write("SET longitude %s\n" % obstory_status['longitude'])

    # Exposure compensation, x_size, y_size, Central RA, Central Dec, position angle, scale_x, scale_y
    fit = fit_list[int(math.floor(len(fit_list) / 2))]
    f.write("%-102s %4.1f %4d %4d %10.5f %10.5f %10.5f %10.5f %10.5f\n"
            % ("GNOMONIC", 1, fit['dims'][0], fit['dims'][1],
               fit['ra'], fit['dec'], fit['pa'],
               fit['sx'], fit['sy'])
            )
    for fit in fits:
        if fit['fit']:
            d = fit['dims']
            f.write("ADD %-93s %4.1f %4.1f %4d %4d %10.5f %10.5f %10.5f %10.5f %10.5f\n" % (
                fit['fname_original'], 1, 1, d[0], d[1], fit['ra'], fit['dec'], fit['pa'], fit['sx'], fit['sy']))
        else:
            f.write("# Cannot read central RA and Dec from %s\n" % (fit['fname_original']))
    f.close()

    # Run <gnomonicStack/align_regularise.py> which uses the fact that we know camera's pointing is fixed to fix
    # in central RA and Dec for image astrometry.net failed on
    os.system("%s/align_regularise.py %s > %s" % (mod_settings.settings['stackerPath'],
                                                  "imageFits.gnom",
                                                  "imageFits_2.gnom"))

    # Clean up and exit
    os.chdir(cwd)
    return os.path.join(tmp, "imageFits_2.gnom")


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
    orientation_calc(_obstory_name, _utc_to_study, _utc_now, 0)
