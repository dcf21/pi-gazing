__author__ = 'tom'
from unittest import TestCase

import meteorpi_fdb
import meteorpi_fdb.testing.dummy_data as dummy
import os.path as path
import meteorpi_model as model
import meteorpi_fdb.sql_builder as sql_builder

DB_PATH_1 = 'localhost:/var/lib/firebird/2.5/data/meteorpi_test1.fdb'
FILE_PATH_1 = path.expanduser("~/meteorpi_test1_files")
DEFAULT_PORT = 12345


class TestGeneratorConcurrency(TestCase):
    """
    Test cases to handle concurrent access to generator classes with other operations on the connection
    """

    def __init__(self, *args, **kwargs):
        super(TestGeneratorConcurrency, self).__init__(*args, **kwargs)
        self.longMessage = True

    def setUp(self):
        """Clear the database and populate it with example contents"""
        self.db = meteorpi_fdb.MeteorDatabase(db_path=DB_PATH_1, file_store_path=FILE_PATH_1)
        self.dummy_helper = dummy.setup_dummy_data(self.db, clear=True)

    def tearDown(self):
        """Stop the server"""

    def test_concurrency(self):
        print self.db.generators
        builder = sql_builder.search_files_sql_builder(model.FileRecordSearch())
        sql = builder.get_select_sql(
            columns='f.internalID, f.cameraID, f.mimeType, f.semanticType, f.fileTime, '
                    'f.fileSize, f.fileID, f.fileName, s.statusID, f.md5Hex',
            skip=0, limit=0, order='f.fileTime DESC')
        file_generator = self.db.generators.file_generator(sql=sql, sql_args=[])
        first_file = file_generator.next()
        self.db.search_events(search=model.EventSearch())
        second_file = file_generator.next()
        self.db.create_or_update_user(user_id='new_user', password='new_password', roles=['user'])
        third_file = file_generator.next()
