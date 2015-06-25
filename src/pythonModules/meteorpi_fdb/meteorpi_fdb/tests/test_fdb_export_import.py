__author__ = 'tom'
from unittest import TestCase

import meteorpi_fdb
import meteorpi_model as mp
import meteorpi_fdb.testing.dummy_data as dummy
import os.path as path

DEFAULT_DB_PATH = 'localhost:/var/lib/firebird/2.5/data/meteorpi.fdb'
DEFAULT_FILE_PATH = path.expanduser("~/meteorpi_files")
DEFAULT_PORT = 12345


class TestFdbExportImport(TestCase):
    """
    Test cases to handle export / import functionality in the database
    """

    def __init__(self, *args, **kwargs):
        super(TestFdbExportImport, self).__init__(*args, **kwargs)
        self.longMessage = True

    def setUp(self):
        """Clear the database and populate it with example contents"""
        self.db = meteorpi_fdb.MeteorDatabase(db_path=DEFAULT_DB_PATH, file_store_path=DEFAULT_FILE_PATH)
        self.dummy_helper = dummy.setup_dummy_data(self.db, clear=True)

    def tearDown(self):
        """Stop the server"""

    def test_round_trip_file_export_configuration(self):
        search = mp.FileRecordSearch()
        config = mp.ExportConfiguration(target_url="http://import.service/api", user_id="user", password="password",
                                        search=search, name="My new search", description="Some kind of import thingy")
        self.db.create_or_update_export_configuration(export_config=config)
        config2 = self.db.get_export_configuration(config_id=config.config_id)
        self.assertDictEqual(config.as_dict(), config2.as_dict())
        self.assertEquals(len(self.db.get_export_configurations()), 1)
        self.db.delete_export_configuration(config_id=config.config_id)
        self.assertEquals(len(self.db.get_export_configurations()), 0)

    def test_round_trip_event_export_configuration(self):
        search = mp.EventSearch()
        config = mp.ExportConfiguration(target_url="http://import.service/api", user_id="user", password="password",
                                        search=search, name="My new search", description="Some kind of import thingy")
        self.db.create_or_update_export_configuration(export_config=config)
        config2 = self.db.get_export_configuration(config_id=config.config_id)
        self.assertDictEqual(config.as_dict(), config2.as_dict())
        self.assertEquals(len(self.db.get_export_configurations()), 1)
        self.db.delete_export_configuration(config_id=config.config_id)
        self.assertEquals(len(self.db.get_export_configurations()), 0)

    def test_mark_all_events(self):
        config = self.db.create_or_update_export_configuration(
            mp.ExportConfiguration(target_url="http://foo/api",
                                   user_id="u",
                                   password="p",
                                   search=mp.EventSearch(),
                                   name="event_search",
                                   description="event_search_desc"))
        self.assertEquals(0, self.db.mark_entities_to_export(config))
        config.enabled = True
        self.db.create_or_update_export_configuration(config)
        self.assertEquals(5, self.db.mark_entities_to_export(config))
        self.assertEquals(0, self.db.mark_entities_to_export(config))

    def test_mark_all_files(self):
        config = self.db.create_or_update_export_configuration(
            mp.ExportConfiguration(target_url="http://foo/api",
                                   user_id="u",
                                   password="p",
                                   search=mp.FileRecordSearch(),
                                   name="file_search",
                                   description="file_search_desc"))
        self.assertEquals(0, self.db.mark_entities_to_export(config))
        config.enabled = True
        self.db.create_or_update_export_configuration(config)
        self.assertEquals(6, self.db.mark_entities_to_export(config))
        self.assertEquals(0, self.db.mark_entities_to_export(config))