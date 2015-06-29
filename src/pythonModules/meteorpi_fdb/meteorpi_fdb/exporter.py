from uuid import UUID

from requests import post
from requests.exceptions import HTTPError
from requests_toolbelt.multipart.encoder import MultipartEncoder


class MeteorExporter(object):
    """
    Manages the communication part of MeteorPi's export mechanism, acquiring :class:`meteorpi_fdb.FileExportTask` and
    :class:`meteorpi_fdb.EventExportTask` instances from the database and sending them on to the appropriate receiver.
    This class in effect defines the communication protocol used by this process.
    """

    def __init__(self, db):
        """
        Build a new MeteorExporter. The export process won't run by default, you must call the appropriate methods on
        this object to actually start exporting.

        :param MeteorDatabase db:
            The database to read from, for both entities under replication and the export configurations.

        """
        self.db = db

    def export_all_the_things(self):
        """
        Process export jobs until we get a response of 'nothing'. This is overly naive and will certainly not work in
        production, don't use it outside of test suites.
        """
        while True:
            result = self.handle_next_export()
            if result == "nothing":
                break

    def handle_next_export(self):
        """
        Retrieve and fully evaluate the next export task, including resolution of any sub-tasks requested by the
        import client such as requests for binary data, camera status etc.

        :return:
            A string describing the result of the last export, the result can take the following values:

                :nothing:
                    There was no pending export job in the queue
                :complete:
                    A job was processed and completed. The job has been marked as complete in the database
                :continue:
                    A job was processed, more information was requested and sent, but the job is still active
                :failed:
                    A job was processed but an error occurred during processing
                :confused:
                    A job was processed, but the importer returned a response which we couldn't recognise
        """
        state = None
        while True:
            state = self._handle_next_export_subtask(export_state=state)
            if state is None:
                return "nothing"
            elif state.export_task is None:
                return state.state

    def _handle_next_export_subtask(self, export_state=None):
        """
        Process the next export sub-task, if there is one.

        :param ExportStateCache previous_export_response:
            If provided, this is used instead of the database queue, in effect directing the exporter to process the
            previous export again. This is used to avoid having to query the database when we know already what needs
            to be done. It also maintains a cache of the entity so we don't have to re-acquire it on multiple exports.
        :return:
            A :class:`meteorpi_fdb.exporter.MeteorExporter.ExportStateCache` representing the state of the export, or
            None if there was nothing to do.
        """
        # Use a cached state, or generate a new one if required
        if export_state is None or export_state.export_task is None:
            export = self.db.get_next_entity_to_export()
            if export is not None:
                export_state = self.ExportStateCache(export_task=export)
            else:
                return None
        try:
            auth = (export_state.export_task.target_user,
                    export_state.export_task.target_password)
            target_url = export_state.export_task.target_url
            if export_state.use_cache:
                response = post(url=target_url,
                                json={'type': 'cached_entity',
                                      'cached_entity_id': export_state.entity_id},
                                auth=auth)
            else:
                response = post(url=target_url,
                                json=export_state.entity_dict,
                                auth=auth)
            response.raise_for_status()
            json = response.json()
            state = json['state']
            if state == 'complete':
                return export_state.fully_processed()
            elif state == 'need_status':
                status_id = UUID(hex=json['status_id'])
                camera_status = self.db.get_camera_status_by_id(status_id)
                if camera_status is None:
                    return export_state.failed()
                post(url=target_url,
                     json={'type': 'status',
                           'status': camera_status.as_dict()},
                     auth=auth)
                return export_state.partially_processed()
            elif state == 'need_file_data':
                file_id = UUID(hex=json['file_id'])
                file_record = self.db.get_file(file_id=file_id)
                if file_record is None:
                    return export_state.failed()
                with open(self.db.file_path_for_id(file_id), 'rb') as file_content:
                    multi = MultipartEncoder(fields={'file': ('file', file_content, file_record.mime_type)})
                    post(url="{0}/data/{1}".format(target_url, file_id.hex),
                         data=multi,
                         headers={'Content-Type': multi.content_type},
                         auth=auth)
                return export_state.partially_processed()
            elif state == 'continue':
                return export_state.partially_processed()
            elif state == 'continue-nocache':
                return export_state.partially_processed(use_cache=False)
            else:
                return export_state.confused()
        except HTTPError:
            return export_state.failed()

    class ExportStateCache(object):
        """
        Used as a continuation when processing a multi-stage export. On sub-task completion, if the export_task is set
        to None this is an indication that the task is completed (whether this means it's failed or succeeded, there's
        nothing left to do).
        """

        def __init__(self, state=None, export_task=None):
            self.state = state
            self.export_task = export_task
            self.use_cache = False
            if export_task is not None:
                self.entity_dict = export_task.as_dict()
                self.entity_id = export_task.get_entity_id().hex
            else:
                self.entity_dict = None

        def fully_processed(self):
            self.state = "complete"
            self.export_task.set_status(0)
            self.export_task = None
            self.entity_dict = None
            return self

        def partially_processed(self, use_cache=True):
            self.state = "partial"
            self.use_cache = use_cache
            return self

        def failed(self):
            self.state = "failed"
            self.export_task = None
            self.entity_dict = None
            return self

        def confused(self):
            self.state = "confused"
            self.export_task = None
            self.entity_dict = None
            return self
