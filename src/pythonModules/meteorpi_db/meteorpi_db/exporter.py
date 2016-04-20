# exporter.py

# -------------------------------------------------
# Copyright 2016 Cambridge Science Centre.

# This file is part of Meteor Pi.

# Meteor Pi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Meteor Pi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Meteor Pi.  If not, see <http://www.gnu.org/licenses/>.
# -------------------------------------------------

# Functions which export database objects to an external server

import traceback
from requests import post
from requests.exceptions import HTTPError, ConnectionError
from requests_toolbelt.multipart.encoder import MultipartEncoder


class MeteorExporter(object):
    """
    Manages the communication part of Meteor Pi's export mechanism, acquiring :class:`meteorpi_db.FileExportTask` and
    :class:`meteorpi_db.EventExportTask` instances from the database and sending them on to the appropriate receiver.
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

    def handle_next_export(self):
        """
        Retrieve and fully evaluate the next export task, including resolution of any sub-tasks requested by the
        import client such as requests for binary data, observation, etc.

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

        :param ExportState export_state:
            If provided, this is used instead of the database queue, in effect directing the exporter to process the
            previous export again. This is used to avoid having to query the database when we know already what needs
            to be done. It also maintains a cache of the entity so we don't have to re-acquire it on multiple exports.
        :return:
            A :class:`meteorpi_db.exporter.MeteorExporter.ExportStateCache` representing the state of the export, or
            None if there was nothing to do.
        """
        # Use a cached state, or generate a new one if required
        if export_state is None or export_state.export_task is None:
            export = self.db.get_next_entity_to_export()
            if export is not None:
                export_state = self.ExportState(export_task=export)
            else:
                return None
        try:
            auth = (export_state.export_task.target_user,
                    export_state.export_task.target_password)
            target_url = export_state.export_task.target_url
            response = post(url=target_url, verify=False,
                            json=export_state.entity_dict,
                            auth=auth)
            response.raise_for_status()
            json = response.json()
            state = json['state']
            if state == 'complete':
                return export_state.fully_processed()
            elif state == 'need_file_data':
                file_id = json['file_id']
                file_record = self.db.get_file(repository_fname=file_id)
                if file_record is None:
                    return export_state.failed()
                with open(self.db.file_path_for_id(file_id), 'rb') as file_content:
                    multi = MultipartEncoder(fields={'file': ('file', file_content, file_record.mime_type)})
                    post(url="{0}/data/{1}/{2}".format(target_url, file_id, file_record.file_md5),
                         data=multi, verify=False,
                         headers={'Content-Type': multi.content_type},
                         auth=auth)
                return export_state.partially_processed()
            elif state == 'continue':
                return export_state.partially_processed()
            else:
                return export_state.confused()
        except HTTPError:
            traceback.print_exc()
            return export_state.failed()
        except ConnectionError:
            traceback.print_exc()
            return export_state.failed()

    class ExportState(object):
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
            self.entity_dict = export_task.as_dict()
            self.entity_id = export_task.get_entity_id()

        def fully_processed(self):
            self.state = "complete"
            self.export_task.set_status(0)
            self.export_task = None
            self.entity_dict = None
            return self

        def partially_processed(self):
            self.state = "partial"
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


class ObservationExportTask(object):
    """
    Represents a single active Observation export, providing methods to get the underlying
    :class:`meteorpi_model.Observation`, the :class:`meteorpi_model.ExportConfiguration` and to update the completion
    state in the database.
    """

    def __init__(self, db, config_id, observation_id, status, target_url, target_user, target_password):
        self.db = db
        self.config_id = config_id
        self.observation_id = observation_id
        self.status = status
        self.target_url = target_url
        self.target_user = target_user
        self.target_password = target_password

    def get_observation(self):
        return self.db.get_observation(self.observation_id)

    def get_export_config(self):
        return self.db.get_export_configuartion(self.config_id)

    def as_dict(self):
        return {
            'type': 'observation',
            'observation': self.get_observation().as_dict()
        }

    def get_entity_id(self):
        return self.observation_id

    def set_status(self, status):
        self.db.con.execute('UPDATE archive_observationExport x '
                            'SET x.exportState = %s '
                            'WHERE x.observationId = (SELECT uid FROM archive_observations o WHERE o.publicId=%s) '
                            'AND x.exportConfig = (SELECT uid FROM archive_exportConfig o WHERE o.exportConfigId=%s) ',
                            (status, self.observation_id, self.config_id))


class FileExportTask(object):
    """
    Represents a single active FileRecord export, providing methods to get the underlying
    :class:`meteorpi_model.FileRecord`, the :class:`meteorpi_model.ExportConfiguration` and to update the
    completion state in the database.
    """

    def __init__(self, db, config_id, file_id, status, target_url, target_user, target_password):
        self.db = db
        self.config_id = config_id
        self.file_id = file_id
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
        self.db.con.execute('UPDATE archive_fileExport x '
                            'SET x.exportState = %s '
                            'WHERE x.fileId = (SELECT uid FROM archive_files o WHERE o.repositoryFname=%s) '
                            'AND x.exportConfig = (SELECT uid FROM archive_exportConfig o WHERE o.exportConfigId=%s) ',
                            (status, self.file_id, self.config_id))


class MetadataExportTask(object):
    """
    Represents a single active ObservatoryMetadata export, providing methods to get the underlying
    :class:`meteorpi_model.ObservatoryMetadata`, the :class:`meteorpi_model.ExportConfiguration` and to update the
    completion state in the database.
    """

    def __init__(self, db, config_id, metadata_id, status, target_url, target_user, target_password):
        self.db = db
        self.config_id = config_id
        self.metadata_id = metadata_id
        self.status = status
        self.target_url = target_url
        self.target_user = target_user
        self.target_password = target_password

    def get_metadata(self):
        return self.db.get_obstory_metadata(self.metadata_id)

    def get_export_config(self):
        return self.db.get_export_configuartion(self.config_id)

    def get_entity_id(self):
        return self.metadata_id

    def as_dict(self):
        return {
            'type': 'metadata',
            'metadata': self.get_metadata().as_dict()
        }

    def set_status(self, status):
        self.db.con.execute('UPDATE archive_metadataExport x '
                            'SET x.exportState = %s '
                            'WHERE x.metadataId = (SELECT uid FROM archive_metadata o WHERE o.publicId=%s) '
                            'AND x.exportConfig = (SELECT uid FROM archive_exportConfig o WHERE o.exportConfigId=%s) ',
                            (status, self.metadata_id, self.config_id))
