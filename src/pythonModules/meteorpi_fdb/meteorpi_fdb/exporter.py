from uuid import UUID
from logging import getLogger
from contextlib import closing

from requests import post
from requests.exceptions import HTTPError, ConnectionError
from requests_toolbelt.multipart.encoder import MultipartEncoder
from apscheduler.schedulers.background import BackgroundScheduler


class MeteorExporter(object):
    """
    Manages the communication part of MeteorPi's export mechanism, acquiring :class:`meteorpi_fdb.FileExportTask` and
    :class:`meteorpi_fdb.EventExportTask` instances from the database and sending them on to the appropriate receiver.
    This class in effect defines the communication protocol used by this process.

    The scheduler defined by default will also handle back-off under failure conditions. If an export fails, the count
    of failures (since the server was started) for that export config will be incremented and all export tasks for that
    config will be pushed a configurable distance into the future. If it fails more than a certain number of times the
    config will be marked as disabled. Any successful export will reset the failure count.

    :ivar scheduler:
        An instance of :class:`apscheduler.schedulers.background.BackgroundScheduler` used to schedule regular mark of
        entities to export and trigger the actual export of such entities.
    """

    def __init__(self, db, mark_interval_seconds=300, max_failures_before_disable=4, defer_on_failure_seconds=1800,
                 scheduler=None):
        """
        Build a new MeteorExporter. The export process won't run by default, you must call the appropriate methods on
        this object to actually start exporting. A scheduler is created to handle automated, regular, exports, but is
        not started, you must explicitly call its start method if you want regular exports to function.

        :param MeteorDatabase db:
            The database to read from, for both entities under replication and the export configurations.
        :param int mark_interval_seconds:
            The number of seconds after finishing on mark / export round that the next one will be triggered. Defaults
            to 300 for a five minute break. Note that at the end of an export round the process is re-run immediately,
            only finishing when there was nothing to do. This means that if we have a lot of data generated during an
            export run we won't wait another five minutes before we process the new data.
        :param int defer_on_failure_seconds:
            The number of seconds into the future which will be applied to any tasks pending for a given config when
            a task created by that config fails (including the failed task). The timestamp for any tasks with timestamps
            less than now + defer_on_failure_seconds will be set to now + defer_on_failure_seconds.
        :param scheduler:
            The scheduler to use, defaults to a BackgroundScheduler with a non-daemon thread if not specified. Use a
            blocking one for test purposes.
        :param int max_failures_before_disable:
            The number of times an export configuration can have its exports fail before it is disabled.
        """
        self.db = db
        if scheduler is None:
            scheduler = BackgroundScheduler(daemon=False)
        self.scheduler = scheduler
        job_id = "meteorpi_export"
        failure_counts = {}
        logger = getLogger("meteorpi.db.export")

        def scheduled_export():
            self.scheduler.pause_job(job_id=job_id)
            job_count = -1
            try:
                while job_count != 0:
                    # Mark any new entities for export
                    for export_config in db.get_export_configurations():
                        if export_config.enabled:
                            db.mark_entities_to_export(export_config)
                            logger.info("Marked entities to export for config id {0}".format(export_config.config_id))
                    job_count = 0
                    while True:
                        state = self.handle_next_export()
                        if state is None:
                            # No jobs were processed on this tick, break out to the next control layer
                            break
                        elif state.state == "failed" or state.state == "confused":
                            config_id = state.config_id
                            job_count += 1
                            # Handle failure
                            export_config = db.get_export_configuration(config_id=config_id)
                            failure_count = failure_counts.pop(config_id, 0) + 1
                            logger.info(
                                "Failure for {0}, previous failure count was {1}".format(config_id, failure_count))
                            if failure_count >= max_failures_before_disable:
                                # Disable this config
                                export_config = db.get_export_configuration(config_id=config_id)
                                export_config.enabled = False
                                db.create_or_update_export_configuration(export_config)
                                # Doesn't add the failure count back in, as we want to be able to run should the user
                                # re-enable this export configuration
                            else:
                                # Defer entries created by this config
                                failure_counts[config_id] = failure_count
                                db.defer_export_tasks(config_id=config_id, seconds=defer_on_failure_seconds)
                        else:
                            config_id = state.config_id
                            job_count += 1
                            # Reset failure count for this config, as we just exported something with it
                            failure_counts.pop(config_id, None)
            finally:
                self.scheduler.resume_job(job_id=job_id)

        self.scheduler.add_job(id=job_id, func=scheduled_export, trigger="interval", seconds=mark_interval_seconds)

    def handle_next_export(self):
        """
        Retrieve and fully evaluate the next export task, including resolution of any sub-tasks requested by the
        import client such as requests for binary data, camera status etc.

        :return:
            An instance of ExportStateCache, the 'state' field contains the state of the export after running as many
            sub-tasks as required until completion or failure. If there were no jobs to run this returns None.

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
                return None
            elif state.export_task is None:
                return state

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
        except ConnectionError:
            return export_state.failed()

    class ExportStateCache(object):
        """
        Used as a continuation when processing a multi-stage export. On sub-task completion, if the export_task is set
        to None this is an indication that the task is completed (whether this means it's failed or succeeded, there's
        nothing left to do).
        """

        def __init__(self, export_task, state="not_started"):
            if export_task is None:
                raise ValueError("Export task cannot be none, must be specified on creation")
            self.state = state
            self.export_task = export_task
            self.config_id = export_task.config_id
            self.use_cache = False
            self.entity_dict = export_task.as_dict()
            self.entity_id = export_task.get_entity_id().hex

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


class EventExportTask(object):
    """
    Represents a single active Event export, providing methods to get the underlying :class:`meteorpi_model.Event`,
    the :class:`meteorpi_model.ExportConfiguration` and to update the completion state in the database.
    """

    def __init__(self, db, config_id, config_internal_id, event_id, event_internal_id, timestamp, status, target_url,
                 target_user, target_password):
        self.db = db
        self.config_id = config_id
        self.config_internal_id = config_internal_id
        self.event_id = event_id
        self.event_internal_id = event_internal_id
        self.timestamp = timestamp
        self.status = status
        self.target_url = target_url
        self.target_user = target_user
        self.target_password = target_password

    def get_event(self):
        return self.db.get_event(self.event_id)

    def get_export_config(self):
        return self.db.get_export_configuartion(self.config_id)

    def as_dict(self):
        return {
            'type': 'event',
            'event': self.get_event().as_dict()
        }

    def get_entity_id(self):
        return self.event_id

    def set_status(self, status):
        with closing(self.db.con.cursor()) as cur:
            cur.execute('UPDATE t_eventExport x '
                        'SET x.exportState = (?) '
                        'WHERE x.eventID = (?) AND x.exportConfig = (?)',
                        (status, self.event_internal_id, self.config_internal_id))
        self.db.con.commit()


class FileExportTask(object):
    """
    Represents a single active FileRecord export, providing methods to get the underlying
    :class:`meteorpi_model.FileRecord`, the :class:`meteorpi_model.ExportConfiguration` and to update the completion
    state in the database.
    """

    def __init__(self, db, config_id, config_internal_id, file_id, file_internal_id, timestamp, status, target_url,
                 target_user, target_password):
        self.db = db
        self.config_id = config_id
        self.config_internal_id = config_internal_id
        self.file_id = file_id
        self.file_internal_id = file_internal_id
        self.timestamp = timestamp
        self.status = status
        self.target_url = target_url
        self.target_user = target_user
        self.target_password = target_password

    def get_file(self):
        return self.db.get_file(self.file_id)

    def get_export_config(self):
        return self.db.get_export_configuartion(self.config_id)

    def get_entity_id(self):
        return self.file_id

    def as_dict(self):
        return {
            'type': 'file',
            'file': self.get_file().as_dict()
        }

    def set_status(self, status):
        with closing(self.db.con.cursor()) as cur:
            cur.execute('UPDATE t_fileExport x '
                        'SET x.exportState = (?) '
                        'WHERE x.fileID = (?) AND x.exportConfig = (?)',
                        (status, self.file_internal_id, self.config_internal_id))
        self.db.con.commit()
