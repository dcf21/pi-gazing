from unittest import TestCase

import requests
import yaml
import os.path as path
import meteorpi_server
import meteorpi_fdb.testing.dummy_data as dummy
import meteorpi_model as model

DB_PATH_1 = 'localhost:/var/lib/firebird/2.5/data/meteorpi_test1.fdb'
FILE_PATH_1 = path.expanduser("~/meteorpi_test_1_files")
DB_PATH_2 = 'localhost:/var/lib/firebird/2.5/data/meteorpi_test2.fdb'
FILE_PATH_2 = path.expanduser("~/meteorpi_test_2_files")
PORT_1 = 12345


class TestServer(TestCase):
    def __init__(self, *args, **kwargs):
        super(TestServer, self).__init__(*args, **kwargs)
        self.server = meteorpi_server.MeteorServer(db_path=DB_PATH_1, file_store_path=FILE_PATH_1, port=PORT_1)

    def setUp(self):
        """Clear the database and populate it with example contents"""
        dummy.setup_dummy_data(self.server.db, clear=True)
        # Start the server, returns a function
        # which can be used to stop it afterwards
        self.stop = self.server.start_non_blocking()

    def tearDown(self):
        """Stop the server"""
        self.stop()
        self.stop = None

    def test_list_cameras(self):
        cameras_from_db = self.server.db.get_cameras()
        response = requests.get(self.server.base_url() + '/cameras').text
        cameras_from_api = yaml.safe_load(response)['cameras']
        self.assertSequenceEqual(cameras_from_db, cameras_from_api)

    def test_get_camera_status(self):
        status_from_db = self.server.db.get_camera_status(camera_id=dummy.CAMERA_1)
        response = requests.get(self.server.base_url() + '/cameras/{0}/status'.format(dummy.CAMERA_1)).text
        status_from_api = model.CameraStatus.from_dict(yaml.safe_load(response)['status'])
        self.assertDictEqual(status_from_api.as_dict(), status_from_db.as_dict())
