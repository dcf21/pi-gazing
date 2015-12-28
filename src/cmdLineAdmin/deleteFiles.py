#!../../virtual-env/bin/python
# deleteFiles.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import sys

import meteorpi_db
import meteorpi_model as mp
import mod_deleteOldData

from mod_settings import *
from mod_time import *

pid = os.getpid()
os.chdir(DATA_PATH)

utcMin = time.time() - 3600 * 24
utcMax = time.time()
cameraId = my_installation_id()

if len(sys.argv) > 1: utcMin = float(sys.argv[1])
if len(sys.argv) > 2: utcMax = float(sys.argv[2])
if len(sys.argv) > 3: cameraId = sys.argv[3]

if (utcMax == 0): utcMax = time.time()

print "# ./deleteImages.py %f %f \"%s\"\n" % (utcMin, utcMax, cameraId)

db_handle = meteorpi_db.MeteorDatabase(DBPATH, DBFILESTORE)

s = db_handle.get_camera_status(camera_id=cameraId)
if not s:
    print "Unknown camera <%s>. Run ./listCameras.py to see a list of available cameras." % cameraId
    sys.exit(0)

search = mp.FileRecordSearch(camera_ids=[cameraId], exclude_events=False, before=UTC2datetime(utcMax),
                             after=UTC2datetime(utcMin), limit=1000000)
files = db_handle.search_files(search)
files = [i for i in files['files']]
files.sort(key=lambda x: x.file_time)

search = mp.EventSearch(camera_ids=[cameraId], before=UTC2datetime(utcMax), after=UTC2datetime(utcMin), limit=1000000)
triggers = db_handle.search_events(search)
triggers = triggers['events']
triggers.sort(key=lambda x: x.event_time)

print "Camera <%s>" % cameraId
print "  * %6d matching files in time range %s --> %s" % (len(files), UTC2datetime(utcMin), UTC2datetime(utcMax))
print "  * %6d matching events in time range" % (len(triggers))

confirmation = raw_input('Delete these files? (Y/N) ')
if not confirmation in 'Yy': sys.exit(0)

mod_deleteOldData.delete_old_data(cameraId, utcMin, utcMax)
