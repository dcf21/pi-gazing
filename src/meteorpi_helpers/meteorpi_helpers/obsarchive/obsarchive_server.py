# -*- coding: utf-8 -*-
# obsarchive_server.py

from functools import wraps

from flask import Flask, request, g
from flask.ext.cors import CORS
from flask.ext.jsonpify import jsonify

from .obsarchive_db import ObservationDatabase


class ObservationApp(object):
    """
    Common functionality for observation archive WSGI apps. This won't contain any routes by default, these must be added using
    the functionality in admin_api, importer_api, query_api etc. This allows you to customise your application to suit,
    rather than forcing all the functionality into every instance. It might be sensible, for example, to only import
    the query API for a node which will never need external administration or configuration.

    :ivar app:
        A WSGI compliant application, this can be referenced from e.g. a fastcgi WSGI container and used to connect an
        external server such as LigHTTPD or Apache to the application logic.
    """

    def __init__(self, file_store_path, binary_path):
        """
        Create a new ObservationApp, setting up the internal DB

        :param string file_store_path
            The path to the database file store.
        """
        self.file_store_path = file_store_path
        self.binary_path = binary_path
        self.app = Flask(__name__)
        CORS(app=self.app, resources='/*', allow_headers=['authorization', 'content-type'])

    def get_db(self):
        return ObservationDatabase(file_store_path=self.file_store_path)

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
                    return ObservationApp.authentication_failure(message='No authorization header supplied')
                user_id = auth.username
                password = auth.password
                try:
                    db = self.get_db()
                    user = db.get_user(user_id=user_id, password=password)
                    if user is None:
                        return ObservationApp.authentication_failure(message='Username and / or password incorrect')
                    if roles is not None:
                        for role in roles:
                            if not user.has_role(role):
                                return ObservationApp.authentication_failure(message='Missing role {0}'.format(role))
                    g.user = user
                    db.close_db()
                except ValueError:
                    return ObservationApp.authentication_failure(message='Unrecognized role encountered')
                return f(*args, **kwargs)

            return decorated

        return requires_auth_inner
