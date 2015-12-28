__author__ = 'tom'
from unittest import TestCase

import meteorpi_fdb
import meteorpi_model as mp
import meteorpi_fdb.testing.dummy_data as dummy
import os.path as path

DB_PATH_1 = 'localhost:/var/lib/firebird/2.5/data/meteorpi_test1.fdb'
FILE_PATH_1 = path.expanduser("~/meteorpi_test1_files")
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
        self.db = meteorpi_fdb.MeteorDatabase(db_path=DB_PATH_1, file_store_path=FILE_PATH_1)
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

    def test_process_marked_entities(self):
        """
        Mark everything for export, then repeatedly call the get_next_entity_to_export() function, adding the
        corresponding entity to a list and resolving the export by calling set_status(0) on the task object. Should
        iterate cleanly over first files, then events, in the database, marking all for export. Once this is completed
        it checks that marking entities adds no new records.
        """
        file_config = self.db.create_or_update_export_configuration(
            mp.ExportConfiguration(target_url="http://foo/api",
                                   user_id="u",
                                   password="p",
                                   search=mp.FileRecordSearch(),
                                   name="file_search",
                                   description="file_search_desc"))
        self.assertEquals(0, self.db.mark_entities_to_export(file_config))
        file_config.enabled = True
        self.db.create_or_update_export_configuration(file_config)
        self.db.mark_entities_to_export(file_config)
        event_config = self.db.create_or_update_export_configuration(
            mp.ExportConfiguration(target_url="http://foo/api",
                                   user_id="u",
                                   password="p",
                                   search=mp.EventSearch(),
                                   name="event_search",
                                   description="event_search_desc"))
        self.assertEquals(0, self.db.mark_entities_to_export(event_config))
        event_config.enabled = True
        self.db.create_or_update_export_configuration(event_config)
        self.db.mark_entities_to_export(event_config)
        # Should have marked all events and stand-alone files to export
        def task_generator():
            """
            Generator that iterates over any available tasks, exiting once none are left
            """
            while True:
                next_task = self.db.get_next_entity_to_export()
                if next_task is not None:
                    yield next_task
                else:
                    break

        entities = []
        for task in task_generator():
            if isinstance(task, meteorpi_fdb.FileExportTask):
                entities.append(task.get_file())
            elif isinstance(task, meteorpi_fdb.EventExportTask):
                entities.append(task.get_event())
            # Set the task completion flag, should mean that the generator moves on to the
            # next available task.
            task.set_status(0)
        self.assertEquals('f6,f7,f8,f9,f10,f11,e0,e1,e2,e3,e4',
                          self.dummy_helper.seq_to_string_no_sort(entities))
        self.assertEquals(0, self.db.mark_entities_to_export(event_config))
        self.assertEquals(0, self.db.mark_entities_to_export(file_config))
