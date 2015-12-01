import mimetypes
import os
import re
from uuid import UUID
from urllib import unquote
from yaml import safe_load
import meteorpi_model as model
from flask.ext.jsonpify import jsonify
from flask import request, send_file, Response


@app.after_request
def after_request(response):
    response.headers.add('Accept-Ranges', 'bytes')
    return response


def add_routes(meteor_app, url_path=''):
    """
    Adds search and retrieval routes to a :class:`meteorpi_server.MeteorServer` instance

    :param MeteorApp meteor_app:
        The :class:`meteorpi_server.MeteorApp` to which routes should be added
    :param string url_path:
        The base path used for the query routes, defaults to ''
    """
    from meteorpi_server import MeteorApp

    db = meteor_app.db
    app = meteor_app.app

    @app.route('{0}/cameras'.format(url_path), methods=['GET'])
    def get_active_cameras():
        cameras = db.get_cameras()
        return jsonify({'cameras': cameras})

    @app.route('{0}/cameras/<camera_id>/status'.format(url_path), methods=['GET'])
    def get_current_camera_status(camera_id):
        status = db.get_camera_status(camera_id=camera_id)
        if status is None:
            return 'No active camera with ID {0}'.format(camera_id), 404
        else:
            return jsonify({'status': status.as_dict()})

    @app.route('{0}/cameras/<camera_id>/status/<time_string>'.format(url_path), methods=['GET'])
    def get_camera_status(camera_id, time_string):
        status = db.get_camera_status(camera_id=camera_id, time=model.milliseconds_to_utc_datetime(int(time_string)))
        if status is None:
            return 'No active camera with ID {0}'.format(camera_id), 404
        else:
            return jsonify({'status': status.as_dict()})

    @app.route('{0}/events/<search_string>'.format(url_path), methods=['GET'], strict_slashes=True)
    def search_events(search_string):
        search = model.EventSearch.from_dict(safe_load(unquote(search_string)))
        events = db.search_events(search)
        return jsonify({'events': list(x.as_dict() for x in events['events']), 'count': events['count']})

    @app.route('{0}/files/<search_string>'.format(url_path), methods=['GET'])
    def search_files(search_string):
        # print search_string
        search = model.FileRecordSearch.from_dict(safe_load(unquote(search_string)))
        files = db.search_files(search)
        return jsonify({'files': list(x.as_dict() for x in files['files']), 'count': files['count']})

    @app.route('{0}/files/content/<file_id>/<file_name>'.format(url_path), methods=['GET'])
    @app.route('{0}/files/content/<file_id>'.format(url_path), methods=['GET'])
    def get_file_content(file_id, file_name=None):

        # http://blog.asgaard.co.uk/2012/08/03/http-206-partial-content-for-flask-python
        def send_file_partial(filename_or_fp, mimetype):
            range_header = request.headers.get('Range', None)
            if not range_header:
                return send_file(filename_or_fp)

            size = os.path.getsize(filename_or_fp)
            byte1, byte2 = 0, None

            m = re.search('(\d+)-(\d*)', range_header)
            g = m.groups()

            if g[0]: byte1 = int(g[0])
            if g[1]: byte2 = int(g[1])

            length = size - byte1
            if byte2 is not None:
                length = byte2 - byte1

            data = None
            with open(filename_or_fp, 'rb') as f:
                f.seek(byte1)
                data = f.read(length)

            rv = Response(data,
                          206,
                          mimetype=mimetypes.guess_type(filename_or_fp)[0],
                          direct_passthrough=True)
            rv.headers.add('Content-Range', 'bytes {0}-{1}/{2}'.format(byte1, byte1 + length - 1, size))

            return rv

        record = db.get_file(file_id=UUID(hex=file_id))
        if record is not None:
            return send_file_partial(filename_or_fp=record.get_path(), mimetype=record.mime_type)
        else:
            return MeteorApp.not_found(entity_id=file_id)
