from unittest import TestCase
import requests

import yaml

import meteorpi_server
import meteorpi_fdb.testing.dummy_data as dummy
import meteorpi_model as model


class TestServer(TestCase):
    def __init__(self, *args, **kwargs):
        super(TestServer, self).__init__(*args, **kwargs)
        self.server = meteorpi_server.MeteorServer()

    def setUp(self):
        """Clear the database and populate it with example contents"""
        dummy.setup_dummy_data(self.server.db, clear=True)
        # Start the server, returns a function
        # which can be used to stop it afterwards
        self.stop = self.server.start_non_blocking()

    def tearDown(self):
        """Stop the server"""
        self.stop()
        self.server = None

    def test_list_cameras(self):
        cameras_from_db = self.server.db.get_cameras()
        response = requests.get(self.server.base_url() + '/cameras').text
        cameras_from_api = yaml.safe_load(response)['cameras']
        self.assertSequenceEqual(cameras_from_db, cameras_from_api)

    def test_get_camera_status(self):
        status_from_db = self.server.db.get_camera_status(cameraID='aabbccddeeff')
        response = requests.get(self.server.base_url() + '/cameras/{0}/status'.format('aabbccddeeff')).text
        status_from_api = model.CameraStatus.from_dict(yaml.safe_load(response)['status'])
        self.assertDictEqual(status_from_api.as_dict(), status_from_db.as_dict())
