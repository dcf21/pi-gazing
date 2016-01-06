#!../../virtual-env/bin/python
# main.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import json
import subprocess

import meteorpi_db
import meteorpi_model as mp

import mod_astro
from mod_log import logTxt, getUTC, getUTCoffset, setUTCoffset
from mod_settings import *
from mod_time import *
import mod_hardwareProps

if I_AM_A_RPI:
    import mod_relay

db_handle = meteorpi_db.MeteorDatabase(DBFILESTORE)
hw_handle = mod_hardwareProps.hardwareProps(os.path.join(PYTHON_PATH, "..", "sensorProperties"))

logTxt("Camera controller launched")

os.system("mkdir -p %s/rawvideo" % DATA_PATH)

def get_gps_fix():
    logTxt("Waiting for GPS link")
    os.system("killall gpsd ; gpsd /dev/ttyUSB0 -F /var/run/gpsd.sock")
    gps_process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    gps_fix_json = gps_process.stdout.read()
    gps_fix = json.loads(gps_fix_json)
    if gps_fix:
        toffset = gps_fix['offset']
        latitude = gps_fix['latitude']
        longitude = gps_fix['longitude']
        logTxt("GPS link achieved")
        logTxt("Longitude = %.6f ; Latitude = %.6f ; Clock offset: %.2f sec behind." % (longitude, latitude, toffset))
        setUTCoffset(toffset)
        logTxt("Trying to update system clock")
        time_now = getUTC()
        os.system("date -s @%d" % time_now)
        toffset = time.time() - time_now
        logTxt("Revised clock offset after trying to set the system clock: %.2f sec behind." % toffset)
        setUTCoffset(toffset)
    else:
        logTxt("Gave up waiting for a GPS link")


# Update camera status with GPS position
timenow = UTC2datetime(getUTC())
logTxt("Fetching camera status")
cameraStatus = db_handle.get_camera_status(time=timenow, camera_id=CAMERA_ID)

if not cameraStatus:
    logTxt("No camera status found for id '%s': using a default" % CAMERA_ID)
    cameraStatus = mp.CameraStatus("VF-DCD-AI-3.5-18-C-2MP", "watec_902h2_ultimate",
                                   "https://meteorpi.cambridgesciencecentre.org", CAMERA_ID,
                                   mp.Orientation(0, 0, 360, 0, 0), mp.Location(latitude, longitude, (flagGPS != 0)),
                                   CAMERA_ID)

logTxt("Updating camera status with new position")
cameraStatus.location = mp.Location(latitude, longitude, (flagGPS != 0))
logTxt("Storing camera status")
db_handle.update_camera_status(cameraStatus, time=timenow, camera_id=CAMERA_ID)

# Create clipping region mask file
logTxt("Creating clipping region mask")
maskFile = "/tmp/triggermask_%d.txt" % os.getpid()
open(maskFile, "w").write(
    "\n\n".join(["\n".join(["%(x)d %(y)d" % p for p in pointList]) for pointList in cameraStatus.regions]))

# Start main observing loop
while True:
    logTxt("Camera controller considering what to do next.")
    timeNow = getUTC()
    sunTimes = mod_astro.sunTimes(timeNow, longitude, latitude)
    secondsTillSunrise = sunTimes[0] - timeNow
    secondsTillSunset = sunTimes[2] - timeNow
    sensorData = mod_hardwareProps.fetchSensorData(db_handle, hw_handle, CAMERA_ID, timeNow)

    if (secondsTillSunset < -sunMargin) or (secondsTillSunrise > sunMargin):
        if secondsTillSunrise < 0:
            secondsTillSunrise += 3600 * 24 - 300
        secondsTillSunrise -= sunMargin
        if secondsTillSunrise > 600:
            if REAL_TIME:
                tstop = timeNow + secondsTillSunrise
                logTxt("Starting observing run until %s (running for %d seconds)." % (
                    datetime.datetime.fromtimestamp(tstop).strftime('%Y-%m-%d %H:%M:%S'), secondsTillSunrise))
                if I_AM_A_RPI:
                    mod_relay.cameraOn()
                time.sleep(10)
                logTxt("Camera has been turned on.")
                timekey = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')
                binary = "%s/debug/realtimeObserve" % BINARY_PATH
                if sensorData.cameraType == "gphoto2":
                    binary += "_dslr"
                cmd = "%s %.1f %.1f %.1f \"%s\" \"%s\" %d %d %s %s %s %s %d %d %s/rawvideo/%s_%s" % (
                    binary, getUTCoffset(), timeNow, tstop, CAMERA_ID, VIDEO_DEV, sensorData.width, sensorData.height,
                    sensorData.fps, maskFile, latitude, longitude, flagGPS, sensorData.upsideDown, DATA_PATH, timekey,
                    CAMERA_ID)
                logTxt("Running command: %s" % cmd)
                os.system(cmd)
                if I_AM_A_RPI:
                    mod_relay.cameraOff()
                logTxt("Camera has been turned off.")
                time.sleep(10)
                continue
            else:
                if (secondsTillSunrise > VIDEO_MAXRECTIME):
                    secondsTillSunrise = VIDEO_MAXRECTIME  # Do not record more than an hour of video in one file
                tstop = timeNow + secondsTillSunrise
                logTxt("Starting video recording until %s (running for %d seconds)." % (
                    datetime.datetime.fromtimestamp(tstop).strftime('%Y-%m-%d %H:%M:%S'), secondsTillSunrise))
                if I_AM_A_RPI:
                    mod_relay.cameraOn()
                time.sleep(10)
                logTxt("Camera has been turned on.")
                timekey = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')
                cmd = "timeout %d %s/debug/recordH264 %.1f %.1f %.1f \"%s\" \"%s\" %d %d %s %s %s %d %d %s/rawvideo/%s_%s" % (
                    secondsTillSunrise + 30, BINARY_PATH, getUTCoffset(), timeNow, tstop, CAMERA_ID, VIDEO_DEV,
                    sensorData.width, sensorData.height, sensorData.fps, latitude, longitude, flagGPS,
                    sensorData.upsideDown, DATA_PATH, timekey, CAMERA_ID)
                # Use timeout here, because sometime the RPi's openmax encoder hangs...
                logTxt("Running command: %s" % cmd)
                os.system(cmd)
                if I_AM_A_RPI:
                    mod_relay.cameraOff()
                logTxt("Camera has been turned off.")
                time.sleep(10)
                continue

    nextObservingTime = secondsTillSunset + sunMargin
    if nextObservingTime < 0:
        nextObservingTime += 3600 * 24 - 300
    # Do daytimejobs on a RPi only if we are doing real-time observation
    if (nextObservingTime > 3600) and (REAL_TIME or not I_AM_A_RPI):
        tstop = timeNow + nextObservingTime
        time.sleep(300)
        logTxt("Starting daytime jobs until %s (running for %d seconds)." % (
            datetime.datetime.fromtimestamp(tstop).strftime('%Y-%m-%d %H:%M:%S'), nextObservingTime))
        os.system("cd %s ; ./daytimeJobs.py %d %d" % (PYTHON_PATH, getUTCoffset(), tstop))
    else:
        logTxt("Not quite time to start observing yet, so let's sleep for %d seconds." % nextObservingTime)
        time.sleep(nextObservingTime)
    time.sleep(10)
