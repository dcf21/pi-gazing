import uuid
from uuid import UUID
from logging import getLogger

from yaml import safe_load
import os.path as path
import meteorpi_model as model
from flask.ext.jsonpify import jsonify
from flask import request, g
from backports.functools_lru_cache import lru_cache


class ImportRequest(object):
    """
    Helper used when importing, makes use of the 'cached_request' request transparent to the importing party.

    :cvar entity_cache:
        LRU cache used to stash entities being imported.
    :cvar logger:
        Logs to 'meteorpi.server.import'
     :ivar entity_type:
            The type of the ID being imported, which will be one of 'file', 'status', 'event' or 'none'.
    """
    entity_cache = lru_cache(maxsize=128, typed=False)

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
        elif isinstance(entity, model.Event):
            self.entity_type = 'event'
        elif isinstance(entity, model.FileRecord):
            self.entity_type = 'file'
        elif isinstance(entity, model.CameraStatus):
            self.entity_type = 'status'
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

    def response_need_status(self):
        """
        Signal the exporter that we need the status associated with the current entity, in response to which it should
        then send a status block with the appropriate ID.

        :return:
            A response that can be returned from a Flask service method
        """
        if self.entity_type == 'file' or self.entity_type == 'event':
            ImportRequest.logger.debug("Sending: need_status, status_id={0}".format(self.entity.status_id.hex))
            return jsonify({'state': 'need_status', 'status_id': self.entity.status_id.hex})
        else:
            ImportRequest.logger.debug(
                "Failed: request to send status for non-event, non-file type {0}".format(self.entity_type))
            raise ValueError("Can't ask for status for entity type {0}".format(self.entity_type))

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
        if entity_type == 'cached_entity':
            entity_id = UUID(g.request_dict['cached_entity_id'])
        else:
            entity_id = UUID(g.request_dict[entity_type][entity_type + '_id'])
        ImportRequest.logger.debug("Received request, type={0}, id={1}".format(entity_type, entity_id))
        entity = ImportRequest._get_entity(entity_id)
        if entity is None:
            ImportRequest.entity_cache.clear()
            ImportRequest.logger.debug(
                "Clearing cache and returning None, entity with id={0} cache requested but missed.".format(entity_id))
        else:
            ImportRequest.logger.debug("Entity with id={0} was {1}".format(entity_id, entity))
        return ImportRequest(entity=entity, entity_id=entity_id)

    @staticmethod
    @entity_cache
    def _get_entity(entity_id):
        """
        Uses the request context to retrieve a :class:`meteorpi_model.CameraStatus`, :class:`meteorpi_model.Event` or
        :class:`meteorpi_model.FileRecord` from the POSTed JSON string. This method will cache using the backported LRU
        cache from Python 3.3 in backports.functools_lru_cache.

        :param string entity_id:
            The ID of a CameraStatus, Event or FileRecord contained within the request
        :return:
            The corresponding entity from the request, using a LRU cache for efficiency. None if we have a request for a
            cached entity but no cache.
        """
        entity_type = g.request_dict['type']
        if entity_type == 'file':
            return model.FileRecord.from_dict(g.request_dict['file'])
        elif entity_type == 'status':
            return model.CameraStatus.from_dict(g.request_dict['status'])
        elif entity_type == 'event':
            return model.Event.from_dict(g.request_dict['event'])
        else:
            return None


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
        Receive an entity import request, using :class:`meteorpi_server.import_api.ImportRequest` to parse it, then
        writing entities into the database and responding with requests for additional information if required.

        :return:
            A response, generally using one of the response_xxx methods in ImportRequest
        """
        import_request = ImportRequest.process_request()
        entity = import_request.entity
        if import_request.entity is None:
            return import_request.response_continue()
        if import_request.entity_type == 'file':
            if not db.has_file_id(entity.file_id):
                if not db.has_camera_status_id(entity.status_id):
                    return import_request.response_need_status()
                if not path.isfile(db.file_path_for_id(entity.file_id)):
                    return import_request.response_need_file_data(file_id=entity.file_id)
                db.import_file_record(entity)
            return import_request.response_complete()
        elif import_request.entity_type == 'event':
            if not db.has_event_id(entity.event_id):
                if not db.has_camera_status_id(entity.status_id):
                    return import_request.response_need_status()
                for file_record in entity.file_records:
                    if not path.isfile(db.file_path_for_id(file_record.file_id)):
                        return import_request.response_need_file_data(file_id=file_record.file_id)
                db.import_event(entity)
            return import_request.response_complete()
        elif import_request.entity_type == 'status':
            if not db.has_camera_status_id(entity.status_id):
                db.import_camera_status(entity)
            return import_request.response_continue()
        else:
            return import_request.response_failed("Unknown import request")

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
        if not path.isfile(db.file_path_for_id(file_id)):
            file_data = request.files['file']
            if file_data:
                file_data.save(db.file_path_for_id(file_id))
        return ImportRequest.response_continue_after_file()
