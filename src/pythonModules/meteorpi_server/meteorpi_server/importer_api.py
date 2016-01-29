# importer_api.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford, Tom Oinn

from logging import getLogger

from yaml import safe_load
from os import path, remove
import meteorpi_model as model
from flask.ext.jsonpify import jsonify
from flask import request, g


class MeteorDatabaseImportReceiver(object):
    """
    Connects to a
    :class:`meteorpi_db.MeteorDatabase` and pushes any data to it on import, including managing the acquisition of any
    additional information (camera status, binary file data) required in the process.
    """

    def __init__(self, db):
        self.db = db

    @staticmethod
    def get_importing_user_id():
        """
        Retrieve the importing user ID from the request context, this user will have already authenticated correctly
        by the point the import receiver is called.

        :return:
            The string user_id for the importing user
        """
        return g.user.user_id

    def receive_observation(self, import_request):
        obs = import_request.entity
        if not self.db.has_event_id(obs.id):
            self.db.import_observation(observation=obs, user_id=self.get_importing_user_id())
            self.db.commit()
        return import_request.response_complete()

    def receive_file_record(self, import_request):
        file_record = import_request.entity
        if not self.db.has_file_id(file_record.id):
            if not path.isfile(self.db.file_path_for_id(file_record.file_id)):
                return import_request.response_need_file_data(file_id=file_record.file_id)
            self.db.import_file(file_item=file_record, user_id=self.get_importing_user_id())
            self.db.commit()
        return import_request.response_complete()

    def receive_metadata(self, import_request):
        entity = import_request.entity
        if not self.db.has_obstory_metadata(entity.id):
            if not self.db.has_obstory_name(entity.obstory_name):
                self.db.register_obstory(obstory_id=entity.obstory_id, obstory_name=entity.obstory_name,
                                         latitude=entity.obstory_lat, longitude=entity.obstory_lng)
            self.db.import_obstory_metadata(obstory_name=entity.obstory_name,
                                            key=entity.key, value=entity.value, metadata_time=entity.time,
                                            time_created=entity.time_created,
                                            user_created=self.get_importing_user_id(),
                                            item_id=entity.id)
            self.db.commit()
        return import_request.response_complete()

    def receive_file_data(self, file_id, file_data, md5_hex):
        file_path = self.db.file_path_for_id(file_id)
        if not path.isfile(file_path):
            file_data.save(file_path)
            if md5_hex != model.get_md5_hash(file_path):
                remove(file_path)


class ImportRequest(object):
    """
    Helper used when importing, makes use of the 'cached_request' request transparent to the importing party.

    :cvar logger:
        Logs to 'meteorpi.server.import'
    :ivar entity_type:
        The type of the ID being imported, which will be one of 'file', 'status', 'event' or 'none'.
    """

    logger = getLogger("meteorpi.server.import")

    def __init__(self, entity, entity_id):
        """
        Constructor, don't use this from your own code, instead use process_request() to create one from the Flask
        request context.

        :param entity:
            The entity being imported, either pulled from the request directly or from the cache. This can be None under
            error conditions, in which case the only legitimate response is to send a 'continue' message back to the
            exporter, at which point it will re-send the necessary information to rebuild the cache.
        :param entity_id:
            The ID of the entity being imported, this will always be defined.
        """
        self.entity_id = entity_id
        self.entity = entity
        if entity is None:
            self.entity_type = 'none'
        elif isinstance(entity, model.Observation):
            self.entity_type = 'observation'
        elif isinstance(entity, model.FileRecord):
            self.entity_type = 'file'
        elif isinstance(entity, model.ObservatoryMetadata):
            self.entity_type = 'metadata'
        else:
            raise ValueError("Unknown entity type, cannot continue.")

    def response_complete(self):
        """
        Signal that this particular entity has been fully processed. The exporter will not send it to this target again
        under this particular export configuration (there is no guarantee another export configuration on the same
        server won't send it, or that it won't be received from another server though, so you must always check whether
        you have an entity and return this status as early as possible if so)

        :return:
            A response that can be returned from a Flask service method
        """
        ImportRequest.logger.info("Completed import for {0} with id {1}".format(self.entity_type, self.entity_id))
        ImportRequest.logger.debug("Sending: complete")
        return jsonify({'state': 'complete'})

    @staticmethod
    def response_failed(message='Import failed'):
        """
        Signal that import for this entity failed. Whether this results in a retry either immediately or later in time
        is entirely up to the exporting party - this should therefore only be used for error cases, and not used to
        indicate duplicate data (use the response_complete for this as it tells the exporter that it shouldn't send the
        data again)

        :param string message:
            An optional message to convey about the failure
        :return:
            A response that can be returned from a Flask service method
        """
        ImportRequest.logger.debug("Sending: failed")
        return jsonify({'state': 'failed', 'message': message})

    def response_continue(self):
        """
        Signals that a partial reception of data has occurred and that the exporter should continue to send data for
        this entity. This should also be used if import-side caching has missed, in which case the response will direct
        the exporter to re-send the full data for the entity (otherwise it will send back the entity ID and rely on the
        import party's caching to resolve it). Use this for generic cases where we need to be messaged again about this
        entity - currently used after requesting and receiving a status block, and in its cache-refresh form if we have
        a cache miss during import.

        :return:
            A response that can be returned from a Flask service method
        """
        if self.entity is not None:
            ImportRequest.logger.debug("Sending: continue")
            return jsonify({'state': 'continue'})
        else:
            ImportRequest.logger.debug("Sending: continue-nocache")
            return jsonify({'state': 'continue-nocache'})

    @staticmethod
    def response_continue_after_file():
        """
        As with response_continue, but static to allow it to be called from context where we don't have a populated
        ImportRequest object. Always uses cached IDs, with the expectation that a subsequent request will force cache
        revalidation if required. Use this when acting on reception of binary data.

        :return:
            A response that can be returned from a Flask service method
        """
        return jsonify({'state': 'continue'})

    @staticmethod
    def response_need_file_data(file_id):
        """
        Signal the exporter that we need the binary data associated with a given file ID

        :param uuid.UUID file_id:
            the UUID of the :class:`meteorpi_model.FileRecord` for which we don't currently have data
        :return:
            A response that can be returned from a Flask service method
        """
        ImportRequest.logger.debug("Sending: need_file_data, id={0}".format(file_id.hex))
        return jsonify({'state': 'need_file_data', 'file_id': file_id.hex})

    @staticmethod
    def process_request():
        """
        Retrieve a CameraStatus, Event or FileRecord from the request, based on the supplied type and ID. If the type is
        'cached_request' then the ID must be specified in 'cached_request_id' - if this ID is not for an entity in the
        cache this method will return None and clear the cache (this should only happen under conditions where we've
        failed to correctly handle caching, such as a server restart or under extreme load, but will result in the
        server having to re-request a previous value from the exporting party).

        :return:
            A dict containing 'entity' - the entity for this request or None if there was an issue causing an unexpected
            cache miss, and 'entity-id' which will be the UUID of the entity requested.
            The entity corresponding to this request, or None if we had an issue and there was an unexpected cache miss.
        """
        g.request_dict = safe_load(request.get_data())
        entity_type = g.request_dict['type']
        entity_id = g.request_dict[entity_type]['id']
        ImportRequest.logger.debug("Received request, type={0}, id={1}".format(entity_type, entity_id))
        entity = ImportRequest._get_entity(entity_id)
        ImportRequest.logger.debug("Entity with id={0} was {1}".format(entity_id, entity))
        return ImportRequest(entity=entity, entity_id=entity_id)

    @staticmethod
    def _get_entity(entity_id):
        """
        Uses the request context to retrieve a :class:`meteorpi_model.CameraStatus`, :class:`meteorpi_model.Event` or
        :class:`meteorpi_model.FileRecord` from the POSTed JSON string.

        :param string entity_id:
            The ID of a CameraStatus, Event or FileRecord contained within the request
        :return:
            The corresponding entity from the request.
        """
        entity_type = g.request_dict['type']
        if entity_type == 'file':
            return model.FileRecord.from_dict(g.request_dict['file'])
        elif entity_type == 'metadata':
            return model.ObservatoryMetadata.from_dict(g.request_dict['metadata'])
        elif entity_type == 'observation':
            return model.Observation.from_dict(g.request_dict['obs'])
        else:
            return None


def add_routes(meteor_app, handler=None, url_path='/importv2'):
    """
    Add two routes to the specified instance of :class:`meteorpi_server.MeteorApp` to implement the import API and allow
    for replication of data to this server.

    :param meteorpi_server.MeteorApp meteor_app:
        The :class:`meteorpi_server.MeteorApp` to which import routes should be added
    :param meteorpi_server.importer_api.BaseImportReceiver handler:
        A subclass of :class:`meteorpi_server.importer_api.BaseImportReceiver` which is used to handle the import. If
        not specified this defaults to an instance of :class:`meteorpi_server.importer_api.MeteorDatabaseImportReceiver`
        which will replicate any missing information from the import into the database attached to the meteor_app.
    :param string url_path:
        The base of the import routes for this application. Defaults to '/import' - routes will be created at this path
        and as import_path/data/<id> for binary data reception. Both paths only respond to POST requests and require
        that the requests are authenticated and that the authenticated user has the 'import' role.
    """
    db = meteor_app.db
    app = meteor_app.app
    if handler is None:
        handler = MeteorDatabaseImportReceiver(db=db)

    @app.route(url_path, methods=['POST'])
    @meteor_app.requires_auth(roles=['import'])
    def import_entities():
        """
        Receive an entity import request, using :class:`meteorpi_server.import_api.ImportRequest` to parse it, then
        passing the parsed request on to an instance of :class:`meteorpi_server.import_api.BaseImportReceiver` to deal
        with the possible import types.

        :return:
            A response, generally using one of the response_xxx methods in ImportRequest
        """
        import_request = ImportRequest.process_request()
        if import_request.entity is None:
            return import_request.response_continue()
        if import_request.entity_type == 'file':
            response = handler.receive_file_record(import_request)
            if response is not None:
                return response
            else:
                return import_request.response_complete()
        elif import_request.entity_type == 'observation':
            response = handler.receive_observation(import_request)
            if response is not None:
                return response
            else:
                return import_request.response_complete()
        elif import_request.entity_type == 'metadata':
            response = handler.receive_metadata(import_request)
            if response is not None:
                return response
            else:
                return import_request.response_continue()
        else:
            return import_request.response_failed("Unknown import request")

    @app.route('{0}/data/<file_id_hex>/<md5_hex>'.format(url_path), methods=['POST'])
    @meteor_app.requires_auth(roles=['import'])
    def import_file_data(file_id_hex, md5_hex):
        """
        Receive a file upload, passing it to the handler if it contains the appropriate information

        :param string file_id_hex:
            The hex representation of the :class:`meteorpi_model.FileRecord` to which this data belongs.
        """
        file_id = file_id_hex
        file_data = request.files['file']
        if file_data:
            handler.receive_file_data(file_id=file_id, file_data=file_data, md5_hex=md5_hex)
        return ImportRequest.response_continue_after_file()
