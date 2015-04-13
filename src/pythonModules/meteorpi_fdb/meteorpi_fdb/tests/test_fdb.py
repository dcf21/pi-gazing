from unittest import TestCase
import tempfile
from datetime import datetime

import meteorpi_fdb as db
import meteorpi_model as model


class TestFdb(TestCase):
    def __init__(self, *args, **kwargs):
        super(TestFdb, self).__init__(*args, **kwargs)
        self._status1 = model.CameraStatus(
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
                True,
                1.0))
        self._status1.regions = [[{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 0, "y": 100}], [
            {"x": 100, "y": 100}, {"x": 100, "y": 0}, {"x": 0, "y": 100}]]

    def test_get_installation_id(self):
        m = db.MeteorDatabase()
        installation_id = db.get_installation_id()
        self.assertTrue(len(installation_id) == 12)

    def test_get_next_internal_id(self):
        m = db.MeteorDatabase()
        id1 = m.get_next_internal_id()
        id2 = m.get_next_internal_id()
        self.assertTrue(id2 == id1 + 1)

    def test_insert_camera(self):
        m = db.MeteorDatabase()
        # Clear the database
        m.clear_database()
        self.assertTrue(len(m.get_cameras()) == 0)
        self.assertTrue(m.get_camera_status() is None)
        m.update_camera_status(ns=self._status1)
        # Check that we now have a camera in the database
        self.assertTrue(len(m.get_cameras()) == 1)
        status = m.get_camera_status()
        self.assertFalse(status is None)
        # Check that the validTo field of the retrieved status is None
        self.assertTrue(status.valid_to is None)
        # Check that the regions have been retrieved
        self.assertTrue(len(status.regions) == 2)
        self.assertTrue(len(status.regions[0]) == 3)
        self.assertTrue(len(status.regions[1]) == 3)

    def test_insert_file(self):
        m = db.MeteorDatabase()
        m.clear_database()
        # Have to have a status block otherwise we should fail
        m.update_camera_status(ns=self._status1)
        tf = tempfile.mkstemp(suffix='.tmp', prefix='meteorpi_test_')
        tf_path = tf[1]
        record = m.register_file(file_path=tf_path,
                                 mime_type='text/plain',
                                 namespace='meteorpi',
                                 semantic_type='test_file',
                                 file_time=datetime.now(),
                                 file_metas=[model.FileMeta('meteorpi',
                                                            'meta1',
                                                            'value1'),
                                             model.FileMeta('meteorpi',
                                                            'meta2',
                                                            'value2')])
        record2 = m.get_file(file_id=record.file_id)
        self.assertEqual(len(record.meta), 2)
        self.assertEqual(str(record), str(record2))
        self.assertFalse(record is record2)

    def test_insert_event(self):
        m = db.MeteorDatabase()
        # Clear the database
        m.clear_database()
        # Have to have a status block otherwise we should fail
        m.update_camera_status(ns=self._status1)
        file1 = m.register_file(
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
        file2 = m.register_file(
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
        event = m.register_event(
            camera_id=db.get_installation_id(),
            event_time=datetime.now(),
            intensity=0.5,
            bezier=model.Bezier(
                0, 1, 2, 3, 4, 5, 6, 7),
            file_records=[file1, file2])
        event2 = m.get_events(event_id=event.event_id)[0]

    def test_event_search(self):
        m = db.MeteorDatabase()
        m.clear_database()
        events = m.search_events(model.EventSearch())
        # TODO - verify that this has done the right thing. It doesn't crash at least...