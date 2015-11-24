#!../../virtual-env/bin/python
# listImages.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import meteorpi_fdb
import meteorpi_model as mp

from mod_astro import *
from mod_settings import *
from mod_time import *

pid = os.getpid()
os.chdir(DATA_PATH)

utcMin = time.time() - 3600 * 24
utcMax = time.time()
cameraId = my_installation_id()
label = ""
imgType = "timelapse/frame/bgrdSub/lensCorr"
stride = 5

if len(sys.argv) > 1: utcMin = float(sys.argv[1])
if len(sys.argv) > 2: utcMax = float(sys.argv[2])
if len(sys.argv) > 3: cameraId = sys.argv[3]
if len(sys.argv) > 4: label = sys.argv[4]
if len(sys.argv) > 5: imgType = sys.argv[5]
if len(sys.argv) > 6: stride = int(sys.argv[6])

if (utcMax == 0): utcMax = time.time()

print "# ./listImages.py %f %f \"%s\" \"%s\" \"%s\" %d\n" % (utcMin, utcMax, cameraId, label, imgType, stride)

fdb_handle = meteorpi_fdb.MeteorDatabase(DBPATH, FDBFILESTORE)

search = mp.FileRecordSearch(camera_ids=[cameraId], semantic_type=mp.NSString(imgType), exclude_events=True,
                             before=UTC2datetime(utcMax), after=UTC2datetime(utcMin), limit=1000000)
files = fdb_handle.search_files(search)
files = [i for i in files['files']]
files.sort(key=lambda x: x.file_time)


def metadata2dict(metadata):
    output = {}
    for i in metadata:
        if (i.key.ns == "meteorpi"):
            output[i.key.s] = i.value
    return output


s = fdb_handle.get_camera_status(camera_id=cameraId)
if not s:
    print "Unknown camera <%s>. Run ./listCameras.py to see a list of available cameras." % cameraId
    sys.exit(0)

print "Camera <%s>" % cameraId
print "  * High water mark: %s" % fdb_handle.get_high_water_mark(camera_id=cameraId)
print "  * Software: %s" % s.software_version
print "  * Lens: %s" % s.lens
print "  * Sensor: %s" % s.sensor
print "  * Validity of this status: %s -> %s" % (s.valid_from, s.valid_to)
print "  * Location: %s" % s.location
print "  * Orientation: %s" % s.orientation
print "  * Regions: %s" % s.regions
print "  * %d matching files in time range %s --> %s" % (len(files), UTC2datetime(utcMin), UTC2datetime(utcMax))
count = 1
for fileObj in files:
    count += 1
    if not (count % stride == 0): continue
    metadata = metadata2dict(fileObj.meta)
    [year, month, day, h, m, s] = InvJulianDay(JDfromUTC(datetime2UTC(fileObj.file_time)))
    print "  * Unix %12.1f   date %04d/%02d/%02d %02d:%02d:%02d UTC   sky clarity %8.1f   filename <%s>" % (
    datetime2UTC(fileObj.file_time), year, month, day, h, m, s, float(metadata['skyClarity']), fileObj.get_path())
