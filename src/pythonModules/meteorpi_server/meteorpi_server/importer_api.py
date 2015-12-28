import uuid
from uuid import UUID
from logging import getLogger

from yaml import safe_load
from os import path, remove
import meteorpi_model as model
from flask.ext.jsonpify import jsonify
from flask import request, g
from backports.functools_lru_cache import lru_cache


class BaseImportReceiver(object):
    """
    Base class for entities which should be able to receive imports, whether that's to handle database to database
    replication or otherwise. This base implementation is functional, but simply replies to both event and file record
    imports with 'complete' messages, thus never triggering either status imports or binary data.
    """

    @staticmethod
    def get_importing_user_id():
        """
        Retrieve the importing user ID from the request context, this user will have already authenticated correctly
        by the point the import receiver is called.

        :return:
            The string user_id for the importing user
        """
        return g.user.user_id

    def receive_event(self, import_request):
        """
        Handle an Event import

        :param ImportRequest import_request:
            An instance of :class:`meteorpi_server.importer_api.ImportRequest` which contains the parsed request,
            including the :class:`meteorpi_model.Event` object along with methods that can be used to continue the
            import process. The Event is available as import_request.entity.
        :returns:
            A Flask response, typically generated using the response_xxx() methods on the import_request. If no return
            is made or None is returned then treated as equivalent to returning response_complete() to terminate import
            of this Event
        """
        return import_request.response_complete()

    def receive_file_record(self, import_request):
        """
        Handle a FileRecord import

        :param ImportRequest import_request:
            An instance of :class:`meteorpi_server.importer_api.ImportRequest` which contains the parsed request,
            including the :class:`meteorpi_model.FileRecord` object along with methods that can be used to continue the
            import process. The FileRecord is available as import_request.entity.
        :returns:
            A Flask response, typically generated using the response_xxx() methods on the import_request. If no return
            is made or None is returned then treated as equivalent to returning response_complete() to terminate import
            of this FileRecord
        """
        return import_request.response_complete()

    def receive_status(self, import_request):
        """
        Handle a :class:`meteorpi_model.CameraStatus` import in response to a previous return of response_need_status()
        from one of the :class:`meteorpi_model.Event` or :class:`meteorpi_model.FileRecord` import methods.

        :param ImportRequest import_request:
            An instance of :class:`meteorpi_server.importer_api.ImportRequest` which contains the parsed request,
            including the :class:`meteorpi_model.CameraStatus` object along with methods that can be used to continue
            the import process. The CameraStatus is available as import_request.entity.
        :returns:
            A Flask response, typically generated using the response_xxx() methods on the import_request. If no return
            is made or None is returned then treated as equivalent to returning response_continue() to return to the
            import of the enclosing entity. This is different to receive_file_record() and receive_event() because we
            only ever see a status imported in response to an attempt to import an event or file record which has a
            status we don't have on the importing side.
        """
        pass

    def receive_file_data(self, file_id, file_data, md5_hex):
        """
        Handle the reception of uploaded file data for a given ID. There is no return mechanism for this method, as the
        import protocol specifies that after a binary file is uploaded the corresponding file record or event should be
        sent again. This allows us to implement the import in a stateless fashion, caching aside, at the cost of an
        additional very small HTTP request. The request is small because all the exporter has to do, typically, is send
        the ID of the event or file record as the import infrastructure in this module caches the full record locally.

        :param uuid.UUID file_id:
            The ID of the FileRecord for this file data
        :param file_data:
            A file upload response from Flask's upload handler, acquired with `file_data = request.files['file']`
        :param md5_hex:
            The hex representation of the MD5 hash of this file from the exporting party. This should be checked against
            the result of meteorpi_model.get_md5_hash(path) to ensure integrity of the file reception, and the file
            discarded or otherwise ignored if it does not match.
        :returns:
            None, continues the import irrespective of whether the file was received or not.
        """
        pass


class MeteorDatabaseImportReceiver(BaseImportReceiver):
    """
    An implementation of :class:`meteorpi_server.import_api.BaseImportReceiver` that connects to a
    :class:`meteorpi_db.MeteorDatabase` and pushes any data to it on import, including managing the acquisition of any
    additional information (camera status, binary file data) required in the process.
    """

    def __init__(self, db):
        self.db = db

    def receive_event(self, import_request):
        event = import_request.entity
        if not self.db.has_event_id(event.event_id):
            if not self.db.has_status_id(event.status_id):
                return import_request.response_need_status()
            for file_record in event.file_records:
                if not path.isfile(self.db.file_path_for_id(file_record.file_id)):
                    return import_request.response_need_file_data(file_id=file_record.file_id)
            self.db.import_event(event=event, user_id=BaseImportReceiver.get_importing_user_id())

    def receive_file_record(self, import_request):
        file_record = import_request.entity
        if not self.db.has_file_id(file_record.file_id):
            if not self.db.has_status_id(file_record.status_id):
                return import_request.response_need_status()
            if not path.isfile(self.db.file_path_for_id(file_record.file_id)):
                return import_request.response_need_file_data(file_id=file_record.file_id)
            self.db.import_file_record(file_record=file_record, user_id=BaseImportReceiver.get_importing_user_id())

    def receive_status(self, import_request):
        if not self.db.has_status_id(import_request.entity.status_id):
            self.db.import_camera_status(import_request.entity)

    def receive_file_data(self, file_id, file_data, md5_hex):
        file_path = self.db.file_path_for_id(file_id)
        if not path.isfile(file_path):
            file_data.save(file_path)
            if md5_hex != model.get_md5_hash(file_path):
                remove(file_path)


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


def add_routes(meteor_app, handler=None, url_path='/import'):
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
        elif import_request.entity_type == 'event':
            response = handler.receive_event(import_request)
            if response is not None:
                return response
            else:
                return import_request.response_complete()
        elif import_request.entity_type == 'status':
            response = handler.receive_status(import_request)
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
        file_id = uuid.UUID(hex=file_id_hex)
        file_data = request.files['file']
        if file_data:
            handler.receive_file_data(file_id=file_id, file_data=file_data, md5_hex=md5_hex)
        return ImportRequest.response_continue_after_file()
