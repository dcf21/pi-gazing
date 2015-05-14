#!/usr/bin/python
# firebirdImport.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import os,time,sys,glob,datetime,operator

import mod_log
from mod_log import logTxt,getUTC
from mod_settings import *
from mod_time import *
import mod_hwm

import meteorpi_model as mp
import meteorpi_fdb
fdb_handle = meteorpi_fdb.MeteorDatabase( DBPATH , FDBFILESTORE )

pid = os.getpid()
cwd = os.getcwd()

os.chdir(DATA_PATH)

hwm_old = {}
hwm_new = {}

bezierNull = mp.Bezier(0,0,0,0,0,0,0,0)

def dictTreeAppend(dictRoot, dictPath, value):
  d = dictRoot
  for subDictName in dictPath[:-1]:
    if subDictName not in d: d[subDictName]={}
    d = d[subDictName]
  leafName = dictPath[-1]
  if leafName not in d: d[leafName]=[]
  d[leafName].append(value)

def metadataToFDB(metadict):
  metadata = []
  for metafield in metadict:
    metadata.append( mp.FileMeta( mp.NSString(metafield,"meteorpi"),metadict[metafield]) )
  return metadata

def localFilenameToSemanticType(fname):

  # Input e.g. timelapse_img_processed/20150505/20150505220000_cameraId_BS0.png
  #  -->       timelapse/BS0

  path = [ fname.split("_")[0] ] # e.g. "timelapse"
  for ext in os.path.split(fname)[1][:-4].split("_")[2:]: # e.g. ["BS0"]
    if   (ext[-1]=="0"): continue
    elif (ext=="BS1")  : path.append("bgrdSub")
    elif (ext=="LC1")  : path.append("lensCorr")
    else               : path.append(ext)
  return "/".join(path)

# Create list of files and events we are importing
dirs = ["timelapse_img_processed" , "triggers_img_processed"]
files= {}
imgs = {}
for dirname in dirs:
  files[dirname] = glob.glob(os.path.join(dirname,"*/*.png"))

triggerList = glob.glob("triggers_vid_processed/*/*.mp4")

# Import still images
for dirname in dirs:
  for fname in files[dirname]:
    fstub    = fname[:-4]
    utc      = mod_hwm.filenameToUTC(fname)
    metafile = "%s.txt"%fstub # File containing metadata
    metadict = mod_hwm.fileToDB(metafile) # Dictionary of image metadata
    assert "cameraId" in metadict, "Timelapse photograph <%s> does not have a cameraId set."%fname
    cameraId = metadict["cameraId"]
    if cameraId not in hwm_old: hwm_old[cameraId] = datetime2UTC( fdb_handle.get_high_water_mark(cameraId) )
    if utc < hwm_old[cameraId]: continue
    metadata = metadataToFDB(metadict) # List of metadata objects
    semanticType = localFilenameToSemanticType(fname)
    logTxt("Registering file <%s>, with cameraId <%s>"%(fname,cameraId))
    fileObj = fdb_handle.register_file(fname, "image/png", mp.NSString(semanticType,"meteorpi"), UTC2datetime(utc), metadata, cameraId)
    if (os.path.exists(metafile)): os.remove(metafile) # Clean up metadata files that we've finished with
    dictTreeAppend(imgs, [dirname,utc], fileObj)
    hwm_new[cameraId] = max(hwm_old[cameraId] , utc)

# Import trigger events
for fname in triggerList:
    fstub    = fname[:-4]
    utc      = mod_hwm.filenameToUTC(fname)
    metafile = "%s.txt"%fstub # File containing metadata
    metadict = mod_hwm.fileToDB(metafile) # Dictionary of image metadata
    assert "cameraId" in metadict, "Trigger video <%s> does not have a cameraId set."%fname
    cameraId = metadict["cameraId"]
    if cameraId not in hwm_old: hwm_old[cameraId] = datetime2UTC( fdb_handle.get_high_water_mark(cameraId) )
    if utc < hwm_old[cameraId]: continue
    metadata = metadataToFDB(metadict) # List of metadata objects
    semanticType = localFilenameToSemanticType(fname)
    fileObjs = [ fdb_handle.register_file(fname, "video/mp4", mp.NSString(semanticType,"meteorpi"), UTC2datetime(utc), metadata, cameraId) ]
    fileObjs.extend( imgs["triggers_img_processed"][utc] )
    intensity = 0 # null for now
    logTxt("Registering event <%s>, with cameraId <%s> and %d files"%(fname,cameraId,len(fileObjs)))
    eventObj = fdb_handle.register_event(cameraId, UTC2datetime(utc), intensity, bezierNull, fileObjs)
    if (os.path.exists(metafile)): os.remove(metafile) # Clean up metadata files that we've finished with
    hwm_new[cameraId] = max(hwm_new[cameraId] , utc)

# Update firebird hwm
for cameraId,utc in hwm_new.iteritems():
  fdb_handle.set_high_water_mark( UTC2datetime(utc) , cameraId )

os.chdir(cwd)

