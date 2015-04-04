from unittest import TestCase

import meteorpi_fdb as m
import meteorpi_model as model


class TestFdb(TestCase):

    def testGetInstallationID(self):
        installationID = m.getInstallationID()
        self.assertTrue(len(installationID) == 12)

    def testGetNextInternalId(self):
        id1 = m.getNextInternalID()
        id2 = m.getNextInternalID()
        self.assertTrue(id2 == id1 + 1)

    def testInsertCamera(self):
        # Clear the database
        m.clearDatabase()
        self.assertTrue(len(m.getCameras()) == 0)
        self.assertTrue(m.getCameraStatus() is None)
        newStatus = model.CameraStatus(
            'a_lens',
            'a_sensor',
            'http://foo.bar.com',
            'test installation',
            model.Orientation(
                0.5,
                0.6,
                0.7),
            model.Location(
                20.0,
                30.0,
                True))
        newStatus.regions = [[{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 0, "y": 100}], [
            {"x": 100, "y": 100}, {"x": 100, "y": 0}, {"x": 0, "y": 100}]]
        m.updateCameraStatus(newStatus)
        # Check that we now have a camera in the database
        self.assertTrue(len(m.getCameras()) == 1)
        status = m.getCameraStatus()
        self.assertFalse(status is None)
        # Check that the validTo field of the retrieved status is None
        self.assertTrue(status.validTo is None)
        # Check that the regions have been retrieved
        self.assertTrue(len(status.regions) == 2)
        self.assertTrue(len(status.regions[0]) == 3)
        self.assertTrue(len(status.regions[1]) == 3)
        print status
