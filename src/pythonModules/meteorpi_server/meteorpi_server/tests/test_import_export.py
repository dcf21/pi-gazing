from unittest import TestCase
import logging
import time

import os.path as path
import meteorpi_server
import meteorpi_fdb
import meteorpi_fdb.exporter
import meteorpi_model as model
import meteorpi_fdb.testing.dummy_data as dummy

DB_PATH_1 = 'localhost:/var/lib/firebird/2.5/data/meteorpi_test1.fdb'
FILE_PATH_1 = path.expanduser("~/meteorpi_test1_files")
DB_PATH_2 = 'localhost:/var/lib/firebird/2.5/data/meteorpi_test2.fdb'
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
        self.source_db = meteorpi_fdb.MeteorDatabase(db_path=DB_PATH_2, file_store_path=FILE_PATH_2)
        self.exporter = meteorpi_fdb.exporter.MeteorExporter(db=self.source_db, mark_interval_seconds=1,
                                                             max_failures_before_disable=4, defer_on_failure_seconds=3)

    def setUp(self):
        """
        Clear the target database, populate the source one with dummy data. Starts up the server for the target database
        and set a function which can be used to stop it in the teardown.
        """
        dummy.setup_dummy_data(self.source_db, clear=True)
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

    def test_send_files(self):
        config = self.source_db.create_or_update_export_configuration(
            model.ExportConfiguration(target_url="http://localhost:12345/import",
                                      user_id="import_user",
                                      password="import_password",
                                      search=model.FileRecordSearch(),
                                      name="file_search",
                                      description="file_search_desc"))
        config.enabled = True
        self.source_db.create_or_update_export_configuration(config)
        self.source_db.mark_entities_to_export(config)
        export_all_the_things(self.exporter)

    def test_send_events(self):
        config = self.source_db.create_or_update_export_configuration(
            model.ExportConfiguration(target_url="http://localhost:12345/import",
                                      user_id="import_user",
                                      password="import_password",
                                      search=model.EventSearch(),
                                      name="event_search",
                                      description="event_search_desc"))
        config.enabled = True
        self.source_db.create_or_update_export_configuration(config)
        self.source_db.mark_entities_to_export(config)
        export_all_the_things(self.exporter)

    def test_send_everything(self):
        event_config = self.source_db.create_or_update_export_configuration(
            model.ExportConfiguration(target_url="http://localhost:12345/import",
                                      user_id="import_user",
                                      password="import_password",
                                      search=model.EventSearch(),
                                      name="event_search",
                                      description="event_search_desc"))
        event_config.enabled = True
        self.source_db.create_or_update_export_configuration(event_config)
        self.source_db.mark_entities_to_export(event_config)
        file_config = self.source_db.create_or_update_export_configuration(
            model.ExportConfiguration(target_url="http://localhost:12345/import",
                                      user_id="import_user",
                                      password="import_password",
                                      search=model.FileRecordSearch(),
                                      name="file_search",
                                      description="file_search_desc"))
        file_config.enabled = True
        self.source_db.create_or_update_export_configuration(file_config)
        self.source_db.mark_entities_to_export(file_config)
        export_all_the_things(self.exporter)

    def test_send_on_schedule(self):
        self.exporter.scheduler.start()
        event_config = self.source_db.create_or_update_export_configuration(
            model.ExportConfiguration(target_url="http://localhost:12345/import",
                                      user_id="import_user",
                                      password="import_password",
                                      search=model.EventSearch(),
                                      name="event_search",
                                      description="event_search_desc"))
        event_config.enabled = True
        self.source_db.create_or_update_export_configuration(event_config)
        time.sleep(6)
        file_config = self.source_db.create_or_update_export_configuration(
            model.ExportConfiguration(target_url="http://localhost:12345/import",
                                      user_id="import_user",
                                      password="import_password",
                                      search=model.FileRecordSearch(),
                                      name="file_search",
                                      description="file_search_desc"))
        file_config.enabled = True
        self.source_db.create_or_update_export_configuration(file_config)
        time.sleep(10)
        self.exporter.scheduler.shutdown()
