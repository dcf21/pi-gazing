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
    if subDictName not in d: d['subDictName']={}
    d = d['subDictName']
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
  for ext in os.path.split(fname)[1].split("_")[2:]: # e.g. ["BS0"]
    if   (ext[-1]=="0"): continue
    elif (ext=="BS1")  : path.append("bgrdSub")
    elif (ext=="LC1")  : path.append("lensCorr")
    else               : path.append(ext)
  return "/".join(path)

# Import still images
dirs = ["timelapse_img_processed" , "trigger_img_processed"]
imgs = {}
for dirname in dirs:
  for fname in glob.glob(os.path.join(dirname,"*/*.png")):
    fstub    = fname[:-4]
    utc      = mod_hwm.filenameToUTC(fname)
    metadict = mod_hwm.fileToDB("%s.txt"%fstub)
    assert "cameraId" in metadict, "Timelapse photograph <%s> does not have a cameraId set."%fname
    cameraId = metadict["cameraId"]
    if cameraId not in hwm_old: hwm_old[cameraId] = datetime2UTC( fdb_handle.get_high_water_mark(cameraId) )
    if utc < hwm_old[cameraId]: continue
    metadata = metadataToFDB(metadict)
    semanticType = localFilenameToSemanticType(fname)
    fileObj = fdb_handle.register_file(fname, "image/png", mp.NSString(semanticType,"meteorpi"), UTC2datetime(utc), metadata, cameraId)
    dictTreeAppend(imgs, [dirname,utc], fileObj)
    hwm_new[cameraId] = max(hwm_old[cameraId] , utc)

# Import trigger events
for fname in glob.glob("trigger_vid_processed/*/*.png"):
    fstub    = fname[:-4]
    utc      = mod_hwm.filenameToUTC(fname)
    metadict = mod_hwm.fileToDB("%s.txt"%fstub)
    assert "cameraId" in metadict, "Trigger video <%s> does not have a cameraId set."%fname
    cameraId = metadict["cameraId"]
    if cameraId not in hwm_old: hwm_old[cameraId] = datetime2UTC( fdb_handle.get_high_water_mark(cameraId) )
    if utc < hwm_old[cameraId]: continue
    metadata = metadataToFDB(metadict)
    semanticType = localFilenameToSemanticType(fname)
    fileObjs = [ fdb_handle.register_file(fname, "video/mp4", mp.NSString(semanticType,"meteorpi"), UTC2datetime(utc), metadata, cameraId) ]
    fileObjs.extend( imgs["trigger_img_processed",utc] )
    intensity = 0 # null for now
    eventObj = fdb_handle.register_event(cameraId, utc, intensity, bezierNull, fileObjs)
    hwm_new[cameraId] = max(hwm_new[cameraId] , utc)

# Update firebird hwm
for cameraId,utc in hwm_new.iteritems():
  fdb_handle.set_high_water_mark( UTC2datetime(utc) , cameraId )

os.chdir(cwd)

