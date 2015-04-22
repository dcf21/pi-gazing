from unittest import TestCase
import requests

import meteorpi_server


class TestServer(TestCase):
    def __init__(self, *args, **kwargs):
        super(TestServer, self).__init__(*args, **kwargs)
        self.server = meteorpi_server.MeteorServer()

    def setUp(self):
        self.stop = self.server.start_non_blocking()

    def tearDown(self):
        self.stop()
        self.server = None


    def test_server(self):
        print requests.get(self.server.base_url() + '/cameras').text

    def test_server_again(self):
        print requests.get(self.server.base_url() + '/cameras/test_id').text