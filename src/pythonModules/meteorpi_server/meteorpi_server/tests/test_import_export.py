from unittest import TestCase
import logging
import time

import os.path as path
import meteorpi_server
import meteorpi_db
import meteorpi_db.exporter
import meteorpi_model as model
import meteorpi_db.testing.dummy_data as dummy

DB_PATH_1 = 'localhost:/var/lib/firebird/2.5/data/meteorpi_test1.db'
FILE_PATH_1 = path.expanduser("~/meteorpi_test1_files")
DB_PATH_2 = 'localhost:/var/lib/firebird/2.5/data/meteorpi_test2.db'
FILE_PATH_2 = path.expanduser("~/meteorpi_test2_files")
PORT_1 = 12345

# Logs on INFO to signal completion, DEBUG to show all messages
logging.getLogger("meteorpi.server.import").setLevel(logging.INFO)
logging.getLogger("meteorpi.db.export").setLevel(logging.INFO)


def export_all_the_things(exporter):
    """
    Process export jobs until we get a response of 'nothing'. This is overly naive and will certainly not work in
    production, don't use it outside of test suites.
    """
    while True:
        state = exporter.handle_next_export()
        if state is None:
            break


class TestImportExport(TestCase):
    """
    Test suite to exercise export / import functionality
    """

    def __init__(self, *args, **kwargs):
        """
        Set up a target database with an API server running on top of it, and a source database which will be populated
        with dummy data which can be exported to the target.
        """
        super(TestImportExport, self).__init__(*args, **kwargs)
        self.server = meteorpi_server.MeteorServer(db_path=DB_PATH_1, file_store_path=FILE_PATH_1, port=PORT_1)
        self.target_db = self.server.db
        self.source_db = meteorpi_db.MeteorDatabase(db_path=DB_PATH_2, file_store_path=FILE_PATH_2)
        self.exporter = meteorpi_db.exporter.MeteorExporter(db=self.source_db, mark_interval_seconds=1,
                                                             max_failures_before_disable=4, defer_on_failure_seconds=3)

    def setUp(self):
        """
        Clear the target database, populate the source one with dummy data. Starts up the server for the target database
        and set a function which can be used to stop it in the teardown.
        """
        self.dummy_helper = dummy.setup_dummy_data(self.source_db, clear=True)
        self.target_db.clear_database()
        # Set up a user for import on the target
        self.target_db.create_or_update_user(user_id="import_user", password="import_password", roles=["import"])
        # Start the server, returns a function
        # which can be used to stop it afterwards
        self.stop = self.server.start_non_blocking()

    def tearDown(self):
        """Stop the server and clear the databases"""
        self.stop()
        self.stop = None
        # self.target_db.clear_database()
        # self.source_db.clear_database()

    def events_in_db(self, db=None):
        if db is None:
            db = self.target_db
        return self.dummy_helper.seq_to_string(
            db.search_events(search=model.EventSearch())['events'])

    def files_in_db(self, db=None):
        if db is None:
            db = self.target_db
        return self.dummy_helper.seq_to_string(
            db.search_files(search=model.FileRecordSearch())['files'])

    def test_send_files(self):
        config = self.source_db.create_or_update_export_configuration(
            model.ExportConfiguration(target_url="http://localhost:12345/import",
                                      user_id="import_user",
                                      password="import_password",
                                      search=model.FileRecordSearch(),
                                      name="file_search",
                                      description="file_search_desc",
                                      enabled=True))
        self.source_db.mark_entities_to_export(config)
        export_all_the_things(self.exporter)
        self.assertEqual(self.files_in_db(), 'f10,f11,f6,f7,f8,f9')

    def test_send_events(self):
        config = self.source_db.create_or_update_export_configuration(
            model.ExportConfiguration(target_url="http://localhost:12345/import",
                                      user_id="import_user",
                                      password="import_password",
                                      search=model.EventSearch(),
                                      name="event_search",
                                      description="event_search_desc",
                                      enabled=True))
        self.source_db.mark_entities_to_export(config)
        export_all_the_things(self.exporter)
        self.assertEqual(self.events_in_db(db=self.source_db), self.events_in_db(db=self.target_db))
        self.assertEqual(self.files_in_db(), 'e0:f0,e0:f1,e1:f0,e1:f1,e1:f2,'
                                             'e1:f3,e2:f0,e2:f1,e3:f0,e3:f1,'
                                             'e3:f2,e4:f0,e4:f1,e4:f2,e4:f3,'
                                             'e4:f4,e4:f5')

    def test_send_everything(self):
        event_config = self.source_db.create_or_update_export_configuration(
            model.ExportConfiguration(target_url="http://localhost:12345/import",
                                      user_id="import_user",
                                      password="import_password",
                                      search=model.EventSearch(),
                                      name="event_search",
                                      description="event_search_desc",
                                      enabled=True))
        self.source_db.mark_entities_to_export(event_config)
        file_config = self.source_db.create_or_update_export_configuration(
            model.ExportConfiguration(target_url="http://localhost:12345/import",
                                      user_id="import_user",
                                      password="import_password",
                                      search=model.FileRecordSearch(),
                                      name="file_search",
                                      description="file_search_desc",
                                      enabled=True))
        self.source_db.mark_entities_to_export(file_config)
        export_all_the_things(self.exporter)
        self.assertEqual(self.events_in_db(db=self.source_db), self.events_in_db(db=self.target_db))
        self.assertEqual(self.files_in_db(db=self.source_db), self.files_in_db(db=self.target_db))

    def test_send_on_schedule(self):
        self.exporter.scheduler.start()
        self.source_db.create_or_update_export_configuration(
            model.ExportConfiguration(target_url="http://localhost:12345/import",
                                      user_id="import_user",
                                      password="import_password",
                                      search=model.EventSearch(),
                                      name="event_search",
                                      description="event_search_desc",
                                      enabled=True))
        time.sleep(6)
        self.assertEqual(self.events_in_db(db=self.source_db), self.events_in_db(db=self.target_db))
        self.assertEqual(self.files_in_db(), 'e0:f0,e0:f1,e1:f0,e1:f1,e1:f2,'
                                             'e1:f3,e2:f0,e2:f1,e3:f0,e3:f1,'
                                             'e3:f2,e4:f0,e4:f1,e4:f2,e4:f3,'
                                             'e4:f4,e4:f5')
        self.source_db.create_or_update_export_configuration(
            model.ExportConfiguration(target_url="http://localhost:12345/import",
                                      user_id="import_user",
                                      password="import_password",
                                      search=model.FileRecordSearch(),
                                      name="file_search",
                                      description="file_search_desc",
                                      enabled=True))
        time.sleep(10)
        self.assertEqual(self.events_in_db(db=self.source_db), self.events_in_db(db=self.target_db))
        self.assertEqual(self.files_in_db(db=self.source_db), self.files_in_db(db=self.target_db))
        self.exporter.scheduler.shutdown()
