from unittest import TestCase
import tempfile
from datetime import datetime

import meteorpi_fdb as db
import meteorpi_fdb.testing.dummy_data as dummy
import meteorpi_model as model
import os.path as path

DB_PATH_1 = 'localhost:/var/lib/firebird/2.5/data/meteorpi_test1.fdb'
FILE_PATH_1 = path.expanduser("~/meteorpi_test1_files")
DB_PATH_2 = 'localhost:/var/lib/firebird/2.5/data/meteorpi_test2.fdb'
FILE_PATH_2 = path.expanduser("~/meteorpi_test2_files")
PORT_1 = 12345


class TestFdb(TestCase):
    def __init__(self, *args, **kwargs):
        super(TestFdb, self).__init__(*args, **kwargs)
        self._status1 = model.CameraStatus(
            lens='a_lens',
            sensor='a_sensor',
            inst_url='http://foo.bar.com',
            inst_name='test installation',
            orientation=model.Orientation(
                0.5,
                0.6,
                0.7),
            location=model.Location(
                20.0,
                30.0,
                True,
                1.0),
            camera_id="aabbccddeeff")
        self._status1.regions = [[{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 0, "y": 100}], [
            {"x": 100, "y": 100}, {"x": 100, "y": 0}, {"x": 0, "y": 100}]]

    def test_get_installation_id(self):
        m = db.MeteorDatabase(db_path=DB_PATH_1, file_store_path=FILE_PATH_1)
        installation_id = m.installation_id
        self.assertTrue(len(installation_id) == 12)

    def test_insert_camera(self):
        m = db.MeteorDatabase(db_path=DB_PATH_1, file_store_path=FILE_PATH_1)
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
        m = db.MeteorDatabase(db_path=DB_PATH_1, file_store_path=FILE_PATH_1)
        m.clear_database()
        # Have to have a status block otherwise we should fail
        m.update_camera_status(ns=self._status1)
        tf = tempfile.mkstemp(suffix='.tmp', prefix='meteorpi_test_')
        tf_path = tf[1]
        record = m.register_file(file_path=tf_path,
                                 mime_type='text/plain',
                                 semantic_type=model.NSString('test_file'),
                                 file_time=datetime.now(),
                                 file_metas=[model.Meta(model.NSString('meta1'),
                                                        'value1'),
                                             model.Meta(model.NSString('meta2'),
                                                        'value2')])
        record2 = m.get_file(file_id=record.file_id)
        self.assertEqual(len(record.meta), 2)
        self.assertEqual(str(record), str(record2))
        self.assertFalse(record is record2)

    def test_insert_event(self):
        m = db.MeteorDatabase(db_path=DB_PATH_1, file_store_path=FILE_PATH_1)
        # Clear the database
        m.clear_database()
        # Have to have a status block otherwise we should fail
        m.update_camera_status(ns=self._status1)
        file1 = m.register_file(
            tempfile.mkstemp(
                suffix='.tmp',
                prefix='meteorpi_test_')[1],
            'text/plain',
            model.NSString('test_file'),
            datetime.now(),
            [
                model.Meta(model.NSString('meta1'),
                           'value1'),
                model.Meta(model.NSString('meta2'),
                           'value2')])
        file2 = m.register_file(
            tempfile.mkstemp(
                suffix='.tmp',
                prefix='meteorpi_test_')[1],
            'text/plain',
            model.NSString('test_file'),
            datetime.now(),
            [
                model.Meta(key=model.NSString('meta3'),
                           value='value3'),
                model.Meta(key=model.NSString('meta4'),
                           value=0.4)])
        event = m.register_event(
            camera_id=m.installation_id,
            event_time=datetime.now(),
            event_type=model.NSString("omgmeteors"),
            file_records=[file1, file2])
        event2 = m.get_event(event_id=event.event_id)

    def test_event_search(self):
        m = db.MeteorDatabase(db_path=DB_PATH_1, file_store_path=FILE_PATH_1)
        dummy.setup_dummy_data(m, clear=True)
        events = m.search_events(model.EventSearch())

    def test_rollback(self):
        m = db.MeteorDatabase(db_path=DB_PATH_1, file_store_path=FILE_PATH_1)
        dummy.setup_dummy_data(m, clear=True)
        # print m.get_high_water_mark(camera_id=dummy.CAMERA_1)
        m.set_high_water_mark(camera_id=dummy.CAMERA_1, time=dummy.make_time(6))

    def test_user_management(self):
        m = db.MeteorDatabase(db_path=DB_PATH_1, file_store_path=FILE_PATH_1)
        m.clear_database()
        self.assertEquals("create", m.create_or_update_user(user_id="tom", password="password1", roles=["user"]))
        user = m.get_user(user_id="tom", password="password1")
        self.assertTrue(user.has_role("user"))
        self.assertFalse(user.has_role("camera_admin"))
        self.assertEquals("update",
                          m.create_or_update_user(user_id="tom", password=None, roles=["user", "camera_admin"]))
        user = m.get_user(user_id="tom", password="password1")
        self.assertTrue(user.has_role("user"))
        self.assertTrue(user.has_role("camera_admin"))
