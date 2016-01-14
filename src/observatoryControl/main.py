#!../../virtual-env/bin/python
# main.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import os
import json
import time
import subprocess

import meteorpi_db
import meteorpi_model as mp

import mod_astro
from mod_log import log_txt, get_utc, get_utc_offset, set_utc_offset
import mod_settings
import installation_info
import mod_hardwareProps

if mod_settings.settings['i_am_a_rpi']:
    import mod_relay

obstory_name = installation_info.local_conf['observatoryName']

db = meteorpi_db.MeteorDatabase(mod_settings.settings['dbFilestore'])
hw = mod_hardwareProps.HardwareProps(os.path.join(mod_settings.settings['pythonPath'], "..", "sensorProperties"))

log_txt("Camera controller launched")

os.system("mkdir -p %s/rawvideo" % mod_settings.settings['dataPath'])

def get_gps_fix():
    log_txt("Waiting for GPS link")
    os.system("killall gpsd ; gpsd /dev/ttyUSB0 -F /var/run/gpsd.sock")
    gps_process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    gps_fix_json = gps_process.stdout.read()
    gps_fix = json.loads(gps_fix_json)
    if gps_fix:
        t_offset = gps_fix['offset']
        latitude = gps_fix['latitude']
        longitude = gps_fix['longitude']
        log_txt("GPS link achieved")
        log_txt("Longitude = %.6f ; Latitude = %.6f ; Clock offset: %.2f sec behind." % (longitude, latitude, t_offset))
        set_utc_offset(t_offset)
        log_txt("Trying to update system clock")
        time_now = get_utc()
        os.system("date -s @%d" % time_now)
        t_offset = time.time() - time_now
        log_txt("Revised clock offset after trying to set the system clock: %.2f sec behind." % t_offset)
        set_utc_offset(t_offset)
    else:
        log_txt("Gave up waiting for a GPS link")


# Update camera status with GPS position
time_now = get_utc()
log_txt("Fetching camera status")
cameraStatus = db.get_camera_status(time=time_now, camera_id=obstory_name)

if not cameraStatus:
    log_txt("No camera status found for id '%s': using a default" % obstory_name)
    cameraStatus = mp.CameraStatus("VF-DCD-AI-3.5-18-C-2MP", "watec_902h2_ultimate",
                                   "https://meteorpi.cambridgesciencecentre.org", obstory_name,
                                   mp.Orientation(0, 0, 360, 0, 0), mp.Location(latitude, longitude, (flagGPS != 0)),
                                   obstory_name)

log_txt("Updating camera status with new position")
cameraStatus.location = mp.Location(latitude, longitude, (flagGPS != 0))
log_txt("Storing camera status")
db.update_camera_status(cameraStatus, time=time_now, camera_id=obstory_name)

# Create clipping region mask file
log_txt("Creating clipping region mask")
maskFile = "/tmp/triggermask_%d.txt" % os.getpid()
open(maskFile, "w").write(
    "\n\n".join(["\n".join(["%(x)d %(y)d" % p for p in pointList]) for pointList in cameraStatus.regions]))

# Start main observing loop
while True:
    log_txt("Camera controller considering what to do next.")
    time_now = get_utc()
    sun_times = mod_astro.sun_times(time_now, longitude, latitude)
    seconds_till_sunrise = sun_times[0] - time_now
    seconds_till_sunset = sun_times[2] - time_now
    sun_margin = mod_settings.settings['sunMargin']
    sensorData = mod_hardwareProps.fetchSensorData(db, hw, obstory_name, time_now)

    if (seconds_till_sunset < -sun_margin) or (seconds_till_sunrise > sun_margin):
        if seconds_till_sunrise < 0:
            seconds_till_sunrise += 3600 * 24 - 300
        seconds_till_sunrise -= sun_margin
        if seconds_till_sunrise > 600:
            if mod_settings.settings['realTime']:
                t_stop = time_now + seconds_till_sunrise
                log_txt("Starting observing run until %s (running for %d seconds)." % (
                    datetime.datetime.fromtimestamp(t_stop).strftime('%Y-%m-%d %H:%M:%S'), seconds_till_sunrise))
                if mod_settings.settings['i_am_a_rpi']:
                    mod_relay.camera_on()
                time.sleep(10)
                log_txt("Camera has been turned on.")
                time_key = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')
                binary = "%s/debug/realtimeObserve" % mod_settings.settings['binaryPath']
                if sensorData.cameraType == "gphoto2":
                    binary += "_dslr"
                cmd = "%s %.1f %.1f %.1f \"%s\" \"%s\" %d %d %s %s %s %s %d %d %s/rawvideo/%s_%s" % (
                    binary, get_utc_offset(), time_now, t_stop, obstory_name, VIDEO_DEV, sensorData.width, sensorData.height,
                    sensorData.fps, maskFile, latitude, longitude, flagGPS, sensorData.upsideDown, DATA_PATH, time_key,
                    obstory_name)
                log_txt("Running command: %s" % cmd)
                os.system(cmd)
                if mod_settings.settings['i_am_a_rpi']:
                    mod_relay.camera_off()
                log_txt("Camera has been turned off.")
                time.sleep(10)
                continue
            else:
                # Do not record more than an hour of video in one file
                if (seconds_till_sunrise > mod_settings.settings['videoMaxRecordTime']):
                    seconds_till_sunrise = mod_settings.settings['videoMaxRecordTime']

                t_stop = time_now + seconds_till_sunrise
                log_txt("Starting video recording until %s (running for %d seconds)." % (
                    datetime.datetime.fromtimestamp(t_stop).strftime('%Y-%m-%d %H:%M:%S'), seconds_till_sunrise))
                if mod_settings.settings['i_am_a_rpi']:
                    mod_relay.camera_on()
                time.sleep(10)
                log_txt("Camera has been turned on.")
                time_key = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')
                cmd = "timeout %d %s/debug/recordH264 %.1f %.1f %.1f \"%s\" \"%s\" %d %d %s %s %s %d %d %s/rawvideo/%s_%s" % (
                    seconds_till_sunrise + 30, mod_settings.settings['binaryPath'], get_utc_offset(), time_now, t_stop, obstory_name, VIDEO_DEV,
                    sensorData.width, sensorData.height, sensorData.fps, latitude, longitude, flagGPS,
                    sensorData.upsideDown, mod_settings.settings['dataPath'], time_key, obstory_name)
                # Use timeout here, because sometime the RPi's openmax encoder hangs...
                log_txt("Running command: %s" % cmd)
                os.system(cmd)
                if mod_settings.settings['i_am_a_rpi']:
                    mod_relay.camera_off()
                log_txt("Camera has been turned off.")
                time.sleep(10)
                continue

    next_observing_time = seconds_till_sunset + sun_margin
    if next_observing_time < 0:
        next_observing_time += 3600 * 24 - 300
    # Do daytimejobs on a RPi only if we are doing real-time observation
    if (next_observing_time > 3600) and (mod_settings.settings['realTime'] or not mod_settings.settings['i_am_a_rpi']):
        t_stop = time_now + next_observing_time
        time.sleep(300)
        log_txt("Starting daytime jobs until %s (running for %d seconds)." % (
            datetime.datetime.fromtimestamp(t_stop).strftime('%Y-%m-%d %H:%M:%S'), next_observing_time))
        os.system("cd %s ; ./daytimeJobs.py %d %d" % (mod_settings.settings['pythonPath'], get_utc_offset(), t_stop))
    else:
        log_txt("Not quite time to start observing yet, so let's sleep for %d seconds." % next_observing_time)
        time.sleep(next_observing_time)
    time.sleep(10)
