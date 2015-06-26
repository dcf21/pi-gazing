__author__ = 'tom'

import uuid

import requests
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
        production cases, don't use it outside of test cases.
        """
        while True:
            state = self._handle_next_export()
            if state == "nothing":
                break

    def _handle_next_export(self):
        """
        Process the next export job, if there is one.

        :return:
            A string status describing what happened:

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
        export = self.db.get_next_entity_to_export()
        print "*******"
        if export is not None:
            try:
                print "export : sending export {0}".format(export)
                response = requests.post(url=export.target_url,
                                         json=export.as_dict(),
                                         auth=(export.target_user,
                                               export.target_password))
                response.raise_for_status()
                json = response.json()
                state = json['state']
                if state == 'complete':
                    # Export complete, we have everything we need
                    export.set_status(0)
                    print "export : completed export job"
                    return "complete"
                elif state == 'need_status':
                    # Send the camera status for this entity
                    status_id = json['status_id']
                    print "export : sending camera status with id {0}".format(status_id)
                    status = self.db.get_camera_status_by_id(status_id=uuid.UUID(hex=status_id))
                    requests.post(url=export.target_url,
                                  json={'type': 'status',
                                        'status': status.as_dict()},
                                  auth=(export.target_user,
                                        export.target_password))
                    return "continue"
                elif state == 'need_file_data':
                    # Send the binary data for this file
                    file_id = uuid.UUID(hex=json['file_id'])
                    print "export : sending binary data for file id {0}".format(file_id.hex)
                    file_record = self.db.get_file(file_id=file_id)
                    if file_record is None:
                        return "failed"
                    file_path = self.db.file_path_for_id(file_id)
                    with open(file_path, 'rb') as file_content:
                        m = MultipartEncoder(
                            fields={'file': ('file', file_content, file_record.mime_type)})
                        r = requests.post(url="{0}/data/{1}".format(export.target_url, file_id.hex), data=m,
                                          headers={'Content-Type': m.content_type}, auth=(export.target_user,
                                                                                          export.target_password))
                    return "continue"
                else:
                    return "confused"
            except requests.exceptions.HTTPError:
                return "failed"
        print "export : no task found"
        return "nothing"
