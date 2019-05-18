#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# main.py
#
# -------------------------------------------------
# Copyright 2015-2019 Dominic Ford
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
Observatory controller
"""

import datetime
import json
import logging
import os
import subprocess
import time

from pigazing_helpers import dcf_ast, sunset_times, relay_control
from pigazing_helpers.obsarchive import obsarchive_db
from pigazing_helpers.settings_read import settings, installation_info, known_observatories

from daytimeTaskDefinitions import check_observatory_exists


# Spawn a separate process and run <gps_fix.py>. If we have a USB GPS dongle attached, this may tell us the time
# and our location. If it does, return this, otherwise return None.
def get_gps_fix():
    logging.info("Waiting for GPS link")

    # Run gpsFix.py, which returns JSON output to stdout
    # Use shell timeout command instead of python's check_output timeout argument, because the latter is unreliable
    cmd_ = "timeout 30s " + os.path.join(settings['pythonPath'], "observe", "gpsFix.py")
    try:
        gps_fix_json = subprocess.check_output(cmd_, shell=True, timeout=40)
        gps_result = json.loads(gps_fix_json)
    except (subprocess.CalledProcessError, ValueError):
        logging.info("Could not read valid JSON response from gpsFix.py")
        gps_result = False

    # If true, we get a structure with fields "offset", "latitude" and "longitude"
    if isinstance(gps_result, dict):
        clock_offset = gps_result['clock_offset']
        gps_latitude = gps_result['latitude']
        gps_longitude = gps_result['longitude']
        gps_altitude = gps_result['altitude']
        logging.info("GPS link achieved")
        logging.info("Longitude = {:.6f} ; Latitude = {:.6f} ; Altitude = {:.6f} ; Clock offset: {:.3f} sec."
                     .format(gps_longitude, gps_latitude, gps_altitude, clock_offset))

        # Use the time shell command to update the system clock (required root access)
        logging.info("Trying to update system clock")
        utc_now = time.time() - clock_offset
        os.system("date -s @%d" % utc_now)

        # Return our geographic position
        return {'latitude': gps_latitude, 'longitude': gps_longitude, 'altitude': gps_altitude}

    # If false, we didn't manage to establish a GPS link
    else:
        logging.info("Gave up waiting for a GPS link")
        return None


def observing_loop():
    obstory_id = installation_info['observatoryId']

    db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                           db_host=installation_info['mysqlHost'],
                                           db_user=installation_info['mysqlUser'],
                                           db_password=installation_info['mysqlPassword'],
                                           db_name=installation_info['mysqlDatabase'],
                                           obstory_id=installation_info['observatoryId'])

    logging.info("Observatory controller launched")

    # Make sure we have created the directory structure where observations live
    os.system("mkdir -p {}/rawvideo".format(settings['dataPath']))

    # Fetch observatory status, e.g. location, etc
    logging.info("Fetching observatory status")
    latitude = known_observatories[obstory_id]['latitude']
    longitude = known_observatories[obstory_id]['longitude']
    altitude = 0
    latest_position_update = 0
    flag_gps = 0

    # Make sure that observatory exists in the database
    check_observatory_exists(db_handle=db, obs_id=obstory_id)

    # Record the software version being used
    db.register_obstory_metadata(obstory_id=obstory_id,
                                 key="softwareVersion",
                                 value=settings['softwareVersion'],
                                 metadata_time=time.time(),
                                 time_created=time.time(),
                                 user_created=settings['pigazingUser'])

    # Fetch updated observatory status
    obstory_status = db.get_obstory_status(obstory_id=obstory_id)

    # Create clipping region mask file
    mask_file = "/tmp/triggermask_%d.txt" % os.getpid()
    open(mask_file, "w").write(
        "\n\n".join(
            ["\n".join([("%d %d" % tuple(p)) for p in point_list])
             for point_list in json.loads(obstory_status["clippingRegion"])]
        )
    )

    # Commit updates to the database
    db.commit()
    db.close_db()
    del db

    # Start main observing loop
    while True:
        # Get a new MySQL connection because old one may not be connected any longer
        db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                               db_host=installation_info['mysqlHost'],
                                               db_user=installation_info['mysqlUser'],
                                               db_password=installation_info['mysqlPassword'],
                                               db_name=installation_info['mysqlDatabase'],
                                               obstory_id=installation_info['observatoryId'])

        # Get a GPS fix on the current time and our location
        gps_fix = get_gps_fix()
        if gps_fix:
            latitude = gps_fix['latitude']
            longitude = gps_fix['longitude']
            altitude = gps_fix['altitude']
            flag_gps = 1

        # If we've not stored a GPS fix in the database within the past hour, do so now
        if flag_gps or (time.time() > latest_position_update + 3600):
            latest_position_update = time.time()
            db.register_obstory_metadata(obstory_id=obstory_id,
                                         key="latitude_gps",
                                         value=latitude,
                                         metadata_time=time.time(),
                                         time_created=time.time(),
                                         user_created=settings['pigazingUser'])
            db.register_obstory_metadata(obstory_id=obstory_id,
                                         key="longitude_gps",
                                         value=longitude,
                                         metadata_time=time.time(),
                                         time_created=time.time(),
                                         user_created=settings['pigazingUser'])
            db.register_obstory_metadata(obstory_id=obstory_id,
                                         key="altitude_gps",
                                         value=altitude,
                                         metadata_time=time.time(),
                                         time_created=time.time(),
                                         user_created=settings['pigazingUser'])

        # Fetch updated observatory status
        obstory_status = db.get_obstory_status(obstory_id=obstory_id)

        # Close database handle
        db.commit()
        db.close_db()
        del db

        # Decide whether we should observe, or do some day-time maintenance tasks
        logging.info("Observation controller considering what to do next.")

        time_now = time.time()

        # How far below the horizon do we require the Sun to be before we start observing?
        angle_below_horizon = settings['sunRequiredAngleBelowHorizon']

        sun_times_yesterday = sunset_times.sun_times(unix_time=time_now - 3600 * 24,
                                                     longitude=longitude,
                                                     latitude=latitude,
                                                     angle_below_horizon=angle_below_horizon)
        sun_times_today = sunset_times.sun_times(unix_time=time_now,
                                                 longitude=longitude,
                                                 latitude=latitude,
                                                 angle_below_horizon=angle_below_horizon)
        sun_times_tomorrow = sunset_times.sun_times(unix_time=time_now + 3600 * 24,
                                                    longitude=longitude,
                                                    latitude=latitude,
                                                    angle_below_horizon=angle_below_horizon)

        logging.info("Sunrise at {}".format(dcf_ast.date_string(sun_times_yesterday[0])))
        logging.info("Sunset  at {}".format(dcf_ast.date_string(sun_times_yesterday[2])))
        logging.info("Sunrise at {}".format(dcf_ast.date_string(sun_times_today[0])))
        logging.info("Sunset  at {}".format(dcf_ast.date_string(sun_times_today[2])))
        logging.info("Sunrise at {}".format(dcf_ast.date_string(sun_times_tomorrow[0])))
        logging.info("Sunset  at {}".format(dcf_ast.date_string(sun_times_tomorrow[2])))

        sun_margin = settings['sunMargin']

        # Calculate whether it's currently night time, and how long until the next sunrise
        is_night_time = False
        seconds_till_sunrise = 0

        # Test whether it is night time is we are between yesterday's sunset and today's sunrise
        if (time_now > sun_times_yesterday[2] + sun_margin) and (time_now < sun_times_today[0] - sun_margin):
            logging.info("""
It is night time. We are between yesterday's sunset and today's sunrise.
""".strip())
            is_night_time = True
            seconds_till_sunrise = sun_times_today[0] - time_now

        # Test whether it is between yesterday's sunset and today's sunrise
        elif (time_now > sun_times_yesterday[2]) and (time_now < sun_times_today[0]):
            next_observing_time = sun_times_yesterday[2] + sun_margin
            next_observing_wait = next_observing_time - time_now
            if next_observing_wait > 0:
                logging.info("""
We are between yesterday's sunset and today's sunrise, but sun has recently set. \
Waiting {:.0f} seconds (until {}) to start observing.
""".format(next_observing_wait, dcf_ast.date_string(next_observing_time)).strip())
                time.sleep(next_observing_wait + 2)
                continue

        # Test whether it is night time, since we are between today's sunrise and tomorrow's sunset
        elif (time_now > sun_times_today[2] + sun_margin) and (time_now < sun_times_tomorrow[0] - sun_margin):
            logging.info("""
It is night time. We are between today's sunset and tomorrow's sunrise.
""".strip())
            is_night_time = True
            seconds_till_sunrise = sun_times_tomorrow[0] - time_now

        # Test whether we between today's sunset and tomorrow's sunrise
        elif (time_now > sun_times_today[2]) and (time_now < sun_times_tomorrow[0]):
            next_observing_time = sun_times_today[2] + sun_margin
            next_observing_wait = next_observing_time - time_now
            if next_observing_time > 0:
                logging.info("""
We are between today's sunset and tomorrow's sunrise, but sun has recently set. \
Waiting {:.0f} seconds (until {}) to start observing.
""".format(next_observing_wait, dcf_ast.date_string(next_observing_time)).strip())
                time.sleep(next_observing_wait + 2)
                continue

        # Calculate time until the next sunset
        seconds_till_sunset = sun_times_yesterday[2] - time_now
        if seconds_till_sunset < -sun_margin:
            seconds_till_sunset = sun_times_today[2] - time_now
        if seconds_till_sunset < -sun_margin:
            seconds_till_sunset = sun_times_tomorrow[2] - time_now

        # If sunset was well in the past, and sunrise is well in the future, we should observe!
        minimum_time_worth_observing = 600
        if is_night_time and (seconds_till_sunrise > (sun_margin + minimum_time_worth_observing)):

            # Calculate how long to observe for
            observing_duration = seconds_till_sunrise - sun_margin

            # Do not record too much video in one file, as otherwise the file will be big
            if not settings['realTime']:
                observing_duration = min(observing_duration, settings['videoMaxRecordTime'])

            # Start observing run
            t_stop = time_now + observing_duration
            logging.info("""
Starting observing run until {} (running for {:.0f} seconds).
""".format(dcf_ast.date_string(t_stop), observing_duration).strip())

            # Flick the relay to turn the camera on
            relay_control.camera_on()
            time.sleep(2)
            logging.info("Camera has been turned on.")

            # Observe! We use different binaries depending whether we're using a webcam-like camera,
            # or a DSLR connected via gphoto2
            time_key = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')

            # Work out which C binary we're using to do observing
            if settings['realTime']:
                output_argument = ""
                if obstory_status["camera_type"] == "gphoto2":
                    binary = "realtimeObserve_dslr"
                else:
                    binary = "realtimeObserve"
            else:
                output_argument = """ --output \"{}/rawvideo/{}_{}\" """.format(settings['dataPath'],
                                                                                time_key, obstory_id)
                if settings['i_am_a_rpi']:
                    binary = "recordH264_openmax"
                else:
                    binary = "recordH264_libav"

            binary_full_path = "{path}{debug}/{binary}".format(path=settings['binaryPath'],
                                                               debug="/debug" if settings['debug'] else "",
                                                               binary=binary
                                                               )
            cmd = """
timeout {timeout} \
{binary} --utc-stop {utc_stop:.1f} \
         --obsid \"{obsid}\" \
         --device \"{device}\" \
         --fps {fps} \
         --width {width:d} \
         --height {height:d} \
         --mask \"{mask_file}\" \
         --latitude {latitude} \
         --longitude {longitude} \
         --flag-gps {flag_gps} \
         --flag-upside-down {upside_down} \
         {output_argument}
""".format(
                timeout=float(observing_duration + 300),
                binary=binary_full_path,
                utc_stop=float(t_stop),
                obsid=obstory_id,
                device=settings['videoDev'],
                width=int(obstory_status['camera_width']),
                height=int(obstory_status['camera_height']),
                fps=float(obstory_status['camera_fps']),
                mask_file=mask_file,
                latitude=float(latitude),
                longitude=float(longitude),
                flag_gps=int(flag_gps),
                upside_down=int(obstory_status['camera_upside_down']),
                output_argument=output_argument
            ).strip()

            logging.info("Running command: {}".format(cmd))
            os.system(cmd)

            # Flick the relay to turn the camera off
            relay_control.camera_off()
            time.sleep(2)
            logging.info("Camera has been turned off.")

            # Snooze for up to 10 minutes; we may rerun daytime tasks in a while if they ended prematurely
            if time.time() < t_stop:
                snooze_duration = float(min(t_stop - time.time(), 600))
                logging.info("Snoozing for {:.0f} seconds".format(snooze_duration))
                time.sleep(snooze_duration)

            continue

        # Estimate roughly when we're next going to be able to observe (i.e. shortly after sunset)
        next_observing_wait = seconds_till_sunset + sun_margin

        # If we've got more than an hour, it's worth doing some day time tasks
        # Do daytime tasks on a RPi only if we are doing real-time observation
        if (next_observing_wait > 3600) and (settings['realTime'] or not settings['i_am_a_rpi']):
            t_stop = time_now + next_observing_wait
            logging.info("""
Starting daytime tasks until {} (running for {:.0f} seconds).
""".format(dcf_ast.date_string(t_stop), next_observing_wait).strip())
            os.system("cd {} ; ./daytimeTasks.py --stop-by {}".format(settings['pythonPath'], t_stop))

            # Snooze for up to 10 minutes; we may rerun daytime tasks in a while if they ended prematurely
            if time.time() < t_stop:
                snooze_duration = float(min(t_stop - time.time(), 600))
                logging.info("Snoozing for {:.0f} seconds".format(snooze_duration))
                time.sleep(snooze_duration)

        else:
            if next_observing_wait < 0:
                next_observing_wait = 0
            next_observing_wait += 30
            t_stop = time_now + next_observing_wait
            logging.info("""
Not time to start observing yet, so sleeping until {} ({:.0f} seconds away).
""".format(dcf_ast.date_string(t_stop), next_observing_wait).strip())
            time.sleep(next_observing_wait)

        # Little snooze to prevent spinning around the loop
        snooze_duration = float(10)
        logging.info("Snoozing for {:.0f} seconds".format(snooze_duration))
        time.sleep(snooze_duration)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='[%(asctime)s] %(levelname)s:%(filename)s:%(message)s',
                        datefmt='%d/%m/%Y %H:%M:%S',
                        handlers=[
                            logging.FileHandler(os.path.join(settings['pythonPath'], "../datadir/pigazing.log")),
                            logging.StreamHandler()
                        ])
    logger = logging.getLogger(__name__)
    logger.info(__doc__.strip())

    observing_loop()
