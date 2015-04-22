from unittest import TestCase
import requests

import meteorpi_server
import meteorpi_fdb.testing.dummy_data as dummy


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

    def test_server(self):
        print requests.get(self.server.base_url() + '/cameras').text

    def test_server_again(self):
        print requests.get(self.server.base_url() + '/cameras/test_id').text