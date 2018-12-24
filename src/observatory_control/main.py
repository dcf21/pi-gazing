#!../../virtualenv/bin/python3
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
import time
import datetime
import subprocess

import pigazing_db

from pigazing_helpers import dcf_ast
from mod_log import log_txt, get_utc, get_utc_offset, set_utc_offset
from pigazing_helpers import settings_read
import installation_info
import mod_hardwareProps

if settings_read.settings['i_am_a_rpi']:
    import mod_relay

obstory_id = installation_info.local_conf['observatoryId']

db = pigazing_db.MeteorDatabase(settings_read.settings['dbFilestore'])
hw = mod_hardwareProps.HardwareProps(os.path.join(settings_read.settings['pythonPath'], "..", "cameraProperties"))

logger.info("Camera controller launched")

# Make sure we have created the directory structure where observations live
os.system("mkdir -p %s/rawvideo" % settings_read.settings['dataPath'])


# Spawn a separate process and run <gpsFix.py>. If we have a USB GPS dongle attached, this may tell us the time
# and our location. If it does, return this, otherwise return None
def get_gps_fix():
    logger.info("Waiting for GPS link")

    # Run gpsFix.py, which returns JSON output to stdout
    cmd_ = os.path.join(settings_read.settings['pythonPath'], "gpsFix.py")
    gps_process = subprocess.Popen(cmd_, shell=True, stdout=subprocess.PIPE)
    gps_fix_json = gps_process.stdout.read()
    try:
        gps_result = json.loads(gps_fix_json)
    except ValueError:
        logger.info("Could not read valid JSON response from gpsFix.py")
        gps_result = False

    # If true, we get a structure with fields "offset", "latitude" and "longitude"
    if isinstance(gps_result, dict):
        t_offset = gps_result['offset']
        gps_latitude = gps_result['latitude']
        gps_longitude = gps_result['longitude']
        gps_altitude = gps_result['altitude']
        logger.info("GPS link achieved")
        logger.info("Longitude = %.6f ; Latitude = %.6f ; Altitude = %.6f ; Clock offset: %.2f sec behind." %
                (gps_longitude, gps_latitude, gps_altitude, t_offset))
        set_utc_offset(t_offset)

        # Use the time shell command to update the system clock (required root access)
        logger.info("Trying to update system clock")
        utc_now = get_utc()
        os.system("date -s @%d" % utc_now)

        # Because the above may fail if we don't have root access, as a fallback we recalculate the clock offset
        t_offset = utc_now - time.time()
        set_utc_offset(t_offset)
        logger.info("Revised clock offset after trying to set the system clock: %.2f sec behind." % t_offset)

        return {'latitude': gps_latitude, 'longitude': gps_longitude, 'altitude': gps_altitude}

    # If false, we didn't manage to establish a GPS link
    else:
        logger.info("Gave up waiting for a GPS link")
        return None


# Fetch observatory status, e.g. location, etc
time_now = get_utc()
logger.info("Fetching observatory status")
latitude = installation_info.local_conf['latitude']
longitude = installation_info.local_conf['longitude']
altitude = 0
latest_position_update = 0
flag_gps = 0
obstory_status = None

# If this observatory doesn't exist in the database, create it now with information from installation_info
if not db.has_obstory_id(obstory_id):
    logger.info("Observatory '%s' is not set up. Using default settings." % obstory_id)
    db.register_obstory(obstory_id=installation_info.local_conf['observatoryId'],
                        obstory_name=installation_info.local_conf['observatoryName'],
                        latitude=latitude,
                        longitude=longitude)
    obstory_name = installation_info.local_conf['observatoryName']
    db.register_obstory_metadata(obstory_name=obstory_name,
                                 key="latitude",
                                 value=latitude,
                                 metadata_time=get_utc(),
                                 time_created=get_utc(),
                                 user_created=settings_read.settings['pigazingUser'])
    db.register_obstory_metadata(obstory_name=obstory_name,
                                 key="longitude",
                                 value=longitude,
                                 metadata_time=get_utc(),
                                 time_created=get_utc(),
                                 user_created=settings_read.settings['pigazingUser'])
    db.register_obstory_metadata(obstory_name=obstory_name,
                                 key="altitude",
                                 value=altitude,
                                 metadata_time=get_utc(),
                                 time_created=get_utc(),
                                 user_created=settings_read.settings['pigazingUser'])
    db.register_obstory_metadata(obstory_name=obstory_name,
                                 key="location_source",
                                 value="manual",
                                 metadata_time=get_utc(),
                                 time_created=get_utc(),
                                 user_created=settings_read.settings['pigazingUser'])
else:
    obstory_name = db.get_obstory_from_id(obstory_id)['name']
    obstory_status = db.get_obstory_status(obstory_name=obstory_name)

# If we don't have complete metadata regarding camera / lens, ensure we have it now
if ((not isinstance(obstory_status, dict)) or
        ('camera' not in obstory_status) or
        ('camera_width' not in obstory_status) or
        ('camera_height' not in obstory_status) or
        ('camera_fps' not in obstory_status) or
        ('camera_upside_down' not in obstory_status) or
        ('camera_type' not in obstory_status)):
    logger.info("No camera information found for '%s'. Using a default." % obstory_id)
    hw.update_camera(db=db, obstory_id=obstory_name, utc=0, name=installation_info.local_conf['defaultCamera'])

if ((not isinstance(obstory_status, dict)) or
        ('lens' not in obstory_status) or
        ('lens_fov' not in obstory_status) or
        ('lens_barrel_a' not in obstory_status) or
        ('lens_barrel_b' not in obstory_status) or
        ('lens_barrel_c' not in obstory_status)):
    logger.info("No lens information found for '%s'. Using a default." % obstory_id)
    hw.update_lens(db=db, obstory_id=obstory_name, utc=0, name=installation_info.local_conf['defaultLens'])

obstory_status = db.get_obstory_status(obstory_name=obstory_name)

# Get most recent estimate of observatory location
if 'latitude' in obstory_status:
    latitude = obstory_status['latitude']
if 'longitude' in obstory_status:
    longitude = obstory_status['longitude']
if 'altitude' in obstory_status:
    altitude = obstory_status['altitude']

# Record the software version being used
db.register_obstory_metadata(obstory_name=obstory_name,
                             key="softwareVersion",
                             value=settings_read.settings['softwareVersion'],
                             metadata_time=get_utc(),
                             time_created=get_utc(),
                             user_created=settings_read.settings['pigazingUser'])

# Create clipping region mask file
logger.info("Creating clipping region mask")
if "clippingRegion" not in obstory_status:
    db.register_obstory_metadata(obstory_name=obstory_name,
                                 key="clippingRegion",
                                 value="[[]]",
                                 metadata_time=0,
                                 time_created=get_utc(),
                                 user_created=settings_read.settings['pigazingUser'])
obstory_status = db.get_obstory_status(obstory_name=obstory_name)

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
    db = pigazing_db.MeteorDatabase(settings_read.settings['dbFilestore'])

    # Get a GPS fix on the current time and our location
    gps_fix = get_gps_fix()
    if gps_fix:
        latitude = gps_fix['latitude']
        longitude = gps_fix['longitude']
        altitude = gps_fix['altitude']
        flag_gps = 1

        # If we've not stored a GPS fix in the database within the past hour, do so now
        if get_utc() > (latest_position_update + 3600):
            latest_position_update = get_utc()
            db.register_obstory_metadata(obstory_name=obstory_name, key="latitude", value=latitude,
                                         metadata_time=get_utc(), time_created=get_utc(),
                                         user_created=settings_read.settings['pigazingUser'])
            db.register_obstory_metadata(obstory_name=obstory_name, key="longitude", value=longitude,
                                         metadata_time=get_utc(), time_created=get_utc(),
                                         user_created=settings_read.settings['pigazingUser'])
            db.register_obstory_metadata(obstory_name=obstory_name, key="altitude", value=altitude,
                                         metadata_time=get_utc(), time_created=get_utc(),
                                         user_created=settings_read.settings['pigazingUser'])
            db.register_obstory_metadata(obstory_name=obstory_name, key="location_source", value="gps",
                                         metadata_time=get_utc(), time_created=get_utc(),
                                         user_created=settings_read.settings['pigazingUser'])
            db.commit()

    # If we have no location metadata, store a manual positional fix in the database
    obstory_status = db.get_obstory_status(obstory_name=obstory_name)
    if ('latitude' not in obstory_status) or ('longitude' not in obstory_status):
        db.register_obstory_metadata(obstory_name=obstory_name, key="latitude", value=latitude,
                                     metadata_time=0, time_created=get_utc(),
                                     user_created=settings_read.settings['pigazingUser'])
        db.register_obstory_metadata(obstory_name=obstory_name, key="longitude", value=longitude,
                                     metadata_time=0, time_created=get_utc(),
                                     user_created=settings_read.settings['pigazingUser'])
        db.register_obstory_metadata(obstory_name=obstory_name, key="altitude", value=altitude,
                                     metadata_time=0, time_created=get_utc(),
                                     user_created=settings_read.settings['pigazingUser'])
        db.register_obstory_metadata(obstory_name=obstory_name, key="location_source", value="manual",
                                     metadata_time=0, time_created=get_utc(),
                                     user_created=settings_read.settings['pigazingUser'])
    db.commit()
    obstory_status = db.get_obstory_status(obstory_name=obstory_name)

    # Decide whether we should observe, or do some day time jobs
    logger.info("Camera controller considering what to do next.")
    time_now = get_utc()
    sun_times_yesterday = dcf_ast.sun_times(unix_time=time_now - 3600 * 24, longitude=longitude, latitude=latitude)
    sun_times_today = dcf_ast.sun_times(unix_time=time_now, longitude=longitude, latitude=latitude)
    sun_times_tomorrow = dcf_ast.sun_times(unix_time=time_now + 3600 * 24, longitude=longitude, latitude=latitude)
    logger.info("Sunrise at %s" % dcf_ast.date_string(sun_times_yesterday[0]))
    logger.info("Sunset  at %s" % dcf_ast.date_string(sun_times_yesterday[2]))
    logger.info("Sunrise at %s" % dcf_ast.date_string(sun_times_today[0]))
    logger.info("Sunset  at %s" % dcf_ast.date_string(sun_times_today[2]))
    logger.info("Sunrise at %s" % dcf_ast.date_string(sun_times_tomorrow[0]))
    logger.info("Sunset  at %s" % dcf_ast.date_string(sun_times_tomorrow[2]))

    sun_margin = settings_read.settings['sunMargin']

    # Calculate whether it's currently night time, and how long until the next sunrise
    is_night_time = False
    seconds_till_sunrise = 0
    # It is night time is we are between yesterday's sunset and today's sunrise
    if (time_now > sun_times_yesterday[2] + sun_margin) and (time_now < sun_times_today[0] - sun_margin):
        logger.info("It is night time. We are between yesterday's sunset and today's sunrise.")
        is_night_time = True
        seconds_till_sunrise = sun_times_today[0] - time_now
    elif (time_now > sun_times_yesterday[2]) and (time_now < sun_times_today[0]):
        next_observing_time = sun_times_yesterday[2] + sun_margin - time_now
        if next_observing_time > 0:
            logger.info("We are between yesterday's sunset and today's sunrise, but sun has recently set. "
                    "Waiting %d seconds to start observing." % next_observing_time)
            time.sleep(next_observing_time + 2)
            continue

    # It is also night time if we are between today's sunrise and tomorrow's sunset
    elif (time_now > sun_times_today[2] + sun_margin) and (time_now < sun_times_tomorrow[0] - sun_margin):
        logger.info("It is night time. We are between today's sunset and tomorrow's sunrise.")
        is_night_time = True
        seconds_till_sunrise = sun_times_tomorrow[0] - time_now
    elif (time_now > sun_times_today[2]) and (time_now < sun_times_tomorrow[0]):
        next_observing_time = sun_times_today[2] + sun_margin - time_now
        if next_observing_time > 0:
            logger.info("We are between today's sunset and yesterday's sunrise, but sun has recently set. "
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
        if settings_read.settings['realTime']:
            t_stop = time_now + observing_duration
            logger.info("Starting observing run until %s (running for %d seconds)." % (dcf_ast.date_string(t_stop),
                                                                                   observing_duration))

            # Flick the relay to turn the camera on
            if settings_read.settings['i_am_a_rpi']:
                mod_relay.camera_on()
            time.sleep(10)
            logger.info("Camera has been turned on.")

            # Observe! We use different binaries depending whether we're using a webcam-like camera,
            # or a DSLR connected via gphoto2
            time_key = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')
            binary = "%s/debug/realtimeObserve" % settings_read.settings['binaryPath']
            if obstory_status["camera_type"] == "gphoto2":
                binary += "_dslr"
            cmd = "%s %.1f %.1f %.1f \"%s\" \"%s\" %d %d %s %s %s %s %d %d %s/rawvideo/%s_%s" % (
                binary, get_utc_offset(), time_now, t_stop, obstory_id, settings_read.settings['videoDev'],
                obstory_status['camera_width'], obstory_status['camera_height'],
                obstory_status['camera_fps'], mask_file, latitude, longitude, flag_gps,
                obstory_status['camera_upside_down'], settings_read.settings['dataPath'], time_key,
                obstory_id)
            logger.info("Running command: %s" % cmd)
            os.system(cmd)

            # Flick the relay to turn the camera off
            if settings_read.settings['i_am_a_rpi']:
                mod_relay.camera_off()
            logger.info("Camera has been turned off.")
            time.sleep(10)
            continue

        # We've been asked to record raw video files which we'll analyse in the morning
        else:

            # Calculate how long to observe for
            observing_duration = seconds_till_sunrise - sun_margin

            # Do not record too much video in one file, as otherwise the file will be big
            observing_duration = min(observing_duration, settings_read.settings['videoMaxRecordTime'])

            t_stop = time_now + observing_duration
            logger.info("Starting video recording until %s (running for %d seconds)." % (dcf_ast.date_string(t_stop),
                                                                                     observing_duration))

            # Flick the relay to turn the camera on
            if settings_read.settings['i_am_a_rpi']:
                mod_relay.camera_on()
            time.sleep(10)
            logger.info("Camera has been turned on.")

            # Observe!
            time_key = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')
            cmd = ("timeout %d %s/debug/recordH264 %.1f %.1f %.1f \"%s\" \"%s\" %d %d %s %s %s %d %d %s/rawvideo/%s_%s"
                   % (
                       observing_duration + 30, settings_read.settings['binaryPath'], get_utc_offset(), time_now, t_stop,
                       obstory_id, settings_read.settings['videoDev'],
                       obstory_status['camera_width'], obstory_status['camera_height'],
                       obstory_status['camera_fps'], latitude, longitude, flag_gps,
                       obstory_status['camera_upside_down'], settings_read.settings['dataPath'], time_key, obstory_id))
            # Use timeout here, because sometime the RPi's openmax encoder hangs...
            logger.info("Running command: %s" % cmd)
            os.system(cmd)

            # Flick the relay to turn the camera off
            if settings_read.settings['i_am_a_rpi']:
                mod_relay.camera_off()
            logger.info("Camera has been turned off.")
            time.sleep(10)
            continue

    # Estimate roughly when we're next going to be able to observe (i.e. shortly after sunset)
    next_observing_time = seconds_till_sunset + sun_margin

    # If we've got more than an hour, it's worth doing some day time tasks
    # Do daytimejobs on a RPi only if we are doing real-time observation
    if (next_observing_time > 3600) and (settings_read.settings['realTime'] or not settings_read.settings['i_am_a_rpi']):
        t_stop = time_now + next_observing_time
        logger.info("Starting daytime jobs until %s (running for %d seconds)." % (dcf_ast.date_string(t_stop),
                                                                              next_observing_time))
        time.sleep(300)
        logger.info("Finished snoozing.")
        os.system("cd %s ; ./daytimeJobs.py %d %d" % (settings_read.settings['pythonPath'], get_utc_offset(), t_stop))
    else:
        if next_observing_time < 0:
            next_observing_time = 0
        next_observing_time += 30
        logger.info("Not quite time to start observing yet, so let's sleep for %d seconds." % next_observing_time)
        time.sleep(next_observing_time)
    time.sleep(10)
