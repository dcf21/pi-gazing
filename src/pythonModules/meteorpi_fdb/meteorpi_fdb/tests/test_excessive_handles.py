__author__ = 'tom'
from unittest import TestCase

import meteorpi_fdb
import meteorpi_fdb.testing.dummy_data as dummy
import os.path as path

DB_PATH_1 = 'localhost:/var/lib/firebird/2.5/data/meteorpi_test1.fdb'
FILE_PATH_1 = path.expanduser("~/meteorpi_test_1_files")
DB_PATH_2 = 'localhost:/var/lib/firebird/2.5/data/meteorpi_test2.fdb'
FILE_PATH_2 = path.expanduser("~/meteorpi_test_2_files")
PORT_1 = 12345


class TestExcessiveHandles(TestCase):
    """
    Test cases to handle export / import functionality in the database
    """

    def __init__(self, *args, **kwargs):
        super(TestExcessiveHandles, self).__init__(*args, **kwargs)
        self.longMessage = True

    def setUp(self):
        """Clear the database and populate it with example contents"""
        self.db = meteorpi_fdb.MeteorDatabase(db_path=DB_PATH_1, file_store_path=FILE_PATH_1)
        self.dummy_helper = dummy.setup_dummy_data(self.db, clear=True)

    def tearDown(self):
        """Stop the server"""

    def test_excessive_handles(self):
        """
        Regression test for https://github.com/camsci/meteor-pi/issues/42
        """
        for x in range(100):
            for x2 in range(1000):
                y = self.db.get_high_water_mark(dummy.CAMERA_1)
            print x
