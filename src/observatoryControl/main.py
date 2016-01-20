#!../../virtual-env/bin/python
# main.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import os
import json
import time
import datetime
import subprocess

import meteorpi_db

import mod_astro
from mod_log import log_txt, get_utc, get_utc_offset, set_utc_offset
import mod_settings
import installation_info
import mod_hardwareProps

if mod_settings.settings['i_am_a_rpi']:
    import mod_relay

obstory_id = installation_info.local_conf['observatoryId']

db = meteorpi_db.MeteorDatabase(mod_settings.settings['dbFilestore'])
hw = mod_hardwareProps.HardwareProps(os.path.join(mod_settings.settings['pythonPath'], "..", "sensorProperties"))

log_txt("Camera controller launched")

# Make sure we have created the directory structure where observations live
os.system("mkdir -p %s/rawvideo" % mod_settings.settings['dataPath'])


# Spawn a separate process and run <gpsFix.py>. If we have a USB GPS dongle attached, this may tell us the time
# and our location. If it does, return this, otherwise return None
def get_gps_fix():
    log_txt("Waiting for GPS link")

    # gpsd isn't very reliable. Restart it to be on the safe side. This requires root access.
    os.system("killall gpsd ; gpsd /dev/ttyUSB0 -F /var/run/gpsd.sock")

    # Run gpsFix.py, which returns JSON output to stdout
    cmd = os.path.join(mod_settings.settings['pythonPath'], "gpdFix.py")
    gps_process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    gps_fix_json = gps_process.stdout.read()
    gps_fix = json.loads(gps_fix_json)

    # If true, we get a structure with fields "offset", "latitude" and "longitude"
    if gps_fix:
        t_offset = gps_fix['offset']
        latitude = gps_fix['latitude']
        longitude = gps_fix['longitude']
        log_txt("GPS link achieved")
        log_txt("Longitude = %.6f ; Latitude = %.6f ; Clock offset: %.2f sec behind." % (longitude, latitude, t_offset))
        set_utc_offset(t_offset)

        # Use the time shell command to update the system clock (required root access)
        log_txt("Trying to update system clock")
        time_now = get_utc()
        os.system("date -s @%d" % time_now)

        # Because the above may fail if we don't have root access, as a fallback we recalculate the clock offset
        t_offset = time.time() - time_now
        log_txt("Revised clock offset after trying to set the system clock: %.2f sec behind." % t_offset)
        set_utc_offset(t_offset)

        return {'latitude': latitude, 'longitude': longitude}

    # If false, we didn't manage to establish a GPS link
    else:
        log_txt("Gave up waiting for a GPS link")
        return None


# Fetch observatory status, e.g. location, etc
time_now = get_utc()
log_txt("Fetching observatory status")
latitude = installation_info.local_conf['latitude']
longitude = installation_info.local_conf['longitude']
latest_position_update = 0
flag_gps = 0
obstory_status = None

# If this observatory doesn't exist in the database, create it now with information from installation_info
if not db.has_obstory_id(obstory_id):
    log_txt("Observatory '%s' is not set up. Using default settings." % obstory_id)
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
                                 user_created=mod_settings.settings['meteorpiUser'])
    db.register_obstory_metadata(obstory_name=obstory_name,
                                 key="longitude",
                                 value=longitude,
                                 metadata_time=get_utc(),
                                 time_created=get_utc(),
                                 user_created=mod_settings.settings['meteorpiUser'])
    db.register_obstory_metadata(obstory_name=obstory_name,
                                 key="location_source",
                                 value="manual",
                                 metadata_time=get_utc(),
                                 time_created=get_utc(),
                                 user_created=mod_settings.settings['meteorpiUser'])
else:
    obstory_name = db.get_obstory_from_id(obstory_id)['name']
    obstory_status = db.get_obstory_status(obstory_name=obstory_name)

# If we don't have any metadata, configure default lens and sensor now
if (obstory_status is None) or (not obstory_status):
    log_txt("No observatory status found for '%s'. Using a default." % obstory_id)
    hw.update_sensor(db=db, obstory_name=obstory_name, utc=time_now, name="watec_902h2_ultimate")
    hw.update_lens(db=db, obstory_name=obstory_name, utc=time_now, name="VF-DCD-AI-3.5-18-C-2MP")
obstory_status = db.get_obstory_status(obstory_name=obstory_name)

# Get most recent estimate of observatory location
if 'latitude' in obstory_status:
    latitude = obstory_status['latitude']
if 'longitude' in obstory_status:
    longitude = obstory_status['longitude']

# Record the software version being used
db.register_obstory_metadata(obstory_name=obstory_name,
                             key="softwareVersion",
                             value=mod_settings.settings['softwareVersion'],
                             metadata_time=get_utc(),
                             time_created=get_utc(),
                             user_created=mod_settings.settings['meteorpiUser'])

# Create clipping region mask file
log_txt("Creating clipping region mask")
if "clippingRegion" not in obstory_status:
    db.register_obstory_metadata(obstory_name=obstory_name,
                                 key="clippingRegion",
                                 value="[[]]",
                                 metadata_time=get_utc(),
                                 time_created=get_utc(),
                                 user_created=mod_settings.settings['meteorpiUser'])
obstory_status = db.get_obstory_status(obstory_name=obstory_name)

mask_file = "/tmp/triggermask_%d.txt" % os.getpid()
open(mask_file, "w").write(
        "\n\n".join(
                ["\n".join(["%(x)d %(y)d" % p for p in pointList])
                 for pointList in obstory_status["clippingRegion"]]
        )
)

# Start main observing loop
while True:

    # Get a GPS fix on the current time and our location
    gps_fix = get_gps_fix()
    if gps_fix:
        latitude = gps_fix['latitude']
        longitude = gps_fix['longitude']
        flag_gps = 1

        # If we've not stored a GPS fix in the database within the past hour, do so now
        if get_utc() > (latest_position_update + 3600):
            latest_position_update = get_utc()
            db.register_obstory_metadata(obstory_name=obstory_name, key="latitude", value=latitude,
                                         metadata_time=get_utc(), time_created=get_utc(),
                                         user_created=mod_settings.settings['meteorpiUser'])
            db.register_obstory_metadata(obstory_name=obstory_name, key="longitude", value=longitude,
                                         metadata_time=get_utc(), time_created=get_utc(),
                                         user_created=mod_settings.settings['meteorpiUser'])
            db.register_obstory_metadata(obstory_name=obstory_name, key="location_source", value="gps",
                                         metadata_time=get_utc(), time_created=get_utc(),
                                         user_created=mod_settings.settings['meteorpiUser'])

    # Decide whether we should observe, or do some day time jobs
    log_txt("Camera controller considering what to do next.")
    time_now = get_utc()
    sun_times = mod_astro.sun_times(time_now, longitude, latitude)
    seconds_till_sunrise = sun_times[0] - time_now
    seconds_till_sunset = sun_times[2] - time_now
    sun_margin = mod_settings.settings['sunMargin']

    # We may have been given the time for yesterday's sunrise. Assume tomorrow's will be exactly 24 hours later.
    if seconds_till_sunrise < 0:
        seconds_till_sunrise += 3600 * 24 - 300

    # If sunset was well in the past, and sunrise is well in the future, we should observe!
    minimum_time_worth_observing = 600
    if (seconds_till_sunset < -sun_margin) or (seconds_till_sunrise > (sun_margin + minimum_time_worth_observing)):

        # Calculate how long to observe for
        observing_duration = seconds_till_sunrise - sun_margin

        # Depending on settings, we either monitor video in real time, or we record raw video to analyse later
        if mod_settings.settings['realTime']:
            t_stop = time_now + observing_duration
            log_txt("Starting observing run until %s (running for %d seconds)." % (mod_astro.time_print(t_stop),
                                                                                   observing_duration))

            # Flick the relay to turn the camera on
            if mod_settings.settings['i_am_a_rpi']:
                mod_relay.camera_on()
            time.sleep(10)
            log_txt("Camera has been turned on.")

            # Observe! We use different binaries depending whether we're using a webcam-like camera,
            # or a DSLR connected via gphoto2
            time_key = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')
            binary = "%s/debug/realtimeObserve" % mod_settings.settings['binaryPath']
            if obstory_status["sensor_camera_type"] == "gphoto2":
                binary += "_dslr"
            cmd = "%s %.1f %.1f %.1f \"%s\" \"%s\" %d %d %s %s %s %s %d %d %s/rawvideo/%s_%s" % (
                binary, get_utc_offset(), time_now, t_stop, obstory_id, mod_settings.settings['videoDev'],
                obstory_status['sensor_width'], obstory_status['sensor_height'],
                obstory_status['sensor_fps'], mask_file, latitude, longitude, flag_gps,
                obstory_status['sensor_upside_down'], mod_settings.settings['dataPath'], time_key,
                obstory_id)
            log_txt("Running command: %s" % cmd)
            os.system(cmd)

            # Flick the relay to turn the camera off
            if mod_settings.settings['i_am_a_rpi']:
                mod_relay.camera_off()
            log_txt("Camera has been turned off.")
            time.sleep(10)
            continue

        # We've been asked to record raw video files which we'll analyse in the morning
        else:

            # Calculate how long to observe for
            observing_duration = seconds_till_sunrise - sun_margin

            # Do not record too much video in one file, as otherwise the file will be big
            observing_duration = min(observing_duration, mod_settings.settings['videoMaxRecordTime'])

            t_stop = time_now + observing_duration
            log_txt("Starting video recording until %s (running for %d seconds)." % (mod_astro.time_print(t_stop),
                                                                                     observing_duration))

            # Flick the relay to turn the camera on
            if mod_settings.settings['i_am_a_rpi']:
                mod_relay.camera_on()
            time.sleep(10)
            log_txt("Camera has been turned on.")

            # Observe!
            time_key = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')
            cmd = ("timeout %d %s/debug/recordH264 %.1f %.1f %.1f \"%s\" \"%s\" %d %d %s %s %s %d %d %s/rawvideo/%s_%s"
                   % (
                       observing_duration + 30, mod_settings.settings['binaryPath'], get_utc_offset(), time_now, t_stop,
                       obstory_id, mod_settings.settings['videoDev'],
                       obstory_status['sensor_width'], obstory_status['sensor_height'],
                       obstory_status['sensor_fps'], latitude, longitude, flag_gps,
                       obstory_status['sensor_upside_down'], mod_settings.settings['dataPath'], time_key, obstory_id))
            # Use timeout here, because sometime the RPi's openmax encoder hangs...
            log_txt("Running command: %s" % cmd)
            os.system(cmd)

            # Flick the relay to turn the camera off
            if mod_settings.settings['i_am_a_rpi']:
                mod_relay.camera_off()
            log_txt("Camera has been turned off.")
            time.sleep(10)
            continue

    # Estimate roughly when we're next going to be able to observe (i.e. shortly after sunset)
    next_observing_time = seconds_till_sunset + sun_margin
    if next_observing_time < 0:
        next_observing_time += 3600 * 24 - 300

    # If we've got more than an hour, it's worth doing some day time tasks
    # Do daytimejobs on a RPi only if we are doing real-time observation
    if (next_observing_time > 3600) and (mod_settings.settings['realTime'] or not mod_settings.settings['i_am_a_rpi']):
        t_stop = time_now + next_observing_time
        time.sleep(300)
        log_txt("Starting daytime jobs until %s (running for %d seconds)." % (mod_astro.time_print(t_stop),
                                                                              next_observing_time))
        os.system("cd %s ; ./daytimeJobs.py %d %d" % (mod_settings.settings['pythonPath'], get_utc_offset(), t_stop))
    else:
        log_txt("Not quite time to start observing yet, so let's sleep for %d seconds." % next_observing_time)
        time.sleep(next_observing_time)
    time.sleep(10)
