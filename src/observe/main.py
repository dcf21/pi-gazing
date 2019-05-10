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

import os
import json
import logging
import time
import datetime
import subprocess

from pigazing_helpers import dcf_ast, sunset_times, relay_control, hardware_properties
from pigazing_helpers.obsarchive import obsarchive_model, obsarchive_db
from pigazing_helpers.settings_read import settings, installation_info


def observing_loop():
    obstory_id = installation_info['observatoryId']

    db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                           db_host=installation_info['mysqlHost'],
                                           db_user=installation_info['mysqlUser'],
                                           db_password=installation_info['mysqlPassword'],
                                           db_name=installation_info['mysqlDatabase'],
                                           obstory_id=installation_info['observatoryId'])

    hw = hardware_properties.HardwareProps(path=os.path.join(settings['pythonPath'], "..", "cameraProperties"))
    
    logging.info("Camera controller launched")
    
    # Make sure we have created the directory structure where observations live
    os.system("mkdir -p {}/rawvideo".format(settings['dataPath']))
    
    # Spawn a separate process and run <gpsFix.py>. If we have a USB GPS dongle attached, this may tell us the time
    # and our location. If it does, return this, otherwise return None
    def get_gps_fix():
        logging.info("Waiting for GPS link")
    
        # Run gpsFix.py, which returns JSON output to stdout
        cmd_ = os.path.join(settings['pythonPath'], "gpsFix.py")
        gps_process = subprocess.Popen(cmd_, shell=True, stdout=subprocess.PIPE)
        gps_fix_json = gps_process.stdout.read()
        try:
            gps_result = json.loads(gps_fix_json)
        except ValueError:
            logging.info("Could not read valid JSON response from gpsFix.py")
            gps_result = False
    
        # If true, we get a structure with fields "offset", "latitude" and "longitude"
        if isinstance(gps_result, dict):
            t_offset = gps_result['offset']
            gps_latitude = gps_result['latitude']
            gps_longitude = gps_result['longitude']
            gps_altitude = gps_result['altitude']
            logging.info("GPS link achieved")
            logging.info("Longitude = %.6f ; Latitude = %.6f ; Altitude = %.6f ; Clock offset: %.2f sec behind." %
                    (gps_longitude, gps_latitude, gps_altitude, t_offset))
    
            # Use the time shell command to update the system clock (required root access)
            logging.info("Trying to update system clock")
            utc_now = time.time()
            os.system("date -s @%d" % utc_now)
    
            # Because the above may fail if we don't have root access, as a fallback we recalculate the clock offset
            t_offset = utc_now - time.time()
            logging.info("Revised clock offset after trying to set the system clock: %.2f sec behind." % t_offset)
    
            return {'latitude': gps_latitude, 'longitude': gps_longitude, 'altitude': gps_altitude}
    
        # If false, we didn't manage to establish a GPS link
        else:
            logging.info("Gave up waiting for a GPS link")
            return None

    # Fetch observatory status, e.g. location, etc
    logging.info("Fetching observatory status")
    latitude = installation_info['latitude']
    longitude = installation_info['longitude']
    altitude = 0
    latest_position_update = 0
    flag_gps = 0
    obstory_status = None
    
    # If this observatory doesn't exist in the database, create it now with information from installation_info
    if not db.has_obstory_id(obstory_id):
        logging.info("Observatory '%s' is not set up. Using default settings." % obstory_id)
        db.register_obstory(obstory_id=installation_info['observatoryId'],
                            obstory_name=installation_info['observatoryName'],
                            latitude=latitude,
                            longitude=longitude,
                            owner=installation_info['owner'])
        db.register_obstory_metadata(obstory_id=obstory_id,
                                     key="latitude",
                                     value=latitude,
                                     metadata_time=time.time(),
                                     time_created=time.time(),
                                     user_created=settings['pigazingUser'])
        db.register_obstory_metadata(obstory_id=obstory_id,
                                     key="longitude",
                                     value=longitude,
                                     metadata_time=time.time(),
                                     time_created=time.time(),
                                     user_created=settings['pigazingUser'])
        db.register_obstory_metadata(obstory_id=obstory_id,
                                     key="altitude",
                                     value=altitude,
                                     metadata_time=time.time(),
                                     time_created=time.time(),
                                     user_created=settings['pigazingUser'])
        db.register_obstory_metadata(obstory_id=obstory_id,
                                     key="location_source",
                                     value="manual",
                                     metadata_time=time.time(),
                                     time_created=time.time(),
                                     user_created=settings['pigazingUser'])
    else:
        obstory_status = db.get_obstory_status(obstory_id=obstory_id)
    
    # If we don't have complete metadata regarding camera / lens, ensure we have it now
    if ((not isinstance(obstory_status, dict)) or
            ('camera' not in obstory_status) or
            ('camera_width' not in obstory_status) or
            ('camera_height' not in obstory_status) or
            ('camera_fps' not in obstory_status) or
            ('camera_upside_down' not in obstory_status) or
            ('camera_type' not in obstory_status)):
        logging.info("No camera information found for '%s'. Using a default." % obstory_id)
        hw.update_camera(db=db, obstory_id=obstory_id, utc=time.time(), name=installation_info['defaultCamera'])
    
    if ((not isinstance(obstory_status, dict)) or
            ('lens' not in obstory_status) or
            ('lens_fov' not in obstory_status) or
            ('lens_barrel_a' not in obstory_status) or
            ('lens_barrel_b' not in obstory_status) or
            ('lens_barrel_c' not in obstory_status)):
        logging.info("No lens information found for '%s'. Using a default." % obstory_id)
        hw.update_lens(db=db, obstory_id=obstory_id, utc=time.time(), name=installation_info['defaultLens'])
    
    obstory_status = db.get_obstory_status(obstory_id=obstory_id)
    
    # Get most recent estimate of observatory location
    if 'latitude' in obstory_status:
        latitude = obstory_status['latitude']
    if 'longitude' in obstory_status:
        longitude = obstory_status['longitude']
    if 'altitude' in obstory_status:
        altitude = obstory_status['altitude']
    
    # Record the software version being used
    db.register_obstory_metadata(obstory_id=obstory_id,
                                 key="softwareVersion",
                                 value=settings['softwareVersion'],
                                 metadata_time=time.time(),
                                 time_created=time.time(),
                                 user_created=settings['pigazingUser'])
    
    # Create clipping region mask file
    logging.info("Creating clipping region mask")
    if "clippingRegion" not in obstory_status:
        db.register_obstory_metadata(obstory_id=obstory_id,
                                     key="clippingRegion",
                                     value="[[]]",
                                     metadata_time=0,
                                     time_created=time.time(),
                                     user_created=settings['pigazingUser'])
    obstory_status = db.get_obstory_status(obstory_id=obstory_id)
    
    # Commit updates to the database
    db.commit()
    
    mask_file = "/tmp/triggermask_%d.txt" % os.getpid()
    open(mask_file, "w").write(
            "\n\n".join(
                    ["\n".join([("%d %d" % tuple(p)) for p in point_list])
                     for point_list in json.loads(obstory_status["clippingRegion"])]
            )
    )
    
    # Start main observing loop
    while True:
    
        # Get a new MySQL connection because old one may not be connected any longer
        del db
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
            if time.time() > (latest_position_update + 3600):
                latest_position_update = time.time()
                db.register_obstory_metadata(obstory_id=obstory_id, key="latitude", value=latitude,
                                             metadata_time=time.time(), time_created=time.time(),
                                             user_created=settings['pigazingUser'])
                db.register_obstory_metadata(obstory_id=obstory_id, key="longitude", value=longitude,
                                             metadata_time=time.time(), time_created=time.time(),
                                             user_created=settings['pigazingUser'])
                db.register_obstory_metadata(obstory_id=obstory_id, key="altitude", value=altitude,
                                             metadata_time=time.time(), time_created=time.time(),
                                             user_created=settings['pigazingUser'])
                db.register_obstory_metadata(obstory_id=obstory_id, key="location_source", value="gps",
                                             metadata_time=time.time(), time_created=time.time(),
                                             user_created=settings['pigazingUser'])
                db.commit()
    
        # If we have no location metadata, store a manual positional fix in the database
        obstory_status = db.get_obstory_status(obstory_id=obstory_id)
        if ('latitude' not in obstory_status) or ('longitude' not in obstory_status):
            db.register_obstory_metadata(obstory_id=obstory_id, key="latitude", value=latitude,
                                         metadata_time=0, time_created=time.time(),
                                         user_created=settings['pigazingUser'])
            db.register_obstory_metadata(obstory_id=obstory_id, key="longitude", value=longitude,
                                         metadata_time=0, time_created=time.time(),
                                         user_created=settings['pigazingUser'])
            db.register_obstory_metadata(obstory_id=obstory_id, key="altitude", value=altitude,
                                         metadata_time=0, time_created=time.time(),
                                         user_created=settings['pigazingUser'])
            db.register_obstory_metadata(obstory_id=obstory_id, key="location_source", value="manual",
                                         metadata_time=0, time_created=time.time(),
                                         user_created=settings['pigazingUser'])
        db.commit()
        obstory_status = db.get_obstory_status(obstory_id=obstory_id)
    
        # Decide whether we should observe, or do some day time jobs
        logging.info("Camera controller considering what to do next.")
        time_now = time.time()
        sun_times_yesterday = sunset_times.sun_times(unix_time=time_now - 3600 * 24,
                                                     longitude=longitude, latitude=latitude)
        sun_times_today = sunset_times.sun_times(unix_time=time_now,
                                                 longitude=longitude, latitude=latitude)
        sun_times_tomorrow = sunset_times.sun_times(unix_time=time_now + 3600 * 24,
                                                    longitude=longitude, latitude=latitude)

        logging.info("Sunrise at %s" % dcf_ast.date_string(sun_times_yesterday[0]))
        logging.info("Sunset  at %s" % dcf_ast.date_string(sun_times_yesterday[2]))
        logging.info("Sunrise at %s" % dcf_ast.date_string(sun_times_today[0]))
        logging.info("Sunset  at %s" % dcf_ast.date_string(sun_times_today[2]))
        logging.info("Sunrise at %s" % dcf_ast.date_string(sun_times_tomorrow[0]))
        logging.info("Sunset  at %s" % dcf_ast.date_string(sun_times_tomorrow[2]))
    
        sun_margin = settings['sunMargin']
    
        # Calculate whether it's currently night time, and how long until the next sunrise
        is_night_time = False
        seconds_till_sunrise = 0
        # It is night time is we are between yesterday's sunset and today's sunrise
        if (time_now > sun_times_yesterday[2] + sun_margin) and (time_now < sun_times_today[0] - sun_margin):
            logging.info("It is night time. We are between yesterday's sunset and today's sunrise.")
            is_night_time = True
            seconds_till_sunrise = sun_times_today[0] - time_now
        elif (time_now > sun_times_yesterday[2]) and (time_now < sun_times_today[0]):
            next_observing_time = sun_times_yesterday[2] + sun_margin - time_now
            if next_observing_time > 0:
                logging.info("We are between yesterday's sunset and today's sunrise, but sun has recently set. "
                        "Waiting %d seconds to start observing." % next_observing_time)
                time.sleep(next_observing_time + 2)
                continue
    
        # It is also night time if we are between today's sunrise and tomorrow's sunset
        elif (time_now > sun_times_today[2] + sun_margin) and (time_now < sun_times_tomorrow[0] - sun_margin):
            logging.info("It is night time. We are between today's sunset and tomorrow's sunrise.")
            is_night_time = True
            seconds_till_sunrise = sun_times_tomorrow[0] - time_now
        elif (time_now > sun_times_today[2]) and (time_now < sun_times_tomorrow[0]):
            next_observing_time = sun_times_today[2] + sun_margin - time_now
            if next_observing_time > 0:
                logging.info("We are between today's sunset and yesterday's sunrise, but sun has recently set. "
                        "Waiting %d seconds to start observing." % next_observing_time)
                time.sleep(next_observing_time + 2)
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
    
            # Depending on settings, we either monitor video in real time, or we record raw video to analyse later
            if settings['realTime']:
                t_stop = time_now + observing_duration
                logging.info("Starting observing run until %s (running for %d seconds)." % (dcf_ast.date_string(t_stop),
                                                                                       observing_duration))
    
                # Flick the relay to turn the camera on
                if settings['i_am_a_rpi']:
                    relay_control.camera_on()
                time.sleep(10)
                logging.info("Camera has been turned on.")
    
                # Observe! We use different binaries depending whether we're using a webcam-like camera,
                # or a DSLR connected via gphoto2
                time_key = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')
                binary = "%s/debug/realtimeObserve" % settings['binaryPath']
                if obstory_status["camera_type"] == "gphoto2":
                    binary += "_dslr"
                cmd = "%s %.1f %.1f \"%s\" \"%s\" %d %d %s %s %s %s %d %d %s/rawvideo/%s_%s" % (
                    binary, time_now, t_stop, obstory_id, settings['videoDev'],
                    obstory_status['camera_width'], obstory_status['camera_height'],
                    obstory_status['camera_fps'], mask_file, latitude, longitude, flag_gps,
                    obstory_status['camera_upside_down'], settings['dataPath'], time_key,
                    obstory_id)
                logging.info("Running command: %s" % cmd)
                os.system(cmd)
    
                # Flick the relay to turn the camera off
                if settings['i_am_a_rpi']:
                    relay_control.camera_off()
                logging.info("Camera has been turned off.")
                time.sleep(10)
                continue
    
            # We've been asked to record raw video files which we'll analyse in the morning
            else:
    
                # Calculate how long to observe for
                observing_duration = seconds_till_sunrise - sun_margin
    
                # Do not record too much video in one file, as otherwise the file will be big
                observing_duration = min(observing_duration, settings['videoMaxRecordTime'])
    
                t_stop = time_now + observing_duration
                logging.info("Starting video recording until %s (running for %d seconds)." % (dcf_ast.date_string(t_stop),
                                                                                         observing_duration))
    
                # Flick the relay to turn the camera on
                if settings['i_am_a_rpi']:
                    relay_control.camera_on()
                time.sleep(10)
                logging.info("Camera has been turned on.")
    
                # Observe!
                time_key = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')
                cmd = ("timeout %d %s/debug/recordH264 %.1f %.1f \"%s\" \"%s\" %d %d %s %s %s %d %d %s/rawvideo/%s_%s"
                       % (
                           observing_duration + 30, settings['binaryPath'], time_now, t_stop,
                           obstory_id, settings['videoDev'],
                           obstory_status['camera_width'], obstory_status['camera_height'],
                           obstory_status['camera_fps'], latitude, longitude, flag_gps,
                           obstory_status['camera_upside_down'], settings['dataPath'], time_key, obstory_id))
                # Use timeout here, because sometime the RPi's openmax encoder hangs...
                logging.info("Running command: %s" % cmd)
                os.system(cmd)
    
                # Flick the relay to turn the camera off
                if settings['i_am_a_rpi']:
                    relay_control.camera_off()
                logging.info("Camera has been turned off.")
                time.sleep(10)
                continue
    
        # Estimate roughly when we're next going to be able to observe (i.e. shortly after sunset)
        next_observing_time = seconds_till_sunset + sun_margin
    
        # If we've got more than an hour, it's worth doing some day time tasks
        # Do daytimejobs on a RPi only if we are doing real-time observation
        if (next_observing_time > 3600) and (settings['realTime'] or not settings['i_am_a_rpi']):
            t_stop = time_now + next_observing_time
            logging.info("Starting daytime jobs until %s (running for %d seconds)." % (dcf_ast.date_string(t_stop),
                                                                                  next_observing_time))
            time.sleep(300)
            logging.info("Finished snoozing.")
            os.system("cd %s ; ./daytimeJobs.py %d" % (settings['pythonPath'], t_stop))
        else:
            if next_observing_time < 0:
                next_observing_time = 0
            next_observing_time += 30
            logging.info("Not quite time to start observing yet, so let's sleep for %d seconds." % next_observing_time)
            time.sleep(next_observing_time)
        time.sleep(10)


if __name__ == "__main__":
    observing_loop()
