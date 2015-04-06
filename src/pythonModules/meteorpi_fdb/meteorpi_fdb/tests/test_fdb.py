from unittest import TestCase
import meteorpi_fdb as db
import meteorpi_model as model
import tempfile
import os
from datetime import datetime


class TestFdb(TestCase):

    def testGetInstallationID(self):
        m = db.MeteorDatabase()
        installationID = db.getInstallationID()
        self.assertTrue(len(installationID) == 12)

    def testGetNextInternalId(self):
        m = db.MeteorDatabase()
        id1 = m.getNextInternalID()
        id2 = m.getNextInternalID()
        self.assertTrue(id2 == id1 + 1)

    def testInsertCamera(self):
        m = db.MeteorDatabase()
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

    def testInsertFile(self):
        m = db.MeteorDatabase()
        m.clearDatabase()
        tf = tempfile.mkstemp(suffix='.tmp', prefix='meteorpi_test_')
        tfPath = tf[1]
        record = m.registerFile(tfPath,
                                'text/plain',
                                'meteorpi',
                                'test_file',
                                datetime.now(),
                                [model.FileMeta('meteorpi',
                                                'meta1',
                                                'value1'),
                                 model.FileMeta('meteorpi',
                                                'meta2',
                                                'value2')])
        record2 = m.getFile(record.fileID)
        self.assertEqual(len(record.meta), 2)
        self.assertEqual(str(record), str(record2))
        self.assertFalse(record is record2)

    def testInsertEvent(self):
        m = db.MeteorDatabase()
        # Clear the database
        m.clearDatabase()
        file1 = m.registerFile(
            tempfile.mkstemp(
                suffix='.tmp',
                prefix='meteorpi_test_')[1],
            'text/plain',
            'meteorpi',
            'test_file',
            datetime.now(),
            [
                model.FileMeta(
                    'meteorpi',
                    'meta1',
                    'value1'),
                model.FileMeta(
                    'meteorpi',
                    'meta2',
                    'value2')])
        file2 = m.registerFile(
            tempfile.mkstemp(
                suffix='.tmp',
                prefix='meteorpi_test_')[1],
            'text/plain',
            'meteorpi',
            'test_file',
            datetime.now(),
            [
                model.FileMeta(
                    'meteorpi',
                    'meta3',
                    'value3'),
                model.FileMeta(
                    'meteorpi',
                    'meta4',
                    'value4')])
        event = m.registerEvent(
            db.getInstallationID(),
            datetime.now(),
            0.5,
            model.Bezier(
                0, 1, 2, 3, 4, 5, 6, 7),
            [file1, file2])
