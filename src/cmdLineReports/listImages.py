#!../../virtual-env/bin/python
# listImages.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import os,time,sys,glob,datetime,operator
from math import *

from mod_settings import *
from mod_time import *

import meteorpi_model as mp
import meteorpi_fdb

pid = os.getpid()
os.chdir(DATA_PATH)

utcMin   = time.time() - 3600*24
utcMax   = time.time()
cameraId = my_installation_id()
label    = ""
imgType  = "timelapse/frame/bgrdSub/lensCorr"
stride   = 1

if len(sys.argv)>1: utcMin   = float(sys.argv[1])
if len(sys.argv)>2: utcMax   = float(sys.argv[2])
if len(sys.argv)>3: cameraId =       sys.argv[3]
if len(sys.argv)>4: label    =       sys.argv[4]
if len(sys.argv)>5: imgType  =       sys.argv[5]
if len(sys.argv)>6: stride   = int  (sys.argv[6])

if (utcMax==0): utcMax = time.time()

print "./listImages.py %f %f \"%s\" \"%s\" \"%s\" %d"%(utcMin,utcMax,cameraId,label,imgType,stride)

fdb_handle = meteorpi_fdb.MeteorDatabase( DBPATH , FDBFILESTORE )

search = mp.FileRecordSearch(camera_ids=[cameraId],semantic_type=mp.NSString(imgType),exclude_events=True,before=UTC2datetime(utcMax),after=UTC2datetime(utcMin),limit=1000000)
files  = fdb_handle.search_files(search)
files  = [i for i in files['files']]
files.sort(key=lambda x: x.file_time)

def metadata2dict(metadata):
  output={}
  for i in metadata:
    if (i.key.ns=="meteorpi"):
      output[i.key.s] = i.value
  return output

title = "Camera <%s>"%cameraId
print "\n\n%s\n%s"%(title,"-"*len(title))
print "%s\n  * %s\n  * High water mark: %s"%(cameraId,fdb_handle.get_camera_status(camera_id=cameraId),fdb_handle.get_high_water_mark(camera_id=cameraId))
print "  * %d matching files in time range %s --> %s"%(len(files),utcMin,utcMax)
count=1
for fileObj in files:
  count+=1
  if not (count%stride==0): continue
  metadata = metadata2dict(fileObj.meta)
  print "  * UTC %12.1f   date %-30s   sky clarity %8.1f   filename <%s>"%(datetime2UTC(fileObj.file_time) , fileObj.file_time , float(metadata['skyClarity']) , fileObj.get_path())

