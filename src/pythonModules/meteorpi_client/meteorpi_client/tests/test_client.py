from unittest import TestCase

import meteorpi_server
import meteorpi_fdb.testing.dummy_data as dummy
import meteorpi_client as client
import meteorpi_model as model


class TestClient(TestCase):
    def __init__(self, *args, **kwargs):
        super(TestClient, self).__init__(*args, **kwargs)
        self.server = meteorpi_server.MeteorServer()
        self.client = client.MeteorClient(base_url=self.server.base_url())

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
        cameras_from_client = self.client.list_cameras()
        self.assertSequenceEqual(cameras_from_db, cameras_from_client)

    def test_get_camera_status(self):
        # Test acquiring status with no time, should use the current time.
        status_from_db_now = self.server.db.get_camera_status(camera_id=dummy.CAMERA_1)
        status_from_client_now = self.client.get_camera_status(camera_id=dummy.CAMERA_1)
        self.assertDictEqual(status_from_db_now.as_dict(), status_from_client_now.as_dict())
        # Test that an unknown camera results in a status of None (logs will show a 404 from the server)
        self.assertEquals(self.client.get_camera_status(camera_id='nosuchcamera'), None)
        for t in range(0, 30):
            # At time 0 there shouldn't be a status and both should return None
            status_from_db = self.server.db.get_camera_status(camera_id=dummy.CAMERA_1, time=dummy.make_time(t))
            status_from_client = self.client.get_camera_status(camera_id=dummy.CAMERA_1, time=dummy.make_time(t))
            if status_from_db is not None and status_from_client is not None:
                self.assertDictEqual(status_from_db.as_dict(), status_from_client.as_dict())
            else:
                self.assertEquals(status_from_db, status_from_client)

    def test_search_events(self):
        # Run all the searches in the list below, checking that results from the db and the client match
        searches = [
            model.EventSearch(),
            model.EventSearch(camera_ids=dummy.CAMERA_1),
            model.EventSearch(camera_ids=[dummy.CAMERA_1, dummy.CAMERA_2])
        ]
        for search in searches:
            events_from_db = self.server.db.search_events(search)
            events_from_client = self.client.search_events(search)
            # Check results based on dictionary equality
            self.assertSequenceEqual(
                list(x.as_dict() for x in events_from_db),
                list(x.as_dict() for x in events_from_client))
