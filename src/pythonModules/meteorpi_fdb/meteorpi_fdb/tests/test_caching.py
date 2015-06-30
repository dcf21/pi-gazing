__author__ = 'tom'
from unittest import TestCase
import time

import meteorpi_fdb
import meteorpi_fdb.testing.dummy_data as dummy
import os.path as path
import meteorpi_model as model

DB_PATH_1 = 'localhost:/var/lib/firebird/2.5/data/meteorpi_test1.fdb'
FILE_PATH_1 = path.expanduser("~/meteorpi_test1_files")
DEFAULT_PORT = 12345


def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()

        print '%r (%r, %r) %2.2f sec' % \
              (method.__name__, args, kw, te - ts)
        return result

    return timed


class TestCaching(TestCase):
    """
    Test cases to handle export / import functionality in the database
    """

    def __init__(self, *args, **kwargs):
        super(TestCaching, self).__init__(*args, **kwargs)
        self.longMessage = True

    def setUp(self):
        """Clear the database and populate it with example contents"""
        self.db = meteorpi_fdb.MeteorDatabase(db_path=DB_PATH_1, file_store_path=FILE_PATH_1)
        self.dummy_helper = dummy.setup_dummy_data(self.db, clear=True)

    def tearDown(self):
        """Stop the server"""

    @timeit
    def test_event_cache(self):
        for n in range(0, 1000):
            result = list(self.db.search_events(model.EventSearch()))
        print self.db.generators.cache_info()