__author__ = 'tom'

import uuid
import datetime

import meteorpi_model as mp


def search_events_sql_builder(search):
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
    if search.exclude_imported:
        b.where_clauses.append('NOT EXISTS (SELECT * FROM t_eventImport i WHERE i.eventID = e.internalID')
    if search.exclude_export_to is not None:
        b.where_clauses.append('NOT EXISTS (SELECT * FROM t_eventExport ex, t_exportConfig c '
                               'WHERE ex.eventID = e.internalID '
                               'AND ex.exportConfig = c.internalID '
                               'AND c.exportConfigID = (?))')
        b.sql_args.append(SQLBuilder.map_value(search.exclude_export_to))
    return b


def search_files_sql_builder(search):
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
    if search.exclude_imported:
        b.where_clauses.append('NOT EXISTS (SELECT * FROM t_fileImport i WHERE i.fileID = f.internalID')
    if search.exclude_export_to is not None:
        b.where_clauses.append('NOT EXISTS (SELECT * FROM t_fileExport e, t_exportConfig c '
                               'WHERE e.fileID = f.internalID '
                               'AND e.exportConfig = c.internalID '
                               'AND c.exportConfigID = (?))')
        b.sql_args.append(SQLBuilder.map_value(search.exclude_export_to))
    return b


class SQLBuilder(object):
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
