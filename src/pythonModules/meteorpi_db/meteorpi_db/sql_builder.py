# sql_builder.py

# Helper functions to build SQL queries


def search_observations_sql_builder(search):
    """
    Create and populate an instance of :class:`meteorpi_db.SQLBuilder` for a given
    :class:`meteorpi_model.ObservationSearch`. This can then be used to retrieve the results of the search, materialise
    them into :class:`meteorpi_model.Observation` instances etc.

    :param ObservationSearch search:
        The search to realise
    :return:
        A :class:`meteorpi_db.SQLBuilder` configured from the supplied search
    """
    b = SQLBuilder(tables="""archive_observations o
INNER JOIN archive_semanticTypes s ON o.obsType=s.uid
INNER JOIN archive_observatories l ON o.observatory=l.uid""", where_clauses=[])
    b.add_set_membership(search.obstory_ids, 'l.publicId')
    b.add_sql(search.observation_type, 's.name = %s')
    b.add_sql(search.observation_id, 'o.publicId = %s')
    b.add_sql(search.time_min, 'o.obsTime > %s')
    b.add_sql(search.time_max, 'o.obsTime < %s')
    b.add_sql(search.lat_min, 'l.latitude >= %s')
    b.add_sql(search.lat_max, 'l.latitude <= %s')
    b.add_sql(search.long_min, 'l.longitude >= %s')
    b.add_sql(search.long_max, 'l.longitude <= %s')
    b.add_metadata_query_properties(meta_constraints=search.meta_constraints, id_column="observationId", id_table="o")

    # Check for import / export filters
    if search.exclude_imported:
        b.where_clauses.append('NOT EXISTS (SELECT * FROM archive_observationImport i WHERE i.observationId = o.uid')
    if search.exclude_export_to is not None:
        b.where_clauses.append("""
        NOT EXISTS (SELECT * FROM archive_observationExport ex
        INNER JOIN archive_exportConfig c ON ex.exportConfig = c.uid
        WHERE ex.observationId = o.uid  AND c.exportConfigID = %s)
        """)
        b.sql_args.append(SQLBuilder.map_value(search.exclude_export_to))
    return b

def search_obsgroups_sql_builder(search):
    """
    Create and populate an instance of :class:`meteorpi_db.SQLBuilder` for a given
    :class:`meteorpi_model.ObservationGroupSearch`. This can then be used to retrieve the results of the search,
    materialise them into :class:`meteorpi_model.ObservationGroup` instances etc.

    :param ObservationGroupSearch search:
        The search to realise
    :return:
        A :class:`meteorpi_db.SQLBuilder` configured from the supplied search
    """
    b = SQLBuilder(tables="""archive_obs_groups g
INNER JOIN archive_semanticTypes s ON g.obsType=s.uid""", where_clauses=[])
    b.add_sql(search.obstory_name, """
EXISTS (SELECT 1 FROM archive_obs_group_members x1
INNER JOIN archive_observations x2 ON x2.uid=x1.observationId
INNER JOIN archive_observatories x3 ON x3.uid=x2.observatory
WHERE x1.groupId=g.uid AND x3.publicId=%s)""")
    b.add_sql(search.observation_id, """
EXISTS (SELECT 1 FROM archive_obs_group_members y1
INNER JOIN archive_observations y2 ON y2.uid=y1.observationId
WHERE y1.groupId=g.uid AND y2.publicId=%s)""")
    b.add_sql(search.group_id, 'g.publicId = %s')
    b.add_sql(search.time_min, 'g.obsTime > %s')
    b.add_sql(search.time_max, 'g.obsTime < %s')
    b.add_metadata_query_properties(meta_constraints=search.meta_constraints, id_column="groupId", id_table="g")
    return b

def search_files_sql_builder(search):
    """
    Create and populate an instance of :class:`meteorpi_db.SQLBuilder` for a given
    :class:`meteorpi_model.FileRecordSearch`. This can then be used to retrieve the results of the search, materialise
    them into :class:`meteorpi_model.FileRecord` instances etc.

    :param FileRecordSearch search:
        The search to realise
    :return:
        A :class:`meteorpi_db.SQLBuilder` configured from the supplied search
    """
    b = SQLBuilder(tables="""archive_files f
INNER JOIN archive_semanticTypes s2 ON f.semanticType=s2.uid
INNER JOIN archive_observations o ON f.observationId=o.uid
INNER JOIN archive_semanticTypes s ON o.obsType=s.uid
INNER JOIN archive_observatories l ON o.observatory=l.uid""", where_clauses=[])
    b.add_set_membership(search.obstory_ids, 'l.publicId')
    b.add_sql(search.repository_fname, 'f.repositoryFname = %s')
    b.add_sql(search.observation_type, 's.name = %s')
    b.add_sql(search.observation_id, 'o.uid = %s')
    b.add_sql(search.time_min, 'f.fileTime > %s')
    b.add_sql(search.time_max, 'f.fileTime < %s')
    b.add_sql(search.lat_min, 'l.latitude >= %s')
    b.add_sql(search.lat_max, 'l.latitude <= %s')
    b.add_sql(search.long_min, 'l.longitude >= %s')
    b.add_sql(search.long_max, 'l.longitude <= %s')
    b.add_sql(search.mime_type, 'f.mimeType = %s')
    b.add_sql(search.semantic_type, 's2.name = %s')
    b.add_metadata_query_properties(meta_constraints=search.meta_constraints, id_column="fileId", id_table="f")

    # Check for import / export filters
    if search.exclude_imported:
        b.where_clauses.append('NOT EXISTS (SELECT * FROM archive_observationImport i WHERE i.observationId = o.uid')
    if search.exclude_export_to is not None:
        b.where_clauses.append("""
        NOT EXISTS (SELECT * FROM archive_observationExport ex
        INNER JOIN archive_exportConfig c ON ex.exportConfig = c.uid
        WHERE ex.observationId = o.uid  AND c.exportConfigID = %s)
        """)
        b.sql_args.append(SQLBuilder.map_value(search.exclude_export_to))

    return b


def search_metadata_sql_builder(search):
    """
    Create and populate an instance of :class:`meteorpi_db.SQLBuilder` for a given
    :class:`meteorpi_model.ObservatoryMetadataSearch`. This can then be used to retrieve the results of the search,
    materialise them into :class:`meteorpi_model.ObservatoryMetadata` instances etc.

    :param ObservatoryMetadataSearch search:
        The search to realise
    :return:
        A :class:`meteorpi_db.SQLBuilder` configured from the supplied search
    """
    b = SQLBuilder(tables="""archive_metadata m
INNER JOIN archive_metadataFields f ON m.fieldId=f.uid
INNER JOIN archive_observatories l ON m.observatory=l.uid""", where_clauses=["m.observatory IS NOT NULL"])
    b.add_set_membership(search.obstory_ids, 'l.publicId')
    b.add_sql(search.field_name, 'f.metaKey = %s')
    b.add_sql(search.time_min, 'm.time > %s')
    b.add_sql(search.time_max, 'm.time < %s')
    b.add_sql(search.lat_min, 'l.latitude >= %s')
    b.add_sql(search.lat_max, 'l.latitude <= %s')
    b.add_sql(search.long_min, 'l.longitude >= %s')
    b.add_sql(search.long_max, 'l.longitude <= %s')
    b.add_sql(search.item_id, 'm.publicId = %s')

    # Check for import / export filters
    if search.exclude_imported:
        b.where_clauses.append('NOT EXISTS (SELECT * FROM archive_metadataImport i WHERE i.metadataId = m.uid')
    if search.exclude_export_to is not None:
        b.where_clauses.append("""
        NOT EXISTS (SELECT * FROM archive_metadataExport ex
        INNER JOIN archive_exportConfig c ON ex.exportConfig = c.uid
        WHERE ex.metadataId = m.uid AND c.exportConfigID = %s)
        """)
        b.sql_args.append(SQLBuilder.map_value(search.exclude_export_to))

    return b


class SQLBuilder(object):
    """
    Helper class to make it easier to build large, potentially complex, SQL clauses.

    This class contains various methods to allow SQL queries to be built without having to manage enormous strings of
    SQL. It includes facilities to add metadata constraints. Also helps simplify the discovery and
    debugging of issues with generated queries as we can pull out the query strings directly from this object.
    """

    def __init__(self, tables, where_clauses=None):
        """
        Construct a new, empty, SQLBuilder

        :param where_clauses:
            Optionally specify an initial array of WHERE clauses, defaults to an empty sequence. Clauses specified here
            must not include the string 'WHERE', but should be e.g. ['e.statusID = s.internalID']
        :param tables:
            A SQL fragment defining the tables used by this SQLBuilder, e.g. 't_file f'
        :ivar where_clauses:
            A list of strings of SQL, which will be prefixed by 'WHERE' to construct a constraint. As with the init
            parameter these will not include the 'WHERE' itself.
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
            The mapped value.
        """
        if value is None:
            return None
        else:
            return value

    def add_sql(self, value, clause):
        """
        Add a WHERE clause to the state.

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
            question_marks = ', '.join(["%s"] * len(values))
            self.where_clauses.append('{0} IN ({1})'.format(column_name, question_marks))
            for value in values:
                self.sql_args.append(SQLBuilder.map_value(value))

    def add_metadata_query_properties(self, meta_constraints, id_table, id_column):
        """
        Construct WHERE clauses from a list of MetaConstraint objects, adding them to the query state.

        :param meta_constraints:
            A list of MetaConstraint objects, each of which defines a condition over metadata which must be satisfied
            for results to be included in the overall query.
        :raises:
            ValueError if an unknown meta constraint type is encountered.
        """
        for mc in meta_constraints:
            meta_key = str(mc.key)
            ct = mc.constraint_type
            sql_template = """
{0}.uid IN (
SELECT m.{1} FROM archive_metadata m
INNER JOIN archive_metadataFields k ON m.fieldId=k.uid
WHERE m.{2} {3} %s AND k.metaKey = %s
)"""
            # Add metadata value to list of SQL arguments
            self.sql_args.append(SQLBuilder.map_value(mc.value))
            # Add metadata key to list of SQL arguments
            self.sql_args.append(meta_key)
            # Put an appropriate WHERE clause
            if ct == 'less':
                self.where_clauses.append(sql_template.format(id_table, id_column, 'floatValue', '<='))
            elif ct == 'greater':
                self.where_clauses.append(sql_template.format(id_table, id_column, 'floatValue', '>='))
            elif ct == 'number_equals':
                self.where_clauses.append(sql_template.format(id_table, id_column, 'floatValue', '='))
            elif ct == 'string_equals':
                self.where_clauses.append(sql_template.format(id_table, id_column, 'stringValue', '='))
            else:
                raise ValueError("Unknown meta constraint type!")

    def get_select_sql(self, columns, order=None, limit=0, skip=0):
        """
        Build a SELECT query based on the current state of the builder.

        :param columns:
            SQL fragment describing which columns to select i.e. 'e.obstoryID, s.statusID'
        :param order:
            Optional ordering constraint, i.e. 'e.eventTime DESC'
        :param limit:
            Optional, used to build the 'LIMIT n' clause. If not specified no limit is imposed.
        :param skip:
            Optional, used to build the 'OFFSET n' clause. If not specified results are returned from the first item
            available. Note that this parameter must be combined with 'order', otherwise there's no ordering imposed
            on the results and subsequent queries may return overlapping data randomly. It's unlikely that this will
            actually happen as almost all databases do in fact create an internal ordering, but there's no guarantee
            of this (and some operations such as indexing will definitely break this property unless explicitly set).
        :returns:
            A SQL SELECT query, which will make use of self.sql_args when executed.
        """
        sql = 'SELECT '
        sql += '{0} FROM {1} WHERE '.format(columns, self.tables)
        sql += ' AND '.join(self.where_clauses)
        if order is not None:
            sql += ' ORDER BY {0}'.format(order)
        if limit > 0:
            sql += ' LIMIT {0} '.format(limit)
        if skip > 0:
            sql += ' OFFSET {0} '.format(skip)
        return sql

    def get_count_sql(self):
        """
        Build a SELECT query which returns the count of items for an unlimited SELECT

        :return:
            A SQL SELECT query which returns the count of items for an unlimited query based on this SQLBuilder
        """
        return 'SELECT COUNT(*) FROM ' + self.tables + ' WHERE ' + (' AND '.join(self.where_clauses))
