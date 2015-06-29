import uuid

from yaml import safe_load

import os.path as path
import meteorpi_model as model
from flask.ext.jsonpify import jsonify
from flask import request


def add_routes(meteor_app, url_path='/import'):
    """
    Add two routes to the specified instance of :class:`meteorpi_server.MeteorApp` to implement the import API and allow
    for replication of data to this server.

    :param meteorpi_server.MeteorApp meteor_app:
        The :class:`meteorpi_server.MeteorApp` to which import routes should be added
    :param string url_path:
        The base of the import routes for this application. Defaults to '/import' - routes will be created at this path
        and as import_path/data/<id> for binary data reception. Both paths only respond to POST requests and require
        that the requests are authenticated and that the authenticated user has the 'import' role.
    """
    db = meteor_app.db
    app = meteor_app.app

    @app.route(url_path, methods=['POST'])
    @meteor_app.requires_auth(roles=['import'])
    def import_entities():
        """
        Route used to import :class:`meteorpi_model.FileRecord` and :class:`meteorpi_model.Event` along with any
        necessary :class:`meteorpi_model.CameraStatus` instances required to provide context. Handles negotiation with
        the exporting party to ensure that we have all the required information before adding the entity to our database
        """
        import_request = safe_load(request.get_data())
        type = import_request['type']
        if type == 'file':
            print "import : received file record with id {0}".format(import_request['file']['file_id'])
            status_id = uuid.UUID(hex=import_request['file']['status_id'])
            # Check whether we have an appropriate status block
            camera_status = db.get_camera_status_by_id(status_id)
            if camera_status is None:
                print "import : requesting camera status id {0}".format(status_id)
                return jsonify({'state': 'need_status', 'status_id': status_id.hex})
            # Check whether the file exists on disk
            file_id = uuid.UUID(hex=import_request['file']['file_id'])
            file_path = db.file_path_for_id(file_id)
            if path.isfile(file_path):
                file_record = model.FileRecord.from_dict(import_request['file'])
                db.import_file_record(file_record)
                print "import : completed reception of file with id {0}".format(file_id.hex)
                return jsonify({'state': 'complete'})
            else:
                print "import : requesting data for file with id {0}".format(file_id.hex)
                return jsonify({'state': 'need_file_data', 'file_id': file_id.hex})
        elif type == 'status':
            camera_status = model.CameraStatus.from_dict(import_request['status'])
            print "import : received camera status with id {0}".format(camera_status.status_id.hex)
            if db.get_camera_status_by_id(camera_status.status_id) is None:
                db.import_camera_status(camera_status)
            return jsonify({'state': 'continue'})
        elif type == 'event':
            print "import : received event with id {0}".format(import_request['event']['event_id'])
            status_id = uuid.UUID(hex=import_request['event']['status_id'])
            # Check whether we have an appropriate status block
            camera_status = db.get_camera_status_by_id(status_id)
            if camera_status is None:
                print "import : requesting camera status id {0}".format(status_id)
                return jsonify({'state': 'need_status', 'status_id': status_id.hex})
            event = model.Event.from_dict(import_request['event'])
            for file_record in event.file_records:
                file_path = db.file_path_for_id(file_record.file_id)
                if not path.isfile(file_path):
                    print "import : requesting data for file with id {0} in event {1}".format(file_record.file_id.hex,
                                                                                              event.event_id.hex)
                    return jsonify({'state': 'need_file_data', 'file_id': file_record.file_id.hex})
            # Have all the data, import the event along with its files
            db.import_event(event)
            return jsonify({'state': 'complete'})
        else:
            print "import: failing, unrecognized request"
            return jsonify({'state': 'failed'})

    @app.route('{0}/data/<file_id_hex>'.format(url_path), methods=['POST'])
    @meteor_app.requires_auth(roles=['import'])
    def import_file_data(file_id_hex):
        """
        Receive a file upload, saving it to the file store. Note that no checks are currently made that the file is
        intact.

        :param string file_id_hex:
            The hex representation of the :class:`meteorpi_model.FileRecord` to which this data belongs.
        """
        file_id = uuid.UUID(hex=file_id_hex)
        file = request.files['file']
        if file:
            file.save(db.file_path_for_id(file_id))
        return jsonify({'state': 'continue'})
