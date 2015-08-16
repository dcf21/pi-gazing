# mod_hardwareProps.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import os
import xml.etree.cElementTree as ElementTree

import mod_xml
from mod_time import *

class sensor:

  def __init__(self, name, width, height, fps, upsideDown, cameraType):
    self.name       = name
    self.width      = width
    self.height     = height
    self.fps        = fps
    self.upsideDown = upsideDown
    self.cameraType = cameraType

  def __str__(self):
    print "sensor(%s,%s,%s,%s,%s,%s)"%(self.name,self.width,self.height,self.fps,self.upsideDown,self.cameraType)

class lens:

  def __init__(self, name, fov, barrel_a, barrel_b, barrel_c):
    self.name       = name
    self.fov        = fov
    self.barrel_a   = barrel_a
    self.barrel_b   = barrel_b
    self.barrel_c   = barrel_c

  def __str__(self):
    print "lens(%s,%s,%s,%s,%s)"%(self.name,self.fov,self.barrel_a,self.barrel_b,self.barrel_c)

class hardwareProps:

  def __init__(self, path):
    sensorsDataPath = os.path.join(path, "sensors.xml")
    lensDataPath    = os.path.join(path, "lenses.xml")
    assert os.path.exists(sensorsDataPath), "Could not find sensor data in file <%s>"%sensorsDataPath
    assert os.path.exists(lensDataPath)   , "Could not find lens data in file <%s>"%lensDataPath

    tree = ElementTree.parse(sensorsDataPath)
    root = tree.getroot()
    sensorXml = mod_xml.XmlListConfig(root)

    self.sensorData = {}
    for d in sensorXml:
      self.sensorData[ d['name'] ] = sensor( d['name'] , int(d['width']) , int(d['height']) , float(d['fps']) , int(d['upsidedown']) , d['type'] )

    tree = ElementTree.parse(lensDataPath)
    root = tree.getroot()
    lensXml = mod_xml.XmlListConfig(root)

    self.lensData = {}
    for d in lensXml:
      self.lensData[ d['name'] ] = lens( d['name'] , float(d['fov']) , float(d['barrel_a']) , float(d['barrel_b']) , float(d['barrel_c']) )


def fetchSensorData(fdb_handle,hw_handle,cameraId,utc):
  cameraStatus = fdb_handle.get_camera_status(camera_id=cameraId,time=UTC2datetime(utc))
  assert cameraStatus, "Camera status is not set for cameraId <%s> at time %d"%(cameraId,utc)
  assert cameraStatus.sensor in hw_handle.sensorData, "Unknown sensor type <%s>"%cameraStatus.sensor
  return hw_handle.sensorData[cameraStatus.sensor]

def fetchLensData(fdb_handle,hw_handle,cameraId,utc):
  cameraStatus = fdb_handle.get_camera_status(camera_id=cameraId,time=UTC2datetime(utc))
  assert cameraStatus, "Camera status is not set"
  assert cameraStatus.lens   in hw_handle.lensData  , "Unknown lens type <%s>"%cameraStatus.lens
  return hw_handle.lensData[cameraStatus.lens]

