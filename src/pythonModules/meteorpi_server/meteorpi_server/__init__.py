import threading
from datetime import datetime
import uuid
from functools import wraps

from yaml import safe_load
import os.path as path
import flask
from tornado.ioloop import IOLoop
from tornado.wsgi import WSGIContainer
from tornado.web import FallbackHandler, Application
import tornado.httpserver
import meteorpi_fdb
import meteorpi_model as model
from flask.ext.jsonpify import jsonify
from flask import request
from flask.ext.cors import CORS

DEFAULT_DB_PATH = 'localhost:/var/lib/firebird/2.5/data/meteorpi.fdb'
DEFAULT_FILE_PATH = path.expanduser("~/meteorpi_files")
DEFAULT_PORT = 12345


def _datetime_from_timestamp(time_string):
    """Parse date strings in request URLs"""
    return datetime.fromtimestamp(timestamp=float(time_string))


def build_app(db):
    """Create and return a WSGI app to respond to API requests"""
    app = flask.Flask(__name__)

    CORS(app=app, resources='/*', allow_headers=['authorization', 'content-type'])

    def requires_auth(roles=None):

        def authentication_failure():
            return flask.abort(403)

        def requires_auth_inner(f):
            @wraps(f)
            def decorated(*args, **kwargs):
                auth = request.authorization
                if not auth:
                    return authentication_failure()
                user_id = auth.username
                password = auth.password
                try:
                    user = db.get_user(user_id=user_id, password=password)
                    if user is None:
                        return authentication_failure()
                    if roles is not None:
                        for role in roles:
                            if not user.has_role(role):
                                return authentication_failure()
                    flask.g.user = user
                except ValueError:
                    return authentication_failure()
                return f(*args, **kwargs)

            return decorated

        return requires_auth_inner

    def get_user():
        return getattr(flask.g, 'user', None)

    @app.route('/login', methods=['GET'])
    @requires_auth(roles=['user'])
    def login():
        return jsonify({'user': get_user().as_dict()})

    @app.route('/cameras', methods=['GET'])
    def get_active_cameras():
        cameras = db.get_cameras()
        return jsonify({'cameras': cameras})

    @app.route('/cameras/<camera_id>/status', methods=['GET'])
    def get_current_camera_status(camera_id):
        status = db.get_camera_status(camera_id=camera_id)
        if status is None:
            return 'No active camera with ID {0}'.format(camera_id), 404
        else:
            return jsonify({'status': status.as_dict()})

    @app.route('/cameras/<camera_id>/status/<time_string>', methods=['GET'])
    def get_camera_status(camera_id, time_string):
        status = db.get_camera_status(camera_id=camera_id, time=_datetime_from_timestamp(time_string))
        if status is None:
            return 'No active camera with ID {0}'.format(camera_id), 404
        else:
            return jsonify({'status': status.as_dict()})

    @app.route('/events/<search_string>', methods=['GET'])
    def search_events(search_string):
        search = model.EventSearch.from_dict(safe_load(search_string))
        return jsonify({'events': list(x.as_dict() for x in db.search_events(search))})

    @app.route('/files/<search_string>', methods=['GET'])
    def search_files(search_string):
        # print search_string
        search = model.FileRecordSearch.from_dict(safe_load(search_string))
        # print search.__dict__
        return jsonify({'files': list(x.as_dict() for x in db.search_files(search))})

    @app.route('/files/content/<file_id>/<file_name>', methods=['GET'])
    @app.route('/files/content/<file_id>', methods=['GET'])
    def get_file_content(file_id, file_name=None):
        fr = db.get_file(file_id=uuid.UUID(hex=file_id))
        if fr is not None:
            return flask.send_file(filename_or_fp=fr.get_path(), mimetype=fr.mime_type)
        else:
            return flask.abort(404)

    return app


class MeteorServer():
    """HTTP server which responds to API requests and returns JSON formatted domain objects"""

    class IOLoopThread(threading.Thread):
        """A thread used to run the Tornado IOLoop in a non-blocking fashion, mostly for testing"""

        def __init__(self):
            threading.Thread.__init__(self, name='IOLoopThread')
            self.loop = IOLoop.instance()

        def run(self):
            self.loop.start()

        def stop(self):
            self.loop.stop()

    def __init__(self, db_path=DEFAULT_DB_PATH, file_store_path=DEFAULT_FILE_PATH, port=DEFAULT_PORT):
        self.db = meteorpi_fdb.MeteorDatabase(db_path=db_path, file_store_path=file_store_path)
        app = build_app(self.db)
        tornado_application = Application([(r'.*', FallbackHandler, dict(fallback=WSGIContainer(app)))])
        self.server = tornado.httpserver.HTTPServer(tornado_application)
        self.port = port

        def _build_datetime(datetime_string):
            """Build a datetime from a string used as a URL component"""
            return datetime.datetime.fromtimestamp(timestamp=datetime_string)

    def __str__(self):
        return 'MeteorServer(port={0}, db_path={1}, file_path={2})'.format(self.port, self.db.db_path,
                                                                           self.db.file_store_path)

    def base_url(self):
        return 'http://localhost:{0}/'.format(self.port)

    def start_non_blocking(self):
        """Start an IOLoop in a new thread, returning a function which will stop the new thread and join it"""
        loop = self.IOLoopThread()
        self.server.listen(self.port)
        loop.start()

        def stop_function():
            self.server.stop()
            loop.stop()
            loop.join()

        return stop_function

    def start(self):
        """Start an IOLoop and server in the current thread, this will block until killed"""
        self.server.listen(self.port)
        IOLoop.instance().start()


"""Start a blocking server if run as a script"""
if __name__ == "__main__":
    server = MeteorServer()
    print 'Running blocking server on port {0}'.format(server.port)
    server.start()
