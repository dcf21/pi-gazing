#!../../virtual-env/bin/python
# timelapseMovie.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# Make a timelapse video of images recording between specified start and end times

from math import *

import meteorpi_db
import meteorpi_model as mp

from mod_settings import *
from mod_time import *

pid = os.getpid()
os.chdir(DATA_PATH)

utcMin = time.time() - 3600 * 24
utcMax = time.time()
cameraId = my_installation_id()
label = ""
imgType = "timelapse/frame/bgrdSub/lensCorr"
stride = 1

if len(sys.argv) > 1: utcMin = float(sys.argv[1])
if len(sys.argv) > 2: utcMax = float(sys.argv[2])
if len(sys.argv) > 3: cameraId = sys.argv[3]
if len(sys.argv) > 4: label = sys.argv[4]
if len(sys.argv) > 5: imgType = sys.argv[5]
if len(sys.argv) > 6: stride = int(sys.argv[6])

if (utcMax == 0): utcMax = time.time()

print "./timelapseMovie.py %f %f \"%s\" \"%s\" \"%s\" %d" % (utcMin, utcMax, cameraId, label, imgType, stride)

db_handle = meteorpi_db.MeteorDatabase(DBPATH, DBFILESTORE)

s = db_handle.get_camera_status(camera_id=cameraId)
if not s:
    print "Unknown camera <%s>. Run ./listCameras.py to see a list of available cameras." % cameraId
    sys.exit(0)

search = mp.FileRecordSearch(camera_ids=[cameraId], semantic_type=mp.NSString(imgType), exclude_events=True,
                             before=UTC2datetime(utcMax), after=UTC2datetime(utcMin), limit=1000000)
files = db_handle.search_files(search)
files = [i for i in files['files']]
files.sort(key=lambda x: x.file_time)

print "Found %d images between time <%s> and <%s> from camera <%s>" % (
len(files), UTC2datetime(utcMin), UTC2datetime(utcMax), cameraId)

filestub = "/tmp/frame_%d_%%08d.jpg" % pid

imgNo = 1
count = 1
for f in files:
    count += 1
    if not (count % stride == 0): continue
    utc = datetime2UTC(f.file_time)
    os.system(
        """convert %s -gravity SouthEast -fill ForestGreen -pointsize 20 -font Ubuntu-Bold -annotate +16+10 '%s %s' %s""" % (
        f.get_path(), label, time.strftime("%d %b %Y %H:%M", time.gmtime(utc)), filestub % imgNo))
    imgNo += 1

os.system("""avconv -r 40 -i %s -codec:v libx264 /tmp/timelapse.mp4""" % filestub)
