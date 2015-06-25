import shutil
import uuid
import datetime
from contextlib import closing
import json

from yaml import safe_load
from passlib.hash import pbkdf2_sha256

import os.path as path
import os
import fdb
import meteorpi_model as mp


def first_non_null(values):
    """
    Retrieve the first, non-null item in the specified list

    :param values:
        a list of values from which the first non-null is returned
    :return:
        the first non-null item
    :raises:
        ValueError if there isn't any such item in the list.
    """
    for item in values:
        if item is not None:
            return item
    raise ValueError("No non-null item in supplied list.")


def get_installation_id():
    """Get the installation ID of the current system, using the MAC address
    rendered as a 12 character hex string.

    :return:
        ID for this installation. Currently this is based on the MAC address of the first network interface - for our
        Pi based cameras this will also be the only hardware network interface but it might be good to have a way for
        us to specify this ID explicitly somewhere, in a configuration file or similar. The installation ID is more
        problematic for non-camera nodes.
    """

    def _to_array(number):
        result = ''
        n = number
        while n > 0:
            (div, mod) = divmod(n, 256)
            n = (n - mod) / 256
            result = ('%0.2x' % mod) + result
        return result

    return _to_array(uuid.getnode())


def _first_from_generator(generator):
    """Pull the first value from a generator and return it.

    :param generator:
        A generator, this will be mapped onto a list and the first item extracted.
    :return:
        None if there are no items, or the first item otherwise.
    :internal:
    """
    results = list(generator)
    if len(results) == 0:
        return None
    return results[0]


def _search_events_sql_builder(search):
    """
    Create and populate an instance of :class:`meteorpi_fdb.SQLBuilder` for a given
    :class:`meteorpi_model.EventSearch`. This can then be used to retrieve the results of the search, materialise
    them into :class:`meteorpi_model.Event` instances etc.
    :param EventSearch search:
        The search to realise
    :return:
        A :class:`meteorpi_fdb.SQLBuilder` configured from the supplied search
    """
    b = SQLBuilder(tables='t_event e, t_cameraStatus s', where_clauses=['e.statusID = s.internalID'])
    b.add_set_membership(search.camera_ids, 'e.cameraID')
    b.add_sql(search.lat_min, 's.locationLatitude >= (?)')
    b.add_sql(search.lat_max, 's.locationLatitude <= (?)')
    b.add_sql(search.long_min, 's.locationLongitude >= (?)')
    b.add_sql(search.long_max, 's.locationLongitude <= (?)')
    b.add_sql(search.before, 'e.eventTime < (?)')
    b.add_sql(search.after, 'e.eventTime > (?)')
    b.add_sql(search.before_offset, 'e.eventOffset < (?)')
    b.add_sql(search.after_offset, 'e.eventOffset > (?)')
    b.add_sql(search.event_type, 'e.eventType = (?)')
    b.add_metadata_query_properties(meta_constraints=search.meta_constraints, meta_table_name='t_eventMeta')

    # Check for import / export filters
    if search.exclude_incomplete:
        b.where_clauses.append(
            'NOT EXISTS (SELECT * FROM t_eventImport i WHERE i.eventID = e.internalID AND i.importState > 0)')
    if search.exclude_imported:
        b.where_clauses.append('NOT EXISTS (SELECT * FROM t_eventImport i WHERE i.eventID = e.internalID')
    if search.exclude_export_to is not None:
        b.where_clauses.append('NOT EXISTS (SELECT * FROM t_eventExport ex, t_exportConfig c '
                               'WHERE ex.eventID = e.internalID '
                               'AND ex.exportConfig = c.internalID '
                               'AND c.exportConfigID = (?))')
        b.sql_args.append(SQLBuilder.map_value(search.exclude_export_to))
    return b


def _search_files_sql_builder(search):
    """
    Create and populate an instance of :class:`meteorpi_fdb.SQLBuilder` for a given
    :class:`meteorpi_model.FileRecordSearch`. This can then be used to retrieve the results of the search, materialise
    them into :class:`meteorpi_model.FileRecord` instances etc.
    :param FileRecordSearch search:
        The search to realise
    :return:
        A :class:`meteorpi_fdb.SQLBuilder` configured from the supplied search
    """
    b = SQLBuilder(tables='t_file f, t_cameraStatus s',
                   where_clauses=['f.statusID = s.internalID'])
    b.add_set_membership(search.camera_ids, 'f.cameraID')
    b.add_sql(search.lat_min, 's.locationLatitude >= (?)')
    b.add_sql(search.lat_max, 's.locationLatitude <= (?)')
    b.add_sql(search.long_min, 's.locationLongitude >= (?)')
    b.add_sql(search.long_max, 's.locationLongitude <= (?)')
    b.add_sql(search.before, 'f.fileTime < (?)')
    b.add_sql(search.after, 'f.fileTime > (?)')
    b.add_sql(search.before_offset, 'f.fileOffset < (?)')
    b.add_sql(search.after_offset, 'f.fileOffset > (?)')
    b.add_sql(search.mime_type, 'f.mimeType = (?)')
    b.add_sql(search.semantic_type, 'f.semanticType = (?)')
    b.add_metadata_query_properties(meta_constraints=search.meta_constraints, meta_table_name='t_fileMeta')
    # Check for avoiding event files
    if search.exclude_events:
        b.where_clauses.append(
            'NOT EXISTS (SELECT * FROM t_event_to_file ef WHERE ef.fileID = f.internalID)')
    # Check for import / export filters
    if search.exclude_incomplete:
        b.where_clauses.append(
            'NOT EXISTS (SELECT * FROM t_fileImport i WHERE i.fileID = f.internalID AND i.importState > 0)')
    if search.exclude_imported:
        b.where_clauses.append('NOT EXISTS (SELECT * FROM t_fileImport i WHERE i.fileID = f.internalID')
    if search.exclude_export_to is not None:
        b.where_clauses.append('NOT EXISTS (SELECT * FROM t_fileExport e, t_exportConfig c '
                               'WHERE e.fileID = f.internalID '
                               'AND e.exportConfig = c.internalID '
                               'AND c.exportConfigID = (?))')
        b.sql_args.append(SQLBuilder.map_value(search.exclude_export_to))
    return b


class SQLBuilder:
    """
    Helper class to make it easier to build large, potentially complex, SQL clauses.

    This class contains various methods to allow SQL queries to be built without having to manage enormous strings of
    SQL. It includes facilities to add metadata constraints, and to map from :py:class:`meteorpi_model.NSString` and
    :class:`datetime.datetime` to the forms
    we use within the firebird database (strings and big integers respectively). Also helps simplify the discovery and
    debugging of issues with generated queries as we can pull out the query strings directly from this object.
    """

    def __init__(self, tables, where_clauses=None):
        """
        Construct a new, empty, SQLBuilder

        :param where_clauses:
            Optionally specify an initial array of WHERE clauses, defaults to an empty sequence. Clauses specified here
            must not include the string 'WHERE', but should be e.g. ['e.statusID = s.internalID']
        :param tables:
            A SQL fragment defining the tables used by this SQLBuilder, i.e. 't_file f, t_cameraStatus s'
        :ivar where_clauses:
            A list of strings of SQL, which will be prefixed by 'WHERE' to construct a constraint. As with the init
            parameter these will not include the 'WHERE' itself.
        :ivar sql_args:
            A list of values which will be bound into an execution of the SQL query
        :return:
            An unpopulated SQLBuilder, including any initial where clauses.
        """
        self.tables = tables
        self.sql_args = []
        if where_clauses is None:
            self.where_clauses = []
        self.where_clauses = where_clauses

    @staticmethod
    def map_value(value):
        """
        Perform type translation of values to be inserted into SQL queries based on their types.

        :param value:
            The value to map
        :return:
            The mapped value. This will be the same as the input value other than two special cases: Firstly if the
            input value is an instance of model.NSString we map it to the stringified form 'ns:value'. Secondly if the
            value is an instance of datetime.datetime we map it using model.utc_datetime_to_milliseconds, returning
            an integer.
        """
        if value is None:
            return None
        elif isinstance(value, mp.NSString):
            return str(value)
        elif isinstance(value, datetime.datetime):
            return mp.utc_datetime_to_milliseconds(value)
        elif isinstance(value, uuid.UUID):
            return value.bytes
        else:
            return value

    def add_sql(self, value, clause):
        """
        Add a WHERE clause to the state. Handles NSString and datetime.datetime sensibly.

        :param value:
            The unknown to bind into the state. Uses SQLBuilder._map_value() to map this into an appropriate database
            compatible type.
        :param clause:
            A SQL fragment defining the restriction on the unknown value
        """
        if value is not None:
            self.sql_args.append(SQLBuilder.map_value(value))
            self.where_clauses.append(clause)

    def add_set_membership(self, values, column_name):
        """
        Append a set membership test, creating a query of the form 'WHERE name IN (?,?...?)'.

        :param values:
            A list of values, or a subclass of basestring. If this is non-None and non-empty this will add a set
            membership test to the state. If the supplied value is a basestring it will be wrapped in a single element
            list. Values are mapped by SQLBuilder._map_value before being added, so e.g. NSString instances will work
            here.
        :param column_name:
            The name of the column to use when checking the 'IN' condition.
        """
        if values is not None and len(values) > 0:
            if isinstance(values, basestring):
                values = [values]
            question_marks = ', '.join(["?"] * len(values))
            self.where_clauses.append('{0} IN ({1})'.format(column_name, question_marks))
            for value in values:
                self.sql_args.append(SQLBuilder.map_value(value))

    def add_metadata_query_properties(self, meta_constraints, meta_table_name):
        """
        Construct WHERE clauses from a list of MetaConstraint objects, adding them to the query state.

        :param meta_constraints:
            A list of MetaConstraint objects, each of which defines a condition over metadata which must be satisfied
            for results to be included in the overall query.
        :param meta_table_name:
            The name of the link table between the queried entity and metadata, i.e. t_eventMeta or t_fileMeta in the
            current code.
        :raises:
            ValueError if an unknown meta constraint type is encountered.
        """
        for mc in meta_constraints:
            meta_key = str(mc.key)
            ct = mc.constraint_type
            sql_template = 'f.internalID IN (' \
                           'SELECT fm.fileID FROM {0} fm WHERE fm.{1} {2} (?) AND fm.metaKey = (?))'
            # Meta value, mapping to the correct type as appropriate
            self.sql_args.append(SQLBuilder.map_value(mc.value))
            # Put the meta key
            self.sql_args.append(str(mc.key))
            # Put an appropriate WHERE clause
            if ct == 'after':
                self.where_clauses.append(sql_template.format(meta_table_name, 'dateValue', '>', meta_key))
            elif ct == 'before':
                self.where_clauses.append(sql_template.format(meta_table_name, 'dateValue', '<', meta_key))
            elif ct == 'less':
                self.where_clauses.append(sql_template.format(meta_table_name, 'floatValue', '<', meta_key))
            elif ct == 'greater':
                self.where_clauses.append(sql_template.format(meta_table_name, 'floatValue', '>', meta_key))
            elif ct == 'number_equals':
                self.where_clauses.append(sql_template.format(meta_table_name, 'floatValue', '=', meta_key))
            elif ct == 'string_equals':
                self.where_clauses.append(sql_template.format(meta_table_name, 'stringValue', '=', meta_key))
            else:
                raise ValueError("Unknown meta constraint type!")

    def get_select_sql(self, columns, order=None, limit=0, skip=0):
        """
        Build a SELECT query based on the current state of the builder.

        :param columns:
            SQL fragment describing which columns to select i.e. 'e.cameraID, s.statusID'
        :param order:
            Optional ordering constraint, i.e. 'e.eventTime DESC'
        :param limit:
            Optional, used to build the 'FIRST n' clause. If not specified no limit is imposed.
        :param skip:
            Optional, used to build the 'SKIP n' clause. If not specified results are returned from the first item
            available. Note that this parameter must be combined with 'order', otherwise there's no ordering imposed
            on the results and subsequent queries may return overlapping data randomly. It's unlikely that this will
            actually happen as almost all databases do in fact create an internal ordering, but there's no guarantee
            of this (and some operations such as indexing will definitely break this property unless explicitly set).
        :returns:
            A SQL SELECT query, which will make use of self.sql_args when executed. To run the query, use e.g.:

            .. code-block:: python

                b = SQLBuilder()
                # Call add_sql etc methods on b here.
                sql = b.get_select_sql(columns='e.cameraID, e.eventID, e.internalID, e.eventTime',
                                       skip=search.skip,
                                       limit=search.limit,
                                       order='e.eventTime DESC')
                with closing(connection.cursor()) as cursor:
                    cursor.execute(sql, b.sql_args)
                    # do stuff with results

        """
        sql = 'SELECT '
        if limit > 0:
            sql += 'FIRST {0} '.format(limit)
        if skip > 0:
            sql += 'SKIP {0} '.format(skip)
        sql += '{0} FROM {1} WHERE '.format(columns, self.tables)
        sql += ' AND '.join(self.where_clauses)
        if order is not None:
            sql += ' ORDER BY {0}'.format(order)
        return sql

    def get_count_sql(self):
        """
        Build a SELECT query which returns the count of items for an unlimited SELECT

        :return:
            A SQL SELECT query which returns the count of items for an unlimited query based on this SQLBuilder
        """
        return 'SELECT count(*) FROM ' + self.tables + ' WHERE ' + (' AND '.join(self.where_clauses))


SOFTWARE_VERSION = 1


class MeteorDatabase:
    """Class representing a single MeteorPi relational database and file
    store."""

    def __init__(
            self,
            db_path='localhost:/var/lib/firebird/2.5/data/meteorpi.fdb',
            file_store_path=path.expanduser("~/meteorpi_files")):
        """
        Create a new db instance. This connects to the specified firebird database and retains a connection which is
        then used by methods in this class when querying or updating the database.

        :param db_path:
            String passed to the firebird database driver and specifying a file location. Defaults to
            localhost:/var/lib/firebird/2.5/data/meteorpi.fdb
        :param file_store_path:
            File data is stored on the file system in a flat structure within the specified directory. Defaults to
            the expansion for the current user of ~/meteorpi_files. If this location doesn't exist it will be created,
            along with any necessary parent directories.
        :return:
            An instance of MeteorDatabase.
        """
        self.con = fdb.connect(
            dsn=db_path,
            user='meteorpi',
            password='meteorpi')
        self.db_path = db_path
        if not path.exists(file_store_path):
            os.makedirs(file_store_path)
        if not path.isdir(file_store_path):
            raise ValueError(
                'File store path already exists but is not a directory!')
        self.file_store_path = file_store_path

    def __str__(self):
        """Simple string representation of this db object

        :return: info about the db path and file store location
        """
        return 'MeteorDatabase(db={0}, file_store_path={1}'.format(
            self.db_path,
            self.file_store_path)

    def _export_configuration_generator(self, sql, sql_args):
        """
        Generator for :class:`meteorpi_model.ExportConfiguration`

        :param sql:
            A SQL statement which must return rows with, in order, internalID, exportConfigID, exportType, searchString,
            targetURL, targetUser, targetPassword, exportName, description, active
        :param sql_args:
            Any variables required to populate the query provided in 'sql'
        :return:
            A generator which produces :class:`meteorpi_model.ExportConfiguration` instances from the supplied SQL,
            closing any opened cursors on completion.
        """
        with closing(self.con.cursor()) as cursor:
            cursor.execute(sql, sql_args)
            for (internalID, exportConfigID, exportType, searchString, targetURL,
                 targetUser, targetPassword, exportName, description, active) in cursor:
                if exportType == "event":
                    search = mp.EventSearch.from_dict(safe_load(searchString))
                elif exportType == "file":
                    search = mp.FileRecordSearch.from_dict(safe_load(searchString))
                else:
                    raise ValueError("Unknown search type!")
                yield mp.ExportConfiguration(target_url=targetURL, user_id=targetUser, password=targetPassword,
                                             search=search, name=exportName, description=description, enabled=active,
                                             config_id=uuid.UUID(bytes=exportConfigID))

    def _event_generator(self, sql, sql_args):
        """Generator for Event

        :param sql:
            A SQL statement which must return rows with, in order, camera ID, event ID, internal ID, event time, event
            semantic type, status ID
        :param sql_args:
            Any variables required to populate the query provided in 'sql'
        :return:
            A generator which produces Event instances from the supplied SQL, closing any opened cursors on completion.
        """
        with closing(self.con.cursor()) as cursor:
            cursor.execute(sql, sql_args)
            for (cameraID, eventID, internalID, eventTime, eventType, statusID) in cursor:
                event = mp.Event(
                    camera_id=cameraID,
                    event_time=mp.milliseconds_to_utc_datetime(eventTime),
                    event_id=uuid.UUID(bytes=eventID),
                    event_type=mp.NSString.from_string(eventType),
                    status_id=uuid.UUID(bytes=statusID))
                fr_sql = 'SELECT f.internalID, f.cameraID, f.mimeType, ' \
                         'f.semanticType, f.fileTime, f.fileSize, f.fileID, f.fileName, s.statusID ' \
                         'FROM t_file f, t_cameraStatus s, t_event_to_file ef ' \
                         'WHERE f.statusID = s.internalID AND ef.fileID = f.internalID AND ef.eventID = (?)'
                event.file_records = list(self._file_generator(fr_sql, (internalID,)))
                with closing(self.con.cursor()) as meta_cur:
                    meta_cur.execute(
                        'SELECT metaKey, stringValue, floatValue, dateValue '
                        'FROM t_eventMeta t '
                        'WHERE t.eventID = (?) '
                        'ORDER BY metaIndex ASC',
                        (internalID,))
                    for (metaKey, stringValue, floatValue, dateValue) in meta_cur:
                        event.meta.append(
                            mp.Meta(key=mp.NSString.from_string(metaKey),
                                    value=first_non_null(
                                        [stringValue, floatValue, mp.milliseconds_to_utc_datetime(dateValue)])))
                yield event

    def _file_generator(self, sql, sql_args):
        """Generator for FileRecord

        :param sql:
            A SQL statement which must return rows with, in order, internal ID, camera ID, mime type, semantic type,
            file time, file size, file ID, file name and file status ID.
        :param sql_args:
            Any variables required to populate the query provided in 'sql'
        :return:
            A generator which produces FileRecord instances from the supplied SQL, closing any opened cursors on
            completion.
        """
        with closing(self.con.cursor()) as cursor:
            cursor.execute(sql, sql_args)
            for (internalID, cameraID, mimeType, semanticType, fileTime, fileSize, fileID, fileName,
                 statusID) in cursor:
                fr = mp.FileRecord(
                    camera_id=cameraID,
                    mime_type=mimeType,
                    semantic_type=mp.NSString.from_string(semanticType),
                    status_id=uuid.UUID(bytes=statusID))
                fr.file_id = uuid.UUID(bytes=fileID)
                fr.file_size = fileSize
                fr.file_time = mp.milliseconds_to_utc_datetime(fileTime)
                fr.file_name = fileName
                fr.get_path = lambda: path.join(self.file_store_path, fr.file_id.hex)
                with closing(self.con.cursor()) as meta_cur:
                    meta_cur.execute(
                        'SELECT metaKey, stringValue, floatValue, dateValue '
                        'FROM t_fileMeta t '
                        'WHERE t.fileID = (?) '
                        'ORDER BY metaIndex ASC',
                        (internalID,))
                    for (metaKey, stringValue, floatValue, dateValue) in meta_cur:
                        fr.meta.append(
                            mp.Meta(key=mp.NSString.from_string(metaKey),
                                    value=first_non_null(
                                        [stringValue, floatValue, mp.milliseconds_to_utc_datetime(dateValue)])))
                yield fr

    def search_events(self, search):
        """
        Search for events

        :param search:
            an instance of EventSearch used to constrain the events returned from the DB
        :return:
            a structure of {count:int total rows of an unrestricted search, events:list of Event}
        """
        b = _search_events_sql_builder(search)
        sql = b.get_select_sql(columns='e.cameraID, e.eventID, e.internalID, e.eventTime, e.eventType, s.statusID',
                               skip=search.skip,
                               limit=search.limit,
                               order='e.eventTime DESC')

        events = list(self._event_generator(sql, b.sql_args))
        rows_returned = len(events)
        total_rows = rows_returned + search.skip
        if (rows_returned == search.limit > 0) or (rows_returned == 0 and search.skip > 0):
            with closing(self.con.cursor()) as count_cur:
                count_cur.execute(b.get_count_sql(), b.sql_args)
                total_rows = count_cur.fetchone()[0]
        return {"count": total_rows,
                "events": events}

    def search_files(self, search):
        """
        Search for FileRecords

        :param search:
            an instance of FileRecordSearch used to constrain the events returned from the DB
        :return:
            a structure of {count:int total rows of an unrestricted search, events:list of FileRecord}
        """
        b = _search_files_sql_builder(search)
        sql = b.get_select_sql(columns='f.internalID, f.cameraID, f.mimeType, f.semanticType, f.fileTime, '
                                       'f.fileSize, f.fileID, f.fileName, s.statusID',
                               skip=search.skip,
                               limit=search.limit,
                               order='f.fileTime DESC')
        files = list(self._file_generator(sql=sql, sql_args=b.sql_args))
        rows_returned = len(files)
        total_rows = rows_returned + search.skip
        if (rows_returned == search.limit > 0) or (rows_returned == 0 and search.skip > 0):
            with closing(self.con.cursor()) as cur:
                cur.execute(b.get_count_sql(), b.sql_args)
                total_rows = cur.fetchone()[0]
        return {"count": total_rows,
                "files": files}

    def get_event(self, event_id):
        """
        Retrieve an existing Event by its ID

        :param event_id:
        :return:
        """
        sql = 'SELECT e.cameraID, e.eventID, e.internalID, e.eventTime, ' \
              'e.eventType, s.statusID ' \
              'FROM t_event e, t_cameraStatus s ' \
              'WHERE e.eventID = (?) AND s.internalID = e.statusID'
        return _first_from_generator(self._event_generator(sql=sql, sql_args=(event_id.bytes,)))

    def get_file(self, file_id):
        """
        Retrieve an existing FileRecord by its ID

        :param file_id:
        :return:
        """
        sql = 'SELECT t.internalID, t.cameraID, t.mimeType, ' \
              't.semanticType, t.fileTime, t.fileSize, t.fileID, t.fileName, s.statusID ' \
              'FROM t_file t, t_cameraStatus s WHERE t.fileID=(?) AND t.statusID = s.internalID'
        return _first_from_generator(self._file_generator(sql=sql, sql_args=(file_id.bytes,)))

    def register_event(
            self,
            camera_id,
            event_time,
            event_type,
            file_records=None,
            event_meta=None):
        """
        Register a new event, updating the database and returning the corresponding Event object

        :param camera_id:
        :param event_time:
        :param event_type:
        :param file_records:
        :param event_meta:
        :return:
        """
        if file_records is None:
            file_records = []
        if event_meta is None:
            event_meta = []
        status_id = self._get_camera_status_id(camera_id=camera_id, time=event_time)
        if status_id is None:
            raise ValueError('No status defined for camera id <%s> at time <%s>!' % (camera_id, event_time))
        with closing(self.con.cursor()) as cur:
            day_and_offset = mp.get_day_and_offset(event_time)
            cur.execute(
                'INSERT INTO t_event (cameraID, eventTime, eventOffset, eventType, '
                'statusID) '
                'VALUES (?, ?, ?, ?, ?) '
                'RETURNING internalID, eventID, eventTime',
                (camera_id,
                 mp.utc_datetime_to_milliseconds(event_time),
                 day_and_offset['seconds'],
                 str(event_type),
                 status_id['internal_id']))
            ids = cur.fetchone()
            event_internal_id = ids[0]
            event_id = uuid.UUID(bytes=ids[1])
            event = mp.Event(camera_id=camera_id, event_time=mp.milliseconds_to_utc_datetime(ids[2]),
                             event_id=event_id, event_type=event_type, status_id=status_id['status_id'])
            for file_record_index, file_record in enumerate(file_records):
                event.file_records.append(file_record)
                cur.execute(
                    'SELECT internalID FROM t_file WHERE fileID = (?)',
                    (file_record.file_id.bytes,
                     ))
                file_internal_id = cur.fetchone()[0]
                cur.execute(
                    'INSERT INTO t_event_to_file '
                    '(fileID, eventID, sequenceNumber) '
                    'VALUES (?, ?, ?)',
                    (file_internal_id,
                     event_internal_id,
                     file_record_index))
            # Store the event metadata
            for meta_index, meta in enumerate(event_meta):
                cur.execute(
                    'INSERT INTO t_eventMeta '
                    '(eventID, metaKey, stringValue, floatValue, dateValue, metaIndex) '
                    'VALUES (?, ?, ?, ?, ?, ?)',
                    (event_internal_id,
                     str(meta.key),
                     meta.string_value(),
                     meta.float_value(),
                     mp.utc_datetime_to_milliseconds(meta.date_value()),
                     meta_index))
                event.meta.append(
                    mp.Meta(key=meta.key, value=meta.value))
        self.con.commit()
        return event

    def register_file(
            self,
            file_path,
            mime_type,
            semantic_type,
            file_time,
            file_metas,
            camera_id=get_installation_id(),
            file_name=None):
        """
        Register a file in the database, also moving the file into the file store. Returns the corresponding FileRecord
        object.

        :param file_path:
        :param mime_type:
        :param semantic_type:
        :param file_time:
        :param file_metas:
        :param camera_id:
        :param file_name:
        :return:
        """
        # Check the file exists, and retrieve its size
        if not path.exists(file_path):
            raise ValueError('No file exists at {0}'.format(file_path))
        file_size_bytes = os.stat(file_path).st_size
        # Handle the database parts
        status_id = self._get_camera_status_id(camera_id=camera_id, time=file_time)
        if status_id is None:
            raise ValueError('No status defined for camera id <%s> at time <%s>!' % (camera_id, file_time))
        cur = self.con.cursor()
        day_and_offset = mp.get_day_and_offset(file_time)
        cur.execute(
            'INSERT INTO t_file (cameraID, mimeType, '
            'semanticType, fileTime, fileOffset, fileSize, statusID, fileName) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?) '
            'RETURNING internalID, fileID, fileTime',
            (camera_id,
             mime_type,
             str(semantic_type),
             mp.utc_datetime_to_milliseconds(file_time),
             day_and_offset['seconds'],
             file_size_bytes,
             status_id['internal_id'],
             file_name))
        row = cur.fetchonemap()
        # Retrieve the internal ID of the file row to link fileMeta if required
        file_internal_id = row['internalID']
        # Retrieve the generated file ID, used to build the File object and to
        # name the source file
        file_id = uuid.UUID(bytes=row['fileID'])
        # Retrieve the file time as stored in the DB
        stored_file_time = row['fileTime']
        result_file = mp.FileRecord(camera_id=camera_id, mime_type=mime_type, semantic_type=semantic_type,
                                    status_id=status_id['status_id'])
        result_file.file_time = mp.milliseconds_to_utc_datetime(stored_file_time)
        result_file.file_id = file_id
        result_file.file_size = file_size_bytes
        # Store the fileMeta
        for file_meta_index, file_meta in enumerate(file_metas):
            cur.execute(
                'INSERT INTO t_fileMeta '
                '(fileID, metaKey, stringValue, floatValue, dateValue, metaIndex) '
                'VALUES (?, ?, ?, ?, ?, ?)',
                (file_internal_id,
                 str(file_meta.key),
                 file_meta.string_value(),
                 file_meta.float_value(),
                 mp.utc_datetime_to_milliseconds(file_meta.date_value()),
                 file_meta_index))
            result_file.meta.append(
                mp.Meta(key=file_meta.key, value=file_meta.value))
        self.con.commit()
        # Move the original file from its path
        target_file_path = path.join(self.file_store_path, result_file.file_id.hex)
        shutil.move(file_path, target_file_path)
        # Return the resultant file object
        return result_file

    def create_or_update_export_configuration(self, export_config):
        """
        Create a new file export configuration or update an existing one

        :param ExportConfiguration export_config:
            a :class:`meteorpi_model.ExportConfiguration` containing the specification for the export. If this
            doesn't include a 'config_id' field it will be inserted as a new record in the database and the field will
            be populated, updating the supplied object. If it does exist already this will update the other properties
            in the database to match the supplied object.
        :returns:
            The supplied :class:`meteorpi_model.ExportConfiguration` as stored in the DB. This is guaranteed to have
            its 'config_id' :class:`uuid.UUID` field defined.
        """
        search_string = json.dumps(obj=export_config.search.as_dict())
        user_id = export_config.user_id
        password = export_config.password
        target_url = export_config.target_url
        enabled = export_config.enabled
        name = export_config.name
        description = export_config.description
        export_type = export_config.type
        with closing(self.con.cursor()) as cur:
            if export_config.config_id is not None:
                # Update existing record
                cur.execute(
                    'UPDATE t_exportConfig c '
                    'SET c.searchString = (?), c.targetUrl = (?), c.targetUser = (?), c.targetPassword = (?), '
                    'c.exportName = (?), c.description = (?), c.active = (?), c.exportType = (?) '
                    'WHERE c.exportConfigId = (?)',
                    (search_string, target_url, user_id, password, name, description, enabled, export_type,
                     export_config.config_id.bytes))
            else:
                # Create new record and add the ID into the supplied config
                cur.execute(
                    'INSERT INTO t_exportConfig '
                    '(searchString, targetUrl, targetUser, targetPassword, '
                    'exportName, description, active, exportType) '
                    'VALUES (?,?,?,?,?,?,?,?) '
                    'RETURNING exportConfigId',
                    (search_string, target_url, user_id, password, name, description, enabled, export_type))
                export_config.config_id = uuid.UUID(bytes=cur.fetchone()[0])
        self.con.commit()
        return export_config

    def delete_export_configuration(self, config_id):
        """
        Delete a file export configuration by external UUID

        :param uuid.UUID config_id: the ID of the config to delete
        """
        with closing(self.con.cursor()) as cur:
            cur.execute('DELETE FROM t_exportConfig c WHERE c.exportConfigId = (?)', (config_id.bytes,))
        self.con.commit()

    def get_export_configuration(self, config_id):
        """
        Retrieve the ExportConfiguration with the given ID
        
        :param uuid.UUID config_id:
            ID for which to search
        :return:
            a :class:`meteorpi_model.ExportConfiguration` or None, or no match was found.
        """
        sql = (
            'SELECT internalID, exportConfigID, exportType, searchString, targetURL, '
            'targetUser, targetPassword, exportName, description, active '
            'FROM t_exportConfig WHERE exportConfigID = (?)')
        return _first_from_generator(self._export_configuration_generator(sql=sql, sql_args=(config_id.bytes,)))

    def get_export_configurations(self):
        """
        Retrieve all ExportConfigurations held in this db

        :return: a list of all :class:`meteorpi_model.ExportConfiguration` on this server
        """
        sql = (
            'SELECT internalID, exportConfigID, exportType, searchString, targetURL, '
            'targetUser, targetPassword, exportName, description, active '
            'FROM t_exportConfig ORDER BY internalID DESC')
        return list(self._export_configuration_generator(sql=sql, sql_args=[]))

    def mark_entities_to_export(self, export_config):
        """
        Apply the specified :class:`meteorpi_model.ExportConfiguration` to the database, running its contained query and
        creating rows in t_eventExport or t_fileExport for matching entities.

        :param ExportConfiguration export_config:
            An instance of :class:`meteorpi_model.ExportConfiguration` to apply.
        """
        # Retrieve the internal ID of the export configuration, failing if it hasn't been stored
        with closing(self.con.cursor()) as cur:
            cur.execute('SELECT internalID FROM t_exportConfig WHERE exportConfigID = (?)',
                        (export_config.config_id.bytes,))
            export_config_id = cur.fetchone()[0]
            if export_config_id is None:
                raise ValueError("Attempt to run export on ExportConfiguration not in database")
        # If the export is inactive then do nothing
        if not export_config.enabled:
            return 0
        # The timestamp that will be used when creating new export entries
        timestamp = mp.utc_datetime_to_milliseconds(mp.now())
        # Track the number of rows created, return it later
        rows_created = 0
        # Handle EventSearch
        if isinstance(export_config.search, mp.EventSearch):
            # Create a deep copy of the search and set the properties required when creating exports
            search = mp.EventSearch.from_dict(export_config.search.as_dict())
            search.exclude_incomplete = True
            search.exclude_export_to = export_config.config_id
            b = _search_events_sql_builder(search)
            with closing(self.con.cursor()) as read_cursor, closing(self.con.cursor()) as write_cursor:
                read_cursor.execute(b.get_select_sql(columns='e.internalID'), b.sql_args)
                for (internalID,) in read_cursor:
                    write_cursor.execute('INSERT INTO t_eventExport '
                                         '(eventID, exportConfig, exportTime, exportState) '
                                         'VALUES (?,?,?,?)',
                                         (internalID, export_config_id, timestamp, 1))
                    rows_created += 1
            self.con.commit()
        # Handle FileRecordSearch
        elif isinstance(export_config.search, mp.FileRecordSearch):
            # Create a deep copy of the search and set the properties required when creating exports
            search = mp.FileRecordSearch.from_dict(export_config.search.as_dict())
            search.exclude_incomplete = True
            search.exclude_events = True
            search.exclude_export_to = export_config.config_id
            b = _search_files_sql_builder(search)
            with closing(self.con.cursor()) as read_cursor, closing(self.con.cursor()) as write_cursor:
                read_cursor.execute(b.get_select_sql(columns='f.internalID'), b.sql_args)
                for (internalID,) in read_cursor:
                    write_cursor.execute('INSERT INTO t_fileExport '
                                         '(fileID, exportConfig, exportTime, exportState) '
                                         'VALUES (?,?,?,?)',
                                         (internalID, export_config_id, timestamp, 1))
                    rows_created += 1
            self.con.commit()
        # Complain if it's anything other than these two (nothing should be at the moment but we might introduce
        # more search types in the future
        else:
            raise ValueError("Unknown search type")
        return rows_created

    def get_next_entity_to_export(self):
        """
        Examines the t_fileExport and t_eventExport tables, finds the earliest incomplete export task and builds
        either a :class:`meteorpi_fdb.FileExportTask` or a :class:`meteorpi_fdb.EventExportTask` as appropriate. These
        task objects can be used to retrieve the underlying entity and export configuration, and to update the
        completion state or push the timestamp into the future, deferring evaluation of the task until later. Only
        considers tasks where the timestamp is before (or equal to) the current time.
        :return:
            Either None, if no exports are available, or a :class:`meteorpi_fdb.FileExportTask` or
            :class:`meteorpi_fdb.EventExportTask` depending on whether a file or event is next in the queue to export.
        """
        entity_type = None
        config_id = None
        entity_id = None
        timestamp = None
        config_internal_id = None
        entity_internal_id = None
        status = None
        target_url = None
        target_user = None
        target_password = None
        current_timestamp = mp.utc_datetime_to_milliseconds(mp.now())
        with closing(self.con.cursor()) as cur:
            # Try to retrieve the earliest record in t_eventExport
            cur.execute('SELECT c.exportConfigID, e.eventID, x.exportTime, x.eventID, x.exportConfig, x.exportState, '
                        'c.targetURL, c.targetUser, c.targetPassword '
                        'FROM t_eventExport x, t_exportConfig C, t_event e '
                        'WHERE x.exportConfig = c.internalID AND x.eventID = e.internalID '
                        'AND c.active = 1 '
                        'AND x.exportState > 0 '
                        'AND x.exportTime <= (?)'
                        'ORDER BY x.exportTime ASC, x.eventID ASC '
                        'ROWS 1', (current_timestamp,))
            row = cur.fetchone()
            if row is not None:
                entity_type = 'event'
                config_id = uuid.UUID(bytes=row[0])
                entity_id = uuid.UUID(bytes=row[1])
                timestamp = row[2]
                entity_internal_id = row[3]
                config_internal_id = row[4]
                status = row[5]
                target_url = row[6]
                target_user = row[7]
                target_password = row[8]
            # Similar operation for t_fileExport
            cur.execute('SELECT c.exportConfigID, f.fileID, x.exportTime, x.fileID, x.exportConfig, x.exportState, '
                        'c.targetURL, c.targetUser, c.targetPassword '
                        'FROM t_fileExport x, t_exportConfig c, t_file f '
                        'WHERE x.exportConfig = C.internalID AND x.fileID = f.internalID '
                        'AND c.active = 1 '
                        'AND x.exportState > 0 '
                        'AND x.exportTime <= (?)'
                        'ORDER BY x.exportTime ASC, x.fileID ASC '
                        'ROWS 1', (current_timestamp,))
            row = cur.fetchone()
            if row is not None:
                if timestamp is None or row[2] < timestamp:
                    entity_type = 'file'
                    config_id = uuid.UUID(bytes=row[0])
                    entity_id = uuid.UUID(bytes=row[1])
                    timestamp = row[2]
                    entity_internal_id = row[3]
                    config_internal_id = row[4]
                    status = row[5]
                    target_url = row[6]
                    target_user = row[7]
                target_password = row[8]
        if entity_type is None:
            return None
        elif entity_type == 'file':
            return FileExportTask(db=self, config_id=config_id, config_internal_id=config_internal_id,
                                  file_id=entity_id, file_internal_id=entity_internal_id, timestamp=timestamp,
                                  status=status, target_url=target_url, target_user=target_user,
                                  target_password=target_password)
        elif entity_type == 'event':
            return EventExportTask(db=self, config_id=config_id, config_internal_id=config_internal_id,
                                   event_id=entity_id, event_internal_id=entity_internal_id, timestamp=timestamp,
                                   status=status, target_url=target_url, target_user=target_user,
                                   target_password=target_password)
        else:
            raise ValueError("Unknown entity type, should never see this!")

    def get_cameras(self):
        """
        Retrieve the IDs of all cameras with active status blocks.

        :return:
            A list of camera IDs for all cameras with status blocks where the 'validTo' date is null
        """
        with closing(self.con.cursor()) as cur:
            cur.execute(
                'SELECT DISTINCT cameraID FROM t_cameraStatus '
                'WHERE validTo IS NULL ORDER BY cameraID DESC')
            return map(lambda row: row[0], cur.fetchall())

    def update_camera_status(self, ns, time=None, camera_id=get_installation_id()):
        """
        Update the status for this installation's camera, optionally specify a
        time (defaults to datetime.now()).

        If the time is earlier than the current high water mark for this
        camera any data products derived after that time will be deleted
        as if setHighWaterMark was called.
        """
        if time is None:
            time = mp.now()
        # Set the high water mark, allowing it to advance to this point or to rollback if
        # we have data products produced after this status' time.
        self.set_high_water_mark(camera_id=camera_id, time=time, allow_rollback=True, allow_advance=True)
        with closing(self.con.cursor()) as cur:
            # If there's an existing status block then set its end time to now
            cur.execute(
                'UPDATE t_cameraStatus t SET t.validTo = (?) '
                'WHERE t.validTo IS NULL AND t.cameraID = (?)',
                (mp.utc_datetime_to_milliseconds(time),
                 camera_id))
            # Insert the new status into the database
            cur.execute(
                'INSERT INTO t_cameraStatus (cameraID, validFrom, validTo, '
                'softwareVersion, orientationAltitude, orientationAzimuth, '
                'orientationRotation, orientationError, widthOfField, locationLatitude, locationLongitude, '
                'locationGPS, lens, sensor, instURL, instName, locationError) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) '
                'RETURNING internalID',
                (camera_id,
                 mp.utc_datetime_to_milliseconds(time),
                 None,
                 SOFTWARE_VERSION,
                 ns.orientation.altitude,
                 ns.orientation.azimuth,
                 ns.orientation.rotation,
                 ns.orientation.error,
                 ns.orientation.width_of_field,
                 ns.location.latitude,
                 ns.location.longitude,
                 ns.location.gps,
                 ns.lens,
                 ns.sensor,
                 ns.inst_url,
                 ns.inst_name,
                 ns.location.error))
            # Retrieve the newly created internal ID for the status block, use this to
            # insert visible regions
            status_internal_id = cur.fetchone()[0]
            for region_index, region in enumerate(ns.regions):
                for point_index, point in enumerate(region):
                    cur.execute(
                        'INSERT INTO t_visibleRegions (cameraStatusID, '
                        'region, pointOrder, x, y) VALUES (?,?,?,?,?)',
                        (status_internal_id,
                         region_index,
                         point_index,
                         point['x'],
                         point['y']))
            self.con.commit()

    def _get_camera_status_id(
            self,
            time=None,
            camera_id=get_installation_id()):
        """Return the integer internal ID and UUID of the camera status block for the
        given time and camera, or None if there wasn't one."""
        if time is None:
            time = mp.now()
        with closing(self.con.cursor()) as cur:
            cur.execute(
                'SELECT internalID, statusID FROM t_cameraStatus t '
                'WHERE t.cameraID = (?) AND t.validFrom <= (?) '
                'AND (t.validTo IS NULL OR t.validTo > (?))',
                (camera_id, mp.utc_datetime_to_milliseconds(time), mp.utc_datetime_to_milliseconds(time)))
            row = cur.fetchone()
            if row is None:
                return None
            return {'internal_id': row[0], 'status_id': uuid.UUID(bytes=row[1])}

    def get_camera_status(
            self,
            time=None,
            camera_id=get_installation_id()):
        """Return the camera status for a given time, or None if no status is
        available time : datetime.datetime object, default now."""
        if time is None:
            time = mp.now()
        with closing(self.con.cursor()) as cur:
            cur.execute(
                'SELECT lens, sensor, instURL, instName, locationLatitude, '
                'locationLongitude, locationGPS, locationError, orientationAltitude, '
                'orientationAzimuth, orientationError, orientationRotation, widthOfField, validFrom, validTo, '
                'softwareVersion, internalID, statusID '
                'FROM t_cameraStatus t '
                'WHERE t.cameraID = (?) AND t.validFrom <= (?) '
                'AND (t.validTo IS NULL OR t.validTo > (?))',
                (camera_id,
                 mp.utc_datetime_to_milliseconds(time),
                 mp.utc_datetime_to_milliseconds(time)))
            row = cur.fetchonemap()
            if row is None:
                return None
            cs = mp.CameraStatus(lens=row['lens'],
                                 sensor=row['sensor'],
                                 inst_url=row['instURL'],
                                 inst_name=row['instName'],
                                 orientation=mp.Orientation(
                                     altitude=row['orientationAltitude'],
                                     azimuth=row['orientationAzimuth'],
                                     rotation=row['orientationRotation'],
                                     error=row['orientationError'],
                                     width_of_field=row['widthOfField']),
                                 location=mp.Location(
                                     latitude=row['locationLatitude'],
                                     longitude=row['locationLongitude'],
                                     gps=row['locationGPS'] is True,
                                     error=row['locationError']),
                                 camera_id=camera_id,
                                 status_id=uuid.UUID(bytes=row['statusID']))
            cs.valid_from = mp.milliseconds_to_utc_datetime(row['validFrom'])
            cs.valid_to = mp.milliseconds_to_utc_datetime(row['validTo'])
            cs.software_version = row['softwareVersion']
            camera_status_id = row['internalID']
            cur.execute('SELECT region, pointOrder, x, y FROM t_visibleRegions t '
                        'WHERE t.cameraStatusID = (?) '
                        'ORDER BY region ASC, pointOrder ASC', [camera_status_id])
            for point in cur.fetchallmap():
                if len(cs.regions) <= point['region']:
                    cs.regions.append([])
                cs.regions[point['region']].append(
                    {'x': point['x'], 'y': point['y']})
            return cs

    def get_high_water_mark(self, camera_id=get_installation_id()):
        """Retrieves the current high water mark for a camera installation, or
        None if none has been set."""
        with closing(self.con.cursor()) as cur:
            cur.execute(
                'SELECT mark FROM t_highWaterMark t WHERE t.cameraID = (?)',
                (camera_id,))
            row = cur.fetchone()
            if row is None:
                return None
            return mp.milliseconds_to_utc_datetime(row[0])

    def set_high_water_mark(self, time, camera_id=get_installation_id(), allow_rollback=True, allow_advance=True):
        """
        Sets the 'high water mark' for this installation.

        This is the latest point before which all data has been
        processed, when this call is made any data products (events,
        images etc) with time stamps later than the high water mark will
        be removed from the database. Any camera status blocks with
        validFrom dates after the high water mark will be removed, and
        any status blocks with validTo dates after the high water mark
        will have their validTo set to None to make them current
        """
        last = self.get_high_water_mark(camera_id)
        if last is None and allow_advance:
            # No high water mark defined, set it and return
            with closing(self.con.cursor()) as cur:
                cur.execute(
                    'INSERT INTO t_highWaterMark (cameraID, mark) VALUES (?,?)',
                    (camera_id,
                     mp.utc_datetime_to_milliseconds(time)))
        elif last is not None and last < time and allow_advance:
            # Defined, but new one is later, we don't really have to do much
            with closing(self.con.cursor()) as cur:
                cur.execute(
                    'UPDATE t_highWaterMark t SET t.mark = (?) WHERE t.cameraID = (?)',
                    (mp.utc_datetime_to_milliseconds(time),
                     camera_id))
        elif last is not None and last > time and allow_rollback:
            # More complicated, we're rolling back time so need to clean up a load
            # of future data
            with closing(self.con.cursor()) as read_cursor, closing(self.con.cursor()) as update_cursor:
                read_cursor.execute(
                    'SELECT fileID AS file_id FROM t_file '
                    'WHERE fileTime > (?) AND cameraID = (?) FOR UPDATE',
                    (mp.utc_datetime_to_milliseconds(time), camera_id))
                read_cursor.name = "read_cursor"
                for (file_id,) in read_cursor:
                    update_cursor.execute("DELETE FROM t_file WHERE CURRENT OF read_cursor")
                    file_path = path.join(self.file_store_path, uuid.UUID(bytes=file_id).hex)
                    try:
                        os.remove(file_path)
                    except OSError:
                        print "Warning: could not remove file {0}.".format(file_path)
                update_cursor.execute(
                    "DELETE FROM t_event WHERE eventTime > (?) AND cameraID = (?)",
                    (mp.utc_datetime_to_milliseconds(time), camera_id))
                update_cursor.execute(
                    'UPDATE t_highWaterMark t SET t.mark = (?) WHERE t.cameraID = (?)',
                    (mp.utc_datetime_to_milliseconds(time), camera_id))
                # Delete future status blocks
                update_cursor.execute(
                    'DELETE FROM t_cameraStatus t '
                    'WHERE t.validFrom > (?) AND t.cameraID = (?)',
                    (mp.utc_datetime_to_milliseconds(time), camera_id))
                # Set the new current camera status block
                update_cursor.execute(
                    'UPDATE t_cameraStatus t SET t.validTo = NULL '
                    'WHERE t.validTo >= (?) AND t.cameraID = (?)',
                    (mp.utc_datetime_to_milliseconds(time), camera_id))
        self.con.commit()

    def get_user(self, user_id, password):
        """
        Retrieve a user record

        :param user_id:
            the user ID
        :param password:
            password
        :return:
            null if the specified user isn't found, a User if everything is correct
        :raises:
            ValueError if the user is found but password is incorrect
        """
        with closing(self.con.cursor()) as cur:
            cur.execute('SELECT userID, pwHash, roleMask FROM t_user WHERE userID = (?)', (user_id,))
            row = cur.fetchonemap()
            if row is None:
                return None
            pw_hash = row['pwHash']
            role_mask = row['roleMask']
            # Check the password
            if pbkdf2_sha256.verify(password, pw_hash):
                return mp.User(user_id=user_id, role_mask=role_mask)
            else:
                raise ValueError("Incorrect password")

    def get_users(self):
        with closing(self.con.cursor()) as cur:
            cur.execute('SELECT userID, roleMask FROM t_user ORDER BY userID ASC')
            return list(mp.User(user_id=row['userID'], role_mask=row['roleMask']) for row in cur.fetchallmap())

    def create_or_update_user(self, user_id, password, roles):
        """
        Create a new user record, or update an existing one

        :param user_id:
            user ID to update or create
        :param password:
            new password, or None to leave unchanged
        :param roles:
            new roles, or None to leave unchanged
        :return:
            the action taken, one of "none", "update", "create"
        :raises:
            ValueError if there is no existing user and either password or roles is None
        """
        if password is None and roles is None:
            return "none"
        with closing(self.con.cursor()) as cur:
            if password is not None:
                cur.execute('UPDATE t_user SET pwHash = (?) WHERE userID = (?)',
                            (pbkdf2_sha256.encrypt(password), user_id))
            if roles is not None:
                cur.execute('UPDATE t_user SET roleMask = (?) WHERE userID = (?)',
                            (mp.User.role_mask_from_roles(roles), user_id))
            if cur.rowcount == 0:
                if password is None:
                    raise ValueError("Must specify both password when creating a user!")
                if roles is None:
                    roles = ['user']
                cur.execute('INSERT INTO t_user (userID, pwHash, roleMask) VALUES (?, ?, ?)',
                            (user_id, pbkdf2_sha256.encrypt(password), mp.User.role_mask_from_roles(roles)))
                self.con.commit()
                return "create"
            else:
                self.con.commit()
                return "update"

    def delete_user(self, user_id):
        with closing(self.con.cursor()) as cur:
            cur.execute('DELETE FROM t_user WHERE userID = (?)', (user_id,))
            self.con.commit()

    def clear_database(self):
        """
        Delete ALL THE THINGS!

        This doesn't reset any internal counters used to generate IDs
        but does otherwise remove all data from the database. Also
        purges all files from the fileStore
        """
        # Purge tables - other tables are deleted by foreign key cascades from these ones.
        with closing(self.con.cursor()) as cur:
            cur.execute('DELETE FROM t_cameraStatus')
            cur.execute('DELETE FROM t_highWaterMark')
            cur.execute('DELETE FROM t_user')
            cur.execute('DELETE FROM t_exportConfig')
        self.con.commit()
        shutil.rmtree(self.file_store_path)
        os.makedirs(self.file_store_path)


class EventExportTask(object):
    """
    Represents a single active Event export, providing methods to get the underlying :class:`meteorpi_model.Event`,
    the :class:`meteorpi_model.ExportConfiguration` and to update the completion state in the database.
    """

    def __init__(self, db, config_id, config_internal_id, event_id, event_internal_id, timestamp, status, target_url,
                 target_user, target_password):
        self.db = db
        self.config_id = config_id
        self.config_internal_id = config_internal_id
        self.event_id = event_id
        self.event_internal_id = event_internal_id
        self.timestamp = timestamp
        self.status = status
        self.target_url = target_url
        self.target_user = target_user
        self.target_password = target_password

    def get_event(self):
        return self.db.get_event(self.event_id)

    def get_export_config(self):
        return self.db.get_export_configuartion(self.config_id)

    def set_status(self, status):
        with closing(self.db.con.cursor()) as cur:
            cur.execute('UPDATE t_eventExport x '
                        'SET x.exportState = (?) '
                        'WHERE x.eventID = (?) AND x.exportConfig = (?)',
                        (status, self.event_internal_id, self.config_internal_id))
        self.db.con.commit()


class FileExportTask(object):
    """
    Represents a single active FileRecord export, providing methods to get the underlying
    :class:`meteorpi_model.FileRecord`, the :class:`meteorpi_model.ExportConfiguration` and to update the completion
    state in the database.
    """

    def __init__(self, db, config_id, config_internal_id, file_id, file_internal_id, timestamp, status, target_url,
                 target_user, target_password):
        self.db = db
        self.config_id = config_id
        self.config_internal_id = config_internal_id
        self.file_id = file_id
        self.file_internal_id = file_internal_id
        self.timestamp = timestamp
        self.status = status
        self.target_url = target_url
        self.target_user = target_user
        self.target_password = target_password

    def get_file(self):
        return self.db.get_file(self.file_id)

    def get_export_config(self):
        return self.db.get_export_configuartion(self.config_id)

    def set_status(self, status):
        with closing(self.db.con.cursor()) as cur:
            cur.execute('UPDATE t_fileExport x '
                        'SET x.exportState = (?) '
                        'WHERE x.fileID = (?) AND x.exportConfig = (?)',
                        (status, self.file_internal_id, self.config_internal_id))
        self.db.con.commit()
