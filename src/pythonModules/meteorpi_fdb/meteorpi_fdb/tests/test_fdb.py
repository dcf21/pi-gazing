from unittest import TestCase

import meteorpi_fdb as m
import meteorpi_model as model

class TestFdb(TestCase):
	def testGetInstallationID(self):
		print 'Installation ID is:', m.getInstallationID()

	def testGetNextInternalId(self):
		print 'Incremented internal ID generator to:', m.getNextInternalID() 

	def testGetCameras(self):
		print 'Cameras with current status blocks:', m.getCameras()

	def testInsertCamera(self):
		newStatus = model.CameraStatus('a_lens','a_camera','http://foo.bar.com','test installation', model.Orientation(0.5, 0.6, 0.7), model.Location(20.0, 30.0, True))
		print(newStatus)
		m.updateCameraStatus(newStatus)
		print m.getCameraStatus()

	
		
