#!../../virtual-env/bin/python
# deleteImages.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import os,time,sys,glob,datetime,operator
from math import *

from mod_settings import *
from mod_time import *
from mod_astro import *

import meteorpi_model as mp
import meteorpi_fdb

pid = os.getpid()
os.chdir(DATA_PATH)

utcMin   = time.time() - 3600*24
utcMax   = time.time()
cameraId = my_installation_id()

if len(sys.argv)>1: utcMin   = float(sys.argv[1])
if len(sys.argv)>2: utcMax   = float(sys.argv[2])
if len(sys.argv)>3: cameraId =       sys.argv[3]

if (utcMax==0): utcMax = time.time()

print "# ./deleteImages.py %f %f \"%s\"\n"%(utcMin,utcMax,cameraId)

fdb_handle = meteorpi_fdb.MeteorDatabase( DBPATH , FDBFILESTORE )

s = fdb_handle.get_camera_status(camera_id=cameraId)
if not s:
  print "Unknown camera <%s>. Run ./listCameras.py to see a list of available cameras."%cameraId
  sys.exit(0)

search = mp.FileRecordSearch(camera_ids=[cameraId],exclude_events=False,before=UTC2datetime(utcMax),after=UTC2datetime(utcMin),limit=1000000)
files  = fdb_handle.search_files(search)
files  = [i for i in files['files']]
files.sort(key=lambda x: x.file_time)

search = mp.EventSearch(camera_ids=[cameraId],before=UTC2datetime(utcMax),after=UTC2datetime(utcMin),limit=1000000)
triggers = fdb_handle.search_events(search)
triggers = triggers['events']
triggers.sort(key=lambda x: x.event_time)

print "Camera <%s>"%cameraId
print "  * %6d matching files in time range %s --> %s"%(len(files),UTC2datetime(utcMin),UTC2datetime(utcMax))
print "  * %6d matching events in time range"%(len(triggers))

confirmation = raw_input('Delete these files? (Y/N) ')
if not confirmation in 'Yy': sys.exit(0)

from contextlib import closing

with closing(fdb_handle.con.trans()) as transaction:
  with closing(fdb_handle.con.cursor()) as read_cursor, closing(transaction.cursor()) as update_cursor:
     read_cursor.execute(
         'SELECT fileID AS file_id FROM t_file '
         'WHERE fileTime > (?) AND fileTime < (?) AND cameraID = (?) FOR UPDATE',
            (mp.utc_datetime_to_milliseconds(UTC2datetime(utcMin)), mp.utc_datetime_to_milliseconds(UTC2datetime(utcMax)), cameraId))
     read_cursor.name = "read_cursor"
     for (file_id,) in read_cursor:
         update_cursor.execute("DELETE FROM t_file WHERE CURRENT OF read_cursor")
         file_path = os.path.join(fdb_handle.file_store_path, uuid.UUID(bytes=file_id).hex)
         try:
             os.remove(file_path)
         except OSError:
             print "Warning: could not remove file {0}.".format(file_path)
     update_cursor.execute(
         "DELETE FROM t_event WHERE eventTime > (?) AND eventTime < (?) AND cameraID = (?)",
         (mp.utc_datetime_to_milliseconds(UTC2datetime(utcMin)), mp.utc_datetime_to_milliseconds(UTC2datetime(utcMax)), cameraId))
transaction.commit()

