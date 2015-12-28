from functools import wraps
from threading import Thread

from os.path import expanduser
from flask import Flask, request, g
from tornado.ioloop import IOLoop
from tornado.wsgi import WSGIContainer
from tornado.web import FallbackHandler, Application
from tornado.httpserver import HTTPServer
from meteorpi_db import MeteorDatabase
from flask.ext.jsonpify import jsonify
from flask.ext.cors import CORS
from meteorpi_server import admin_api, importer_api, query_api


class MeteorApp(object):
    """
    Common functionality for MeteorPi WSGI apps. This won't contain any routes by default, these must be added using the
    functionality in admin_api, importer_api, query_api etc. This allows you to customise your application to suit,
    rather than forcing all the functionality into every instance. It might be sensible, for example, to only import
    the query API for a node which will never need external administration or configuration.

    :ivar app:
        A WSGI compliant application, this can be referenced from e.g. a fastcgi WSGI container and used to connect an
        external server such as LigHTTPD or Apache to the application logic.
    """

    def __init__(self, db):
        """
        Create a new MeteorApp, setting up the internal DB

        :param MeteorDatabase db:
            An instance of :class:`meteorpi_db.MeteorDatabase` to use when accessing the data and file stores.
        """
        self.db = db
        self.app = Flask(__name__)
        CORS(app=self.app, resources='/*', allow_headers=['authorization', 'content-type'])

    @staticmethod
    def success(message='Okay'):
        """
        Build a response with an object containing a single field 'message' with the supplied content

        :param string message:
            message, defaults to 'Okay'
        :return:
            A flask Response object, can be used as a return type from service methods
        """
        resp = jsonify({'message': message})
        resp.status_code = 200
        return resp

    @staticmethod
    def not_found(entity_id=None, message='Entity not found'):
        """
        Build a response to indicate that the requested entity was not found.

        :param string message:
            An optional message, defaults to 'Entity not found'
        :param string entity_id:
            An option ID of the entity requested and which was not found
        :return:
            A flask Response object, can be used as a return type from service methods
        """
        resp = jsonify({'message': message, 'entity_id': entity_id})
        resp.status_code = 404
        return resp

    @staticmethod
    def authentication_failure(message='Authorization required'):
        """
        Returns an authentication required response, including an optional message.

        :param string message:
            An optional message, can be used to specify additional information
        :return:
            flask error code, can be used as a return type from service methods
        """
        resp = jsonify({'message': message})
        resp.status_code = 403
        return resp

    @staticmethod
    def get_user():
        return getattr(g, 'user', None)

    def requires_auth(self, roles=None):
        """
        Used to impose auth constraints on requests which require a logged in user with particular roles.

        :param list[string] roles:
            A list of :class:`string` representing roles the logged in user must have to perform this action. The user
            and password are passed in each request in the authorization header obtained from request.authorization,
            the user and password are checked against the user database and roles obtained. The user must match an
            existing user (including the password, obviously) and must have every role specified in this parameter.
        :return:
            The result of the wrapped function if everything is okay, or a flask.abort(403) error code if authentication
            fails, either because the user isn't properly authenticated or because the user doesn't have the required
            role or roles.
        """

        def requires_auth_inner(f):
            @wraps(f)
            def decorated(*args, **kwargs):
                auth = request.authorization
                if not auth:
                    return MeteorApp.authentication_failure(message='No authorization header supplied')
                user_id = auth.username
                password = auth.password
                try:
                    user = self.db.get_user(user_id=user_id, password=password)
                    if user is None:
                        return MeteorApp.authentication_failure(message='Username and / or password incorrect')
                    if roles is not None:
                        for role in roles:
                            if not user.has_role(role):
                                return MeteorApp.authentication_failure(message='Missing role {0}'.format(role))
                    g.user = user
                except ValueError:
                    return MeteorApp.authentication_failure(message='Unrecognized role encountered')
                return f(*args, **kwargs)

            return decorated

        return requires_auth_inner


class MeteorServer(object):
    """
    Tornado based server, exposes an instance of :class:`meteorpi_server.MeteorApp` on localhost, can either be
    configured to expose all available APIs or can have such APIs added individually.

    The database and application are exposed as instance properties to aid testing.

    :ivar MeteorDatabase db:
        The db used for this server
    :ivar MeteorApp meteor_app:
        The application this server exposes
    :ivar HTTPServer server:
        The tornado HTTPServer instance
    :ivar int port:
        The port on which we're listening for HTTP requests
    """

    class IOLoopThread(Thread):
        """A thread used to run the Tornado IOLoop in a non-blocking fashion, mostly for testing"""

        def __init__(self):
            Thread.__init__(self, name='IOLoopThread')
            self.loop = IOLoop.instance()

        def run(self):
            self.loop.start()

        def stop(self):
            self.loop.stop()

    def __init__(self, db_path, file_store_path, port, add_routes=True):
        """
        Create a new instance, does not start the server.

        :param string db_path:
            Path to the database, i.e. 'localhost:/var/lib/firebird/2.5/data/meteorpi.db'
        :param string file_store_path:
            File path to a directory on disk where the data store can store and retrieve its file data, i.e.
            path.expanduser("~/meteorpi_files")
        :param int port:
            Port on which the HTTP server should run
        :param boolean add_routes:
            Optional, defaults to True. If True then all routes from admin_api, importer_api and query_api will be
            added to the application, otherwise no routes will be added and you'll have to do so explicitly.
        """
        self.db = MeteorDatabase(db_path=db_path, file_store_path=file_store_path)
        self.meteor_app = MeteorApp(db=self.db)
        if add_routes:
            MeteorServer.add_all_routes(self.meteor_app)
        tornado_application = Application([(r'.*', FallbackHandler, dict(fallback=WSGIContainer(self.meteor_app.app)))])
        self.server = HTTPServer(tornado_application)
        self.port = port

    @staticmethod
    def add_all_routes(meteor_app):
        """
        Add routes from admin_api, importer_api and query_api to the specified application

        :param MeteorApp meteor_app:
            The application to which routes should be added
        """
        admin_api.add_routes(meteor_app=meteor_app)
        importer_api.add_routes(meteor_app=meteor_app)
        query_api.add_routes(meteor_app=meteor_app)

    def __str__(self):
        return 'MeteorServer(port={0}, db_path={1}, file_path={2})'.format(self.port, self.db.db_path,
                                                                           self.db.file_store_path)

    def base_url(self):
        """
        :return:
            The full URL of this server
        """
        return 'http://localhost:{0}/'.format(self.port)

    def start_non_blocking(self):
        """
        Start a non-blocking server, returning a function which can be called to stop the server.

        :return:
            A zero-argument function which, when called, will stop the server.
        """
        loop = self.IOLoopThread()
        self.server.listen(self.port)
        loop.start()

        def stop_function():
            self.server.stop()
            loop.stop()
            loop.join()

        return stop_function

    def start(self):
        """
        Start an IOLoop and server in the current thread, this will block until killed
        """
        self.server.listen(self.port)
        IOLoop.instance().start()


"""Start a blocking server if run as a script"""
if __name__ == "__main__":
    server = MeteorServer(db_path='localhost:/var/lib/firebird/2.5/data/meteorpi.db',
                          file_store_path=expanduser("~/meteorpi_files"),
                          port=12345)
    print 'Running blocking server (meteorpi) on port {0}'.format(server.port)
    server.start()
