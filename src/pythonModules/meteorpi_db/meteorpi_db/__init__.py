# meteorpi_db
# Meteor Pi, Cambridge Science Centre
# Dominic Ford, Tom Oinn

# Classes which interact with the Meteor Pi database

import os
import sys
import MySQLdb
import shutil
import json
import numbers

from passlib.hash import pbkdf2_sha256
import meteorpi_model as mp
from meteorpi_db.generators import first_from_generator, MeteorDatabaseGenerators
from meteorpi_db.sql_builder import search_observations_sql_builder, search_files_sql_builder, \
    search_metadata_sql_builder, search_obsgroups_sql_builder
from meteorpi_db.exporter import ObservationExportTask, FileExportTask, MetadataExportTask

SOFTWARE_VERSION = 2


class MeteorDatabase(object):
    """
    Class representing a single Meteor Pi database and file store.

    :ivar con:
        Database connection used to access the db
    :ivar db_host:
        Host of the database
    :ivar db_user:
        User login to the database
    :ivar db_password:
        Password for the database
    :ivar db_name:
        Database name
    :ivar file_store_path:
        Path to the file store on disk
    :ivar string obstory_id:
        The local obstory ID
    :ivar object generator:
        Object generator class
    """

    def __init__(self, file_store_path, db_host='localhost', db_user='meteorpi', db_password='meteorpi',
                 db_name='meteorpi', obstory_name='Undefined'):
        """
        Create a new db instance. This connects to the specified firebird database and retains a connection which is
        then used by methods in this class when querying or updating the database.

        :param file_store_path:
            Path to the file store on disk
        :param db_host:
            Host of the database
        :param db_user:
            User login to the database
        :param db_password:
            Password for the database
        :param db_name:
            Database name
        :param string obstory_name:
            The local obstory ID
        """
        self.db = MySQLdb.connect(host=db_host, user=db_user, passwd=db_password, db=db_name)
        self.con = self.db.cursor(cursorclass=MySQLdb.cursors.DictCursor)

        if not os.path.exists(file_store_path):
            os.makedirs(file_store_path)
        if not os.path.isdir(file_store_path):
            raise ValueError('File store path already exists but is not a directory!')
        self.file_store_path = file_store_path
        self.db_host = db_host
        self.db_user = db_user
        self.db_password = db_password
        self.db_name = db_name
        self.obstory_name = obstory_name
        self.generators = MeteorDatabaseGenerators(db=self, con=self.con)

    def __str__(self):
        """Simple string representation of this db object

        :return:
            info about the db path and file store location
        """
        return ('MeteorDatabase(file_store_path={0}, db_path={1}, db_host={2}, db_user={3}, db_password={4}, '
                'db_name={5}, obstory_name={6})'.format(
                self.file_store_path,
                self.db_host,
                self.db_user,
                self.db_password,
                self.db_name,
                self.obstory_name))

    def commit(self):
        self.db.commit()

    # Functions relating to observatories
    def has_obstory_id(self, obstory_id):
        self.con.execute('SELECT 1 FROM archive_observatories WHERE publicId=%s;', (obstory_id,))
        return len(self.con.fetchall()) > 0

    def has_obstory_name(self, obstory_name):
        self.con.execute('SELECT 1 FROM archive_observatories WHERE name=%s;', (obstory_name,))
        return len(self.con.fetchall()) > 0

    def get_obstory_from_name(self, obstory_name):
        self.con.execute('SELECT * FROM archive_observatories WHERE name=%s;', (obstory_name,))
        results = self.con.fetchall()
        if len(results) < 1:
            raise ValueError("No such obstory: %s" % obstory_name)
        return results[0]

    def get_obstory_from_id(self, obstory_id):
        self.con.execute('SELECT * FROM archive_observatories WHERE publicId=%s;', (obstory_id,))
        results = self.con.fetchall()
        if len(results) < 1:
            raise ValueError("No such obstory: %s" % obstory_id)
        return results[0]

    def register_obstory(self, obstory_id, obstory_name, latitude, longitude):
        self.con.execute("""
INSERT INTO archive_observatories
(publicId, name, latitude, longitude)
VALUES
(%s, %s, %s, %s);
""", (obstory_id, obstory_name, latitude, longitude))
        return obstory_id

    def delete_obstory(self, obstory_name):
        self.con.execute("DELETE FROM archive_observatories WHERE name=%s;", (obstory_name,))

    def get_obstory_ids(self):
        """
        Retrieve the IDs of all obstorys.

        :return:
            A list of obstory IDs for all obstorys
        """
        self.con.execute('SELECT publicId FROM archive_observatories;')
        return map(lambda row: row['publicId'], self.con.fetchall())

    def get_obstory_names(self):
        self.con.execute('SELECT name FROM archive_observatories;')
        return map(lambda row: row['name'], self.con.fetchall())

    # Functions for returning observatory metadata
    def has_obstory_metadata(self, status_id):
        """
        Check for the presence of the given metadata item

        :param string status_id:
            The metadata item ID
        :return:
            True if we have a metadata item with this ID, False otherwise
        """
        self.con.execute('SELECT 1 FROM archive_metadata WHERE publicId=%s;', (status_id,))
        return len(self.con.fetchall()) > 0

    def get_obstory_metadata(self, item_id):
        search = mp.ObservatoryMetadataSearch(item_id=item_id)
        b = search_metadata_sql_builder(search)
        sql = b.get_select_sql(columns='l.publicId AS obstory_id, l.name AS obstory_name, '
                                       'l.latitude AS obstory_lat, l.longitude AS obstory_lng, '
                                       'stringValue, floatValue, m.publicId AS metadata_id, '
                                       'f.metaKey AS metadata_key, time, setAtTime AS time_created, '
                                       'setByUser AS user_created',
                               skip=0, limit=1, order='m.time DESC')
        items = list(self.generators.obstory_metadata_generator(sql=sql, sql_args=b.sql_args))
        if not items:
            return None
        return items[0]

    def search_obstory_metadata(self, search):
        b = search_metadata_sql_builder(search)
        sql = b.get_select_sql(columns='l.publicId AS obstory_id, l.name AS obstory_name, '
                                       'l.latitude AS obstory_lat, l.longitude AS obstory_lng, '
                                       'stringValue, floatValue, m.publicId AS metadata_id, '
                                       'f.metaKey AS metadata_key, time, setAtTime AS time_created, '
                                       'setByUser AS user_created',
                               skip=search.skip,
                               limit=search.limit,
                               order='m.time DESC')
        items = list(self.generators.obstory_metadata_generator(sql=sql, sql_args=b.sql_args))
        rows_returned = len(items)
        total_rows = rows_returned + search.skip
        if (rows_returned == search.limit > 0) or (rows_returned == 0 and search.skip > 0):
            self.con.execute(b.get_count_sql(), b.sql_args)
            total_rows = self.con.fetchone()[0]
        return {"count": total_rows,
                "items": items}

    def register_obstory_metadata(self, obstory_name, key, value, metadata_time, user_created, time_created=None):
        if time_created is None:
            time_created = mp.now()
        obstory = self.get_obstory_from_name(obstory_name)
        item_id = mp.get_hash(metadata_time, obstory['publicId'], key)

        # If new value equals old value, no point re-entering it!
        previous_value = self.lookup_obstory_metadata(key, metadata_time, obstory_name)
        if previous_value == value:
            return None

        self.import_obstory_metadata(obstory['name'], key, value, metadata_time, time_created, user_created, item_id)

        return mp.ObservatoryMetadata(metadata_id=item_id, obstory_id=obstory['uid'], obstory_name=obstory['name'],
                                      obstory_lat=obstory['latitude'], obstory_lng=obstory['longitude'],
                                      key=key, value=value, metadata_time=metadata_time,
                                      time_created=time_created, user_created=user_created)

    def import_obstory_metadata(self, obstory_name, key, value, metadata_time, time_created, user_created, item_id):
        if self.has_obstory_metadata(item_id):
            return

        obstory = self.get_obstory_from_name(obstory_name)
        key_id = self.get_metadata_key_id(key)
        str_value = float_value = None
        if isinstance(value, numbers.Number):
            float_value = value
        else:
            str_value = str(value)

        # Insert into database
        self.con.execute("""
INSERT INTO archive_metadata
(publicId, observatory, fieldId, time, setAtTime, setByUser, stringValue, floatValue)
VALUES
(%s, %s, %s, %s, %s, %s, %s, %s);
""", (item_id, obstory['uid'], key_id, metadata_time, time_created, user_created, str_value, float_value))

    def get_obstory_status(self, time=None, obstory_name=None):
        if time is None:
            time = mp.now()
        if obstory_name is None:
            obstory_name = self.obstory_name
        obstory = self.get_obstory_from_name(obstory_name)

        output = {}

        self.con.execute('SELECT uid,metaKey FROM archive_metadataFields;')
        for item in self.con.fetchall():
            self.con.execute("""
SELECT floatValue, stringValue FROM archive_metadata
WHERE observatory=%s AND fieldId=%s AND time<%s ORDER BY time DESC LIMIT 1
""", (obstory['uid'], item['uid'], time))
            results = self.con.fetchall()
            if len(results) > 0:
                result = results[0]
                if result['stringValue'] is None:
                    value = result['floatValue']
                else:
                    value = result['stringValue']
                output[item['metaKey']] = value
        return output

    def lookup_obstory_metadata(self, key, time=None, obstory_name=None):
        if time is None:
            time = mp.now()
        if obstory_name is None:
            obstory_name = self.obstory_name
        obstory = self.get_obstory_from_name(obstory_name)

        self.con.execute('SELECT uid FROM archive_metadataFields WHERE metaKey=%s;', (key,))
        results = self.con.fetchall()
        if len(results) < 1:
            return None
        self.con.execute("""
SELECT floatValue, stringValue FROM archive_metadata
WHERE observatory=%s AND fieldId=%s AND time<%s ORDER BY time DESC LIMIT 1
""", (obstory['uid'], results[0]['uid'], time))
        results = self.con.fetchall()
        if len(results) < 1:
            return None
        result = results[0]
        if result['stringValue'] is None:
            value = result['floatValue']
        else:
            value = result['stringValue']
        return value

    # Functions relating to metadata keys
    def get_metadata_key_id(self, metakey):
        self.con.execute("SELECT uid FROM archive_metadataFields WHERE metaKey=%s;", (metakey,))
        results = self.con.fetchall()
        if len(results) < 1:
            self.con.execute("INSERT INTO archive_metadataFields (metaKey) VALUES (%s);", (metakey,))
            self.con.execute("SELECT uid FROM archive_metadataFields WHERE metaKey=%s;", (metakey,))
            results = self.con.fetchall()
        return results[0]['uid']

    # Functions relating to file objects
    def file_path_for_id(self, repository_fname):
        """
        Get the system file path for a given file ID. Does not guarantee that the file exists!

        :param string repository_fname:
            ID of a file (which may or may not exist, this method doesn't check)
        :return:
            System file path for the file
        """
        return os.path.join(self.file_store_path, repository_fname)

    def has_file_id(self, repository_fname):
        """
        Check for the presence of the given file_id

        :param string repository_fname:
            The file ID
        :return:
            True if we have a :class:`meteorpi_model.FileRecord` with this ID, False otherwise
        """
        self.con.execute('SELECT 1 FROM archive_files WHERE repositoryFname = %s', (repository_fname,))
        return len(self.con.fetchall()) > 0

    def delete_file(self, repository_fname):
        file_path = self.file_path_for_id(repository_fname)
        try:
            os.unlink(file_path)
        except OSError:
            print "Could not delete file <%s>" % file_path
            pass
        self.con.execute('DELETE FROM archive_files WHERE repositoryFname = %s', (repository_fname,))

    def get_file(self, repository_fname):
        """
        Retrieve an existing :class:`meteorpi_model.FileRecord` by its ID

        :param string repository_fname:
            The file ID
        :return:
            A :class:`meteorpi_model.FileRecord` instance, or None if not found
        """
        search = mp.FileRecordSearch(repository_fname=repository_fname)
        b = search_files_sql_builder(search)
        sql = b.get_select_sql(columns='f.uid, o.publicId AS observationId, f.mimeType, '
                                       'f.fileName, s2.name AS semanticType, f.fileTime, '
                                       'f.fileSize, f.fileMD5, l.publicId AS obstory_id, l.name AS obstory_name, '
                                       'f.repositoryFname',
                               skip=0, limit=1, order='f.fileTime DESC')
        files = list(self.generators.file_generator(sql=sql, sql_args=b.sql_args))
        if not files:
            return None
        return files[0]

    def search_files(self, search):
        """
        Search for :class:`meteorpi_model.FileRecord` entities

        :param search:
            an instance of :class:`meteorpi_model.FileRecordSearch` used to constrain the observations returned from
            the DB
        :return:
            a structure of {count:int total rows of an unrestricted search, observations:list of
            :class:`meteorpi_model.FileRecord`}
        """
        b = search_files_sql_builder(search)
        sql = b.get_select_sql(columns='f.uid, o.publicId AS observationId, f.mimeType, '
                                       'f.fileName, s2.name AS semanticType, f.fileTime, '
                                       'f.fileSize, f.fileMD5, l.publicId AS obstory_id, l.name AS obstory_name, '
                                       'f.repositoryFname',
                               skip=search.skip,
                               limit=search.limit,
                               order='f.fileTime DESC')
        files = list(self.generators.file_generator(sql=sql, sql_args=b.sql_args))
        rows_returned = len(files)
        total_rows = rows_returned + search.skip
        if (rows_returned == search.limit > 0) or (rows_returned == 0 and search.skip > 0):
            self.con.execute(b.get_count_sql(), b.sql_args)
            total_rows = self.con.fetchone()['COUNT(*)']
        return {"count": total_rows,
                "files": files}

    def register_file(self, observation_id, user_id, file_path, file_time, mime_type, semantic_type,
                      file_md5=None, file_meta=None):
        """
        Register a file in the database, also moving the file into the file store. Returns the corresponding FileRecord
        object.

        :param observation_id:
            The publicId of the observation this file belongs to
        :param string user_id:
            The ID of the user who created this file
        :param string file_path:
            The path of the file on disk to register. This file will be moved into the file store and renamed.
        :param string mime_type:
            MIME type of the file
        :param string semantic_type:
            A string defining the semantic type of the file
        :param float file_time:
            UTC datetime of the import of the file into the database
        :param list file_meta:
            A list of :class:`meteorpi_model.Meta` used to provide additional information about this file
        :return:
            The resultant :class:`meteorpi_model.FileRecord` as stored in the database
        """

        if file_meta is None:
            file_meta = []

        # Check that file exists
        if not os.path.exists(file_path):
            raise ValueError('No file exists at {0}'.format(file_path))

        # Get checksum for file, and size
        file_size_bytes = os.stat(file_path).st_size
        file_name = os.path.split(file_path)[1]

        if file_md5 is None:
            file_md5 = mp.get_md5_hash(file_path)

        # Fetch information about parent observation
        self.con.execute("""
SELECT obsTime, l.publicId AS obstory_id, l.name AS obstory_name FROM archive_observations o
INNER JOIN archive_observatories l ON observatory=l.uid
WHERE o.publicId=%s
""", (observation_id,))
        obs = self.con.fetchall()
        if len(obs) == 0:
            raise ValueError("No observation with ID <%s>" % observation_id)
        obs = obs[0]
        repository_fname = mp.get_hash(obs['obsTime'], obs['obstory_id'], file_name)

        # Get ID code for obs_type
        semantic_type_id = self.get_obs_type_id(semantic_type)

        # Insert into database
        self.con.execute("""
INSERT INTO archive_files
(observationId, mimeType, fileName, semanticType, fileTime, fileSize, repositoryFname, fileMD5)
VALUES
((SELECT uid FROM archive_observations WHERE publicId=%s), %s, %s, %s, %s, %s, %s, %s);
""", (observation_id, mime_type, file_name, semantic_type_id, file_time, file_size_bytes, repository_fname, file_md5))

        # Move the original file from its path
        target_file_path = os.path.join(self.file_store_path, repository_fname)
        try:
            shutil.move(file_path, target_file_path)
        except OSError:
            sys.stderr.write("Could not move file into repository\n")

        # Store the file metadata
        for meta in file_meta:
            self.set_file_metadata(user_id, repository_fname, meta, file_time)

        result_file = mp.FileRecord(obstory_id=obs['obstory_id'],
                                    obstory_name=obs['obstory_name'],
                                    observation_id=observation_id,
                                    repository_fname=repository_fname,
                                    file_time=file_time,
                                    file_size=file_size_bytes,
                                    file_name=file_name,
                                    mime_type=mime_type,
                                    semantic_type=semantic_type,
                                    file_md5=file_md5,
                                    meta=file_meta
                                    )

        # Return the resultant file object
        return result_file

    def import_file(self, file_item, user_id):
        if self.has_file_id(file_item.repository_fname):
            return
        if not self.has_observation_id(file_item.observation_id):
            raise ValueError("No observation with ID <%s>" % file_item.observation_id)

        # Get ID code for obs_type
        semantic_type_id = self.get_obs_type_id(file_item.semantic_type)

        # Insert into database
        self.con.execute("""
INSERT INTO archive_files
(observationId, mimeType, fileName, semanticType, fileTime, fileSize, repositoryFname, fileMD5)
VALUES
((SELECT uid FROM archive_observations WHERE publicId=%s), %s, %s, %s, %s, %s, %s, %s);
""", (
            file_item.observation_id, file_item.mime_type, file_item.file_name, semantic_type_id,
            file_item.file_time, file_item.file_size,
            file_item.repository_fname, file_item.file_md5))

        # Store the file metadata
        for meta in file_item.meta:
            self.set_file_metadata(user_id, file_item.repository_fname, meta, file_item.file_time)

    def set_file_metadata(self, user_id, file_id, meta, utc=None):
        meta_id = self.get_metadata_key_id(meta.key)
        if utc is None:
            utc = mp.now()
        public_id = mp.get_hash(utc, meta.key, user_id)
        self.con.execute("DELETE FROM archive_metadata WHERE "
                         "fieldId=%s AND fileId=(SELECT uid FROM archive_files WHERE repositoryFname=%s);",
                         (meta_id, file_id))
        self.con.execute("""
INSERT INTO archive_metadata (publicId, fieldId, setAtTime, setByUser, stringValue, floatValue, fileId)
VALUES (%s, %s, %s, %s, %s, %s, (SELECT uid FROM archive_files WHERE repositoryFname=%s))
""", (
            public_id,
            meta_id,
            mp.now(),
            user_id,
            meta.string_value(),
            meta.float_value(),
            file_id))

    def unset_file_metadata(self, file_id, key):
        meta_id = self.get_metadata_key_id(key)
        self.con.execute("DELETE FROM archive_metadata WHERE "
                         "fieldId=%s AND fileId=(SELECT uid FROM archive_files WHERE repositoryFname=%s);",
                         (meta_id, file_id))

    def get_file_metadata(self, file_id, key):
        meta_id = self.get_metadata_key_id(key)
        self.con.execute("SELECT stringValue, floatValue FROM archive_metadata "
                         "WHERE fieldId=%s AND fileId=(SELECT uid FROM archive_files WHERE repositoryFname=%s);",
                         (meta_id, file_id))
        results = self.con.fetchall()
        if len(results) < 1:
            return None
        if results[0]['stringValue'] is not None:
            return results[0]['stringValue']
        return results[0]['floatValue']

    # Functions for handling observation objects
    def has_observation_id(self, observation_id):
        """
        Check for the presence of the given observation_id

        :param string observation_id:
            The observation ID
        :return:
            True if we have a :class:`meteorpi_model.Observation` with this Id, False otherwise
        """
        self.con.execute('SELECT 1 FROM archive_observations WHERE publicId = %s', (observation_id,))
        return len(self.con.fetchall()) > 0

    def get_obs_type_id(self, name):
        self.con.execute("SELECT uid FROM archive_semanticTypes WHERE name=%s;", (name,))
        results = self.con.fetchall()
        if len(results) < 1:
            self.con.execute("INSERT INTO archive_semanticTypes (name) VALUES (%s);", (name,))
            self.con.execute("SELECT uid FROM archive_semanticTypes WHERE name=%s;", (name,))
            results = self.con.fetchall()
        return results[0]['uid']

    def delete_observation(self, observation_id):
        self.con.execute('SELECT repositoryFname FROM archive_files f '
                         'INNER JOIN archive_observations o ON f.observationId=o.uid '
                         'WHERE o.publicId=%s;', (observation_id,))
        for file_item in self.con.fetchall():
            self.delete_file(file_item['repositoryFname'])
        self.con.execute('DELETE FROM archive_observations WHERE publicId = %s', (observation_id,))

    def get_observation(self, observation_id):
        """
        Retrieve an existing :class:`meteorpi_model.Observation` by its ID

        :param string observation_id:
            UUID of the observation
        :return:
            A :class:`meteorpi_model.Observation` instance, or None if not found
        """
        search = mp.ObservationSearch(observation_id=observation_id)
        b = search_observations_sql_builder(search)
        sql = b.get_select_sql(columns='l.publicId AS obstory_id, l.name AS obstory_name, '
                                       'o.obsTime, s.name AS obsType, o.publicId, o.uid',
                               skip=0, limit=1, order='o.obsTime DESC')
        obs = list(self.generators.observation_generator(sql=sql, sql_args=b.sql_args))
        if not obs:
            return None
        return obs[0]

    def search_observations(self, search):
        """
        Search for :class:`meteorpi_model.Observation` entities

        :param search:
            an instance of :class:`meteorpi_model.ObservationSearch` used to constrain the observations returned from
            the DB
        :return:
            a structure of {count:int total rows of an unrestricted search, observations:list of
            :class:`meteorpi_model.Observation`}
        """
        b = search_observations_sql_builder(search)
        sql = b.get_select_sql(columns='l.publicId AS obstory_id, l.name AS obstory_name, '
                                       'o.obsTime, s.name AS obsType, o.publicId, o.uid',
                               skip=search.skip,
                               limit=search.limit,
                               order='o.obsTime DESC')
        obs = list(self.generators.observation_generator(sql=sql, sql_args=b.sql_args))
        rows_returned = len(obs)
        total_rows = rows_returned + search.skip
        if (rows_returned == search.limit > 0) or (rows_returned == 0 and search.skip > 0):
            self.con.execute(b.get_count_sql(), b.sql_args)
            total_rows = self.con.fetchone()['COUNT(*)']
        return {"count": total_rows,
                "obs": obs}

    def register_observation(self, obstory_name, user_id, obs_time, obs_type, obs_meta=None):
        """
        Register a new observation, updating the database and returning the corresponding Observation object

        :param string obstory_name:
            The ID of the obstory which produced this observation
        :param string user_id:
            The ID of the user who created this observation
        :param float obs_time:
            The UTC date/time of the observation
        :param string obs_type:
            A string describing the semantic type of this observation
        :param list obs_meta:
            A list of :class:`meteorpi_model.Meta` used to provide additional information about this observation
        :return:
            The :class:`meteorpi_model.Observation` as stored in the database
        """

        if obs_meta is None:
            obs_meta = []

        # Get obstory id from name
        obstory = self.get_obstory_from_name(obstory_name)

        # Create a unique ID for this observation
        observation_id = mp.get_hash(obs_time, obstory['publicId'], obs_type)

        # Get ID code for obs_type
        obs_type_id = self.get_obs_type_id(obs_type)

        # Insert into database
        self.con.execute("""
INSERT INTO archive_observations (publicId, observatory, userId, obsTime, obsType)
VALUES
(%s, %s, %s, %s, %s);
""", (observation_id, obstory['uid'], user_id, obs_time, obs_type_id))

        # Store the observation metadata
        for meta in obs_meta:
            self.set_observation_metadata(user_id, observation_id, meta, obs_time)

        observation = mp.Observation(obstory_name=obstory_name,
                                     obstory_id=obstory['publicId'],
                                     obs_time=obs_time,
                                     obs_id=observation_id,
                                     obs_type=obs_type,
                                     file_records=[],
                                     meta=obs_meta)
        return observation

    def import_observation(self, observation, user_id):
        if self.has_observation_id(observation.obs_id):
            return

        # Get ID code for obs_type
        obs_type_id = self.get_obs_type_id(observation.obs_type)

        # Insert into database
        self.con.execute("""
INSERT INTO archive_observations (publicId, observatory, userId, obsTime, obsType)
VALUES
(%s, (SELECT uid FROM archive_observatories WHERE publicId=%s), %s, %s, %s);
""", (observation.obs_id, observation.obstory_id, user_id, observation.obs_time, obs_type_id))

        # Store the observation metadata
        for meta in observation.meta:
            self.set_observation_metadata(user_id, observation.obs_id, meta)

    def set_observation_metadata(self, user_id, observation_id, meta, utc=None):
        meta_id = self.get_metadata_key_id(meta.key)
        if utc is None:
            utc = mp.now()
        public_id = mp.get_hash(utc, meta.key, user_id)
        self.con.execute("DELETE FROM archive_metadata WHERE "
                         "fieldId=%s AND observationId=(SELECT uid FROM archive_observations WHERE publicId=%s);",
                         (meta_id, observation_id))
        self.con.execute("""
INSERT INTO archive_metadata (publicId, fieldId, setAtTime, setByUser, stringValue, floatValue, observationId)
VALUES (%s, %s, %s, %s, %s, %s, (SELECT uid FROM archive_observations WHERE publicId=%s))
""", (
            public_id,
            meta_id,
            mp.now(),
            user_id,
            meta.string_value(),
            meta.float_value(),
            observation_id))

    def unset_observation_metadata(self, observation_id, key):
        meta_id = self.get_metadata_key_id(key)
        self.con.execute("DELETE FROM archive_metadata WHERE "
                         "fieldId=%s AND observationId=(SELECT uid FROM archive_observations WHERE publicId=%s);",
                         (meta_id, observation_id))

    def get_observation_metadata(self, observation_id, key):
        meta_id = self.get_metadata_key_id(key)
        self.con.execute("SELECT stringValue, floatValue FROM archive_metadata "
                         "WHERE fieldId=%s AND observationId=(SELECT uid FROM archive_observations WHERE publicId=%s);",
                         (meta_id, observation_id))
        results = self.con.fetchall()
        if len(results) < 1:
            return None
        if results[0]['stringValue'] is not None:
            return results[0]['stringValue']
        return results[0]['floatValue']

    def like_observation(self, observation_id, user_id):
        self.con.execute('SELECT uid FROM archive_users WHERE userId = %s;', (user_id,))
        results = self.con.fetchall()
        if len(results) == 0:
            return None
        uid = results[0]['uid']
        self.con.execute('DELETE FROM archive_obs_likes WHERE userId=%s AND observationId=%d;',
                         (uid, observation_id))
        self.con.execute('INSERT INTO archive_obs_likes (userId, observationId) VALUES (%s,%s);',
                         (uid, observation_id))

    def unlike_observation(self, observation_id, user_id):
        self.con.execute('SELECT uid FROM archive_users WHERE userId = %s;', (user_id,))
        results = self.con.fetchall()
        if len(results) == 0:
            return None
        uid = results[0]['uid']
        self.con.execute('DELETE FROM archive_obs_likes WHERE userId=%s AND observationId=%d;',
                         (uid, observation_id))

    # Functions for handling observation groups
    def has_obsgroup_id(self, group_id):
        """
        Check for the presence of the given group_id

        :param string group_id:
            The group ID
        :return:
            True if we have a :class:`meteorpi_model.ObservationGroup` with this Id, False otherwise
        """
        self.con.execute('SELECT 1 FROM archive_obs_groups WHERE publicId = %s', (group_id,))
        return len(self.con.fetchall()) > 0

    def delete_obsgroup(self, group_id):
        self.con.execute('DELETE FROM archive_obs_groups WHERE publicId = %s', (group_id,))

    def get_obsgroup(self, group_id):
        """
        Retrieve an existing :class:`meteorpi_model.ObservationGroup` by its ID

        :param string group_id:
            UUID of the observation
        :return:
            A :class:`meteorpi_model.Observation` instance, or None if not found
        """
        search = mp.ObservationGroupSearch(group_id=group_id)
        b = search_obsgroups_sql_builder(search)
        sql = b.get_select_sql(columns='g.uid, g.time, g.setAtTime, g.setByUser, g.publicId, g.title,'
                                       's.name AS semanticType',
                               skip=0, limit=1, order='g.time DESC')
        obs_groups = list(self.generators.obsgroup_generator(sql=sql, sql_args=b.sql_args))
        if not obs_groups:
            return None
        return obs_groups[0]

    def search_obsgroups(self, search):
        """
        Search for :class:`meteorpi_model.ObservationGroup` entities

        :param search:
            an instance of :class:`meteorpi_model.ObservationGroupSearch` used to constrain the observations returned
            from the DB
        :return:
            a structure of {count:int total rows of an unrestricted search, observations:list of
            :class:`meteorpi_model.ObservationGroup`}
        """
        b = search_obsgroups_sql_builder(search)
        sql = b.get_select_sql(columns='g.uid, g.time, g.setAtTime, g.setByUser, g.publicId, g.title,'
                                       's.name AS semanticType',
                               skip=search.skip,
                               limit=search.limit,
                               order='g.time DESC')
        obs_groups = list(self.generators.obsgroup_generator(sql=sql, sql_args=b.sql_args))
        rows_returned = len(obs_groups)
        total_rows = rows_returned + search.skip
        if (rows_returned == search.limit > 0) or (rows_returned == 0 and search.skip > 0):
            self.con.execute(b.get_count_sql(), b.sql_args)
            total_rows = self.con.fetchone()['COUNT(*)']
        return {"count": total_rows,
                "obsgroups": obs_groups}

    def register_obsgroup(self, title, user_id, semantic_type, obs_time, set_time, obs=None, grp_meta=None):
        """
        Register a new observation, updating the database and returning the corresponding Observation object

        :param string title:
            The title of this observation group
        :param string user_id:
            The ID of the user who created this observation
        :param float obs_time:
            The UTC date/time of the observation
        :param float set_time:
            The UTC date/time that this group was created
        :param list obs:
            A list of :class: publicIds of observations which are members of this group
        :param list grp_meta:
            A list of :class:`meteorpi_model.Meta` used to provide additional information about this observation
        :return:
            The :class:`meteorpi_model.ObservationGroup` as stored in the database
        """

        if grp_meta is None:
            grp_meta = []

        # Create a unique ID for this observation
        group_id = mp.get_hash(set_time, title, user_id)

        # Get ID code for semantic_type
        semantic_type_id = self.get_obs_type_id(semantic_type)

        # Insert into database
        self.con.execute("""
INSERT INTO archive_obs_groups (publicId, title, time, setByUser, setAtTime, semanticType)
VALUES
(%s, %s, %s, %s, %s, %s);
""", (group_id, title, obs_time, user_id, set_time, semantic_type_id))

        # Store list of observations into the database
        for item in obs:
            self.con.execute("""
INSERT INTO archive_obs_group_members (groupId, observationId)
VALUES
((SELECT uid FROM archive_obs_groups WHERE publicId=%s), (SELECT uid FROM archive_observations WHERE publicId=%s));
""", (group_id, item))
        # Store the observation metadata
        for meta in grp_meta:
            self.set_obsgroup_metadata(user_id, group_id, meta, obs_time)

        obs_group = mp.ObservationGroup(group_id=group_id,
                                        title=title,
                                        obs_time=obs_time,
                                        user_id=user_id,
                                        set_time=set_time,
                                        semantic_type=semantic_type,
                                        obs_records=[],
                                        meta=grp_meta)
        return obs_group

    def add_obsgroup_member(self, group_id, observation_id):
        self.delete_obsgroup_member(group_id, observation_id)
        self.con.execute("INSERT INTO archive_obs_group_members (groupId, observationId)  VALUES "
                         "( (SELECT uid FROM archive_obs_groups WHERE publicId=%s),"
                         "  (SELECT uid FROM archive_observations WHERE publicId=%s) );",
                         (group_id, observation_id))

    def delete_obsgroup_member(self, group_id, observation_id):
        self.con.execute("DELETE FROM archive_obs_group_members WHERE "
                         "groupId=(SELECT uid FROM archive_obs_groups WHERE publicId=%s) AND"
                         "observationId=(SELECT uid FROM archive_observations WHERE publicId=%s);",
                         (group_id, observation_id))

    def set_obsgroup_metadata(self, user_id, group_id, meta, utc=None):
        meta_id = self.get_metadata_key_id(meta.key)
        if utc is None:
            utc = mp.now()
        public_id = mp.get_hash(utc, meta.key, user_id)
        self.con.execute("DELETE FROM archive_metadata WHERE "
                         "fieldId=%s AND groupId=(SELECT uid FROM archive_obs_groups WHERE publicId=%s);",
                         (meta_id, group_id))
        self.con.execute("""
INSERT INTO archive_metadata (publicId, fieldId, setAtTime, setByUser, stringValue, floatValue, groupId)
VALUES (%s, %s, %s, %s, %s, %s, (SELECT uid FROM archive_obs_groups WHERE publicId=%s))
""", (
            public_id,
            meta_id,
            mp.now(),
            user_id,
            meta.string_value(),
            meta.float_value(),
            group_id))

    def unset_obsgroup_metadata(self, group_id, key):
        meta_id = self.get_metadata_key_id(key)
        self.con.execute("DELETE FROM archive_metadata WHERE "
                         "fieldId=%s AND groupId=(SELECT uid FROM archive_obs_groups WHERE publicId=%s);",
                         (meta_id, group_id))

    def get_obsgroup_metadata(self, group_id, key):
        meta_id = self.get_metadata_key_id(key)
        self.con.execute("SELECT stringValue, floatValue FROM archive_metadata "
                         "WHERE fieldId=%s AND groupId=(SELECT uid FROM archive_obs_groups WHERE publicId=%s);",
                         (meta_id, group_id))
        results = self.con.fetchall()
        if len(results) < 1:
            return None
        if results[0]['stringValue'] is not None:
            return results[0]['stringValue']
        return results[0]['floatValue']

    # Functions for handling user accounts
    def get_user(self, user_id, password):
        """
        Retrieve a user record

        :param user_id:
            the user ID
        :param password:
            password
        :return:
            A :class:`meteorpi_model.User` if everything is correct
        :raises:
            ValueError if the user is found but password is incorrect or if the user is not found.
        """
        self.con.execute('SELECT uid, pwHash FROM archive_users WHERE userId = %s;', (user_id,))
        results = self.con.fetchall()
        if len(results) == 0:
            raise ValueError("No such user")
        pw_hash = results[0]['pwHash']
        # Check the password
        if not pbkdf2_sha256.verify(password, pw_hash):
            raise ValueError("Incorrect password")

        # Fetch list of roles
        self.con.execute('SELECT name FROM archive_roles r INNER JOIN archive_user_roles u ON u.roleId=r.uid '
                         'WHERE u.userId = %s;', (results[0]['uid'],))
        role_list = [row['name'] for row in self.con.fetchall()]
        return mp.User(user_id=user_id, roles=role_list)

    def get_users(self):
        """
        Retrieve all users in the system

        :return:
            A list of :class:`meteorpi_model.User`
        """
        output = []
        self.con.execute('SELECT userId, uid FROM archive_users;')
        results = self.con.fetchall()

        for result in results:
            # Fetch list of roles
            self.con.execute('SELECT name FROM archive_roles r INNER JOIN archive_user_roles u ON u.roleId=r.uid '
                             'WHERE u.userId = %s;', (result['uid'],))
            role_list = [row['name'] for row in self.con.fetchall()]
            output.append(mp.User(user_id=result['userId'], roles=role_list))
        return output

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
        action = "update"
        self.con.execute('SELECT 1 FROM archive_users WHERE userId = %s;', (user_id,))
        results = self.con.fetchall()
        if len(results) == 0:
            if password is None:
                raise ValueError("Must specify an initial password when creating a new user!")
            action = "create"
            self.con.execute('INSERT INTO archive_users (userId, pwHash) VALUES (%s,%s)',
                             (user_id, pbkdf2_sha256.encrypt(password)))

        if password is None and roles is None:
            action = "none"
        if password is not None:
            self.con.execute('UPDATE archive_users SET pwHash = %s WHERE userId = %s',
                             (pbkdf2_sha256.encrypt(password), user_id))
        if roles is not None:

            # Clear out existing roles, and delete any unused roles
            self.con.execute("DELETE r FROM archive_user_roles AS r WHERE "
                             "(SELECT u.userId FROM  archive_users AS u WHERE r.userId=u.uid)=%s;", (user_id,))
            self.con.execute("DELETE r FROM archive_roles AS r WHERE r.uid NOT IN "
                             "(SELECT roleId FROM archive_user_roles);")

            for role in roles:
                self.con.execute("SELECT uid FROM archive_roles WHERE name=%s;", (role,))
                results = self.con.fetchall()
                if len(results) < 1:
                    self.con.execute("INSERT INTO archive_roles (name) VALUES (%s);", (role,))
                    self.con.execute("SELECT uid FROM archive_roles WHERE name=%s;", (role,))
                    results = self.con.fetchall()

                    self.con.execute('INSERT INTO archive_user_roles (userId, roleId) VALUES '
                                     '((SELECT u.uid FROM archive_users u WHERE u.userId=%s),'
                                     '%s)', (user_id, results[0]['uid']))
            return action

    def delete_user(self, user_id):
        """
        Completely remove the specified user ID from the system

        :param string user_id:
            The user_id to remove
        """
        self.con.execute('DELETE FROM archive_users WHERE userId = %s', (user_id,))

    # Functions for handling export configurations
    def get_export_configuration(self, config_id):
        """
        Retrieve the ExportConfiguration with the given ID

        :param string config_id:
            ID for which to search
        :return:
            a :class:`meteorpi_model.ExportConfiguration` or None, or no match was found.
        """
        sql = (
            'SELECT uid, exportConfigId, exportType, searchString, targetURL, '
            'targetUser, targetPassword, exportName, description, active '
            'FROM archive_exportConfig WHERE exportConfigId = %s')
        return first_from_generator(
                self.generators.export_configuration_generator(sql=sql, sql_args=(config_id,)))

    def get_export_configurations(self):
        """
        Retrieve all ExportConfigurations held in this db

        :return: a list of all :class:`meteorpi_model.ExportConfiguration` on this server
        """
        sql = (
            'SELECT uid, exportConfigId, exportType, searchString, targetURL, '
            'targetUser, targetPassword, exportName, description, active '
            'FROM archive_exportConfig ORDER BY uid DESC')
        return list(self.generators.export_configuration_generator(sql=sql, sql_args=[]))

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
            its 'config_id' string field defined.
        """
        search_string = json.dumps(obj=export_config.search.as_dict())
        user_id = export_config.user_id
        password = export_config.password
        target_url = export_config.target_url
        enabled = export_config.enabled
        name = export_config.name
        description = export_config.description
        export_type = export_config.type
        if export_config.config_id is not None:
            # Update existing record
            self.con.execute(
                    'UPDATE archive_exportConfig c '
                    'SET c.searchString = %s, c.targetUrl = %s, c.targetUser = %s, c.targetPassword = %s, '
                    'c.exportName = %s, c.description = %s, c.active = %s, c.exportType = %s '
                    'WHERE c.exportConfigId = %s',
                    (search_string, target_url, user_id, password, name, description, enabled, export_type,
                     export_config.config_id))
        else:
            # Create new record and add the ID into the supplied config
            item_id = mp.get_hash(mp.now(), name, export_type)
            self.con.execute(
                    'INSERT INTO archive_exportConfig '
                    '(searchString, targetUrl, targetUser, targetPassword, '
                    'exportName, description, active, exportType, exportConfigId) '
                    'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ',
                    (search_string, target_url, user_id, password,
                     name, description, enabled, export_type, item_id))
            export_config.config_id = item_id
        return export_config

    def delete_export_configuration(self, config_id):
        """
        Delete a file export configuration by external UUID

        :param string config_id: the ID of the config to delete
        """
        self.con.execute('DELETE FROM archive_exportConfig WHERE exportConfigId = %s;', (config_id,))

    def mark_entities_to_export(self, export_config):
        """
        Apply the specified :class:`meteorpi_model.ExportConfiguration` to the database, running its contained query and
        creating rows in t_observationExport or t_fileExport for matching entities.

        :param ExportConfiguration export_config:
            An instance of :class:`meteorpi_model.ExportConfiguration` to apply.
        :returns:
            The integer number of rows added to the export tables
        """
        # Retrieve the internal ID of the export configuration, failing if it hasn't been stored
        self.con.execute('SELECT uid FROM archive_exportConfig WHERE exportConfigID = %s;',
                         (export_config.config_id,))
        export_config_id = self.con.fetchall()
        if len(export_config_id) < 1:
            raise ValueError("Attempt to run export on ExportConfiguration not in database")
        export_config_id = export_config_id[0]['uid']

        # If the export is inactive then do nothing
        if not export_config.enabled:
            return 0

        # Track the number of rows created, return it later
        rows_created = 0

        # Handle ObservationSearch
        if isinstance(export_config.search, mp.ObservationSearch):
            # Create a deep copy of the search and set the properties required when creating exports
            search = mp.ObservationSearch.from_dict(export_config.search.as_dict())
            search.exclude_export_to = export_config.config_id
            b = search_observations_sql_builder(search)

            self.con.execute(b.get_select_sql(columns='o.uid'), b.sql_args)
            for result in self.con.fetchall():
                self.con.execute('INSERT INTO archive_observationExport (observationId, exportConfig, exportState) '
                                 'VALUES (%s,%s,%s)', (result['uid'], export_config_id, 1))
                rows_created += 1

        # Handle FileSearch
        elif isinstance(export_config.search, mp.FileRecordSearch):
            # Create a deep copy of the search and set the properties required when creating exports
            search = mp.FileRecordSearch.from_dict(export_config.search.as_dict())
            search.exclude_export_to = export_config.config_id
            b = search_files_sql_builder(search)

            self.con.execute(b.get_select_sql(columns='f.uid'), b.sql_args)
            for result in self.con.fetchall():
                self.con.execute('INSERT INTO archive_fileExport (fileId, exportConfig, exportState) '
                                 'VALUES (%s,%s,%s)', (result['uid'], export_config_id, 1))
                rows_created += 1

        # Handle ObservatoryMetadataSearch
        elif isinstance(export_config.search, mp.ObservatoryMetadataSearch):
            # Create a deep copy of the search and set the properties required when creating exports
            search = mp.ObservatoryMetadataSearch.from_dict(export_config.search.as_dict())
            search.exclude_export_to = export_config.config_id
            b = search_metadata_sql_builder(search)

            self.con.execute(b.get_select_sql(columns='m.uid'), b.sql_args)
            for result in self.con.fetchall():
                self.con.execute('INSERT INTO archive_metadataExport (metadataId, exportConfig, exportState) '
                                 'VALUES (%s,%s,%s)', (result['uid'], export_config_id, 1))
                rows_created += 1

        # Complain if it's anything other than these two (nothing should be at the moment but we might introduce
        # more search types in the future
        else:
            raise ValueError("Unknown search type %s" % str(type(export_config.search)))
        return rows_created

    def get_next_entity_to_export(self):
        """
        Examines the archive_observationExport and archive_metadataExport tables, and builds
        either a :class:`meteorpi_db.ObservationExportTask` or a :class:`meteorpi_db.MetadataExportTask` as appropriate.
        These task objects can be used to retrieve the underlying entity and export configuration, and to update the
        completion state or push the timestamp into the future, deferring evaluation of the task until later.

        :returns:
            Either None, if no exports are available, or an object, depending on whether an observation or metadata
            item is next in the queue to export.
        """

        # Similar operation for archive_metadataExport
        self.con.execute('SELECT c.exportConfigId, o.publicId, x.exportState, '
                         'c.targetURL, c.targetUser, c.targetPassword '
                         'FROM archive_metadataExport x '
                         'INNER JOIN archive_exportConfig c ON x.exportConfig=c.uid '
                         'INNER JOIN archive_metadata o ON x.metadataId=o.uid '
                         'AND c.active = 1 '
                         'AND x.exportState > 0 '
                         'ORDER BY o.setAtTime ASC, o.uid ASC LIMIT 1')
        row = self.con.fetchone()
        if row is not None:
            config_id = row['exportConfigId']
            entity_id = row['publicId']
            status = row['exportState']
            target_url = row['targetURL']
            target_user = row['targetUser']
            target_password = row['targetPassword']
            return MetadataExportTask(db=self, config_id=config_id, metadata_id=entity_id,
                                      status=status, target_url=target_url, target_user=target_user,
                                      target_password=target_password)

        # Try to retrieve the earliest record in archive_observationExport
        self.con.execute('SELECT c.exportConfigId, o.publicId, x.exportState, '
                         'c.targetURL, c.targetUser, c.targetPassword '
                         'FROM archive_observationExport x '
                         'INNER JOIN archive_exportConfig c ON x.exportConfig=c.uid '
                         'INNER JOIN archive_observations o ON x.observationId=o.uid '
                         'WHERE c.active = 1 '
                         'AND x.exportState > 0 '
                         'ORDER BY o.obsTime ASC, o.uid ASC LIMIT 1')
        row = self.con.fetchone()
        if row is not None:
            config_id = row['exportConfigId']
            entity_id = row['publicId']
            status = row['exportState']
            target_url = row['targetURL']
            target_user = row['targetUser']
            target_password = row['targetPassword']
            return ObservationExportTask(db=self, config_id=config_id, observation_id=entity_id,
                                         status=status, target_url=target_url, target_user=target_user,
                                         target_password=target_password)

        # Try to retrieve the earliest record in archive_fileExport
        self.con.execute('SELECT c.exportConfigId, o.repositoryFname, x.exportState, '
                         'c.targetURL, c.targetUser, c.targetPassword '
                         'FROM archive_fileExport x '
                         'INNER JOIN archive_exportConfig c ON x.exportConfig=c.uid '
                         'INNER JOIN archive_files o ON x.fileId=o.uid '
                         'WHERE c.active = 1 '
                         'AND x.exportState > 0 '
                         'ORDER BY o.fileTime ASC, o.uid ASC LIMIT 1')
        row = self.con.fetchone()
        if row is not None:
            config_id = row['exportConfigId']
            entity_id = row['repositoryFname']
            status = row['exportState']
            target_url = row['targetURL']
            target_user = row['targetUser']
            target_password = row['targetPassword']
            return FileExportTask(db=self, config_id=config_id, file_id=entity_id,
                                  status=status, target_url=target_url, target_user=target_user,
                                  target_password=target_password)

        return None

    # Functions relating to high water marks
    def get_hwm_key_id(self, metakey):
        self.con.execute("SELECT uid FROM archive_highWaterMarkTypes WHERE metaKey=%s;", (metakey,))
        results = self.con.fetchall()
        if len(results) < 1:
            self.con.execute("INSERT INTO archive_highWaterMarkTypes (metaKey) VALUES (%s);", (metakey,))
            self.con.execute("SELECT uid FROM archive_highWaterMarkTypes WHERE metaKey=%s;", (metakey,))
            results = self.con.fetchall()
        return results[0]['uid']

    def get_high_water_mark(self, mark_type, obstory_name=None):
        """
        Retrieves the high water mark for a given obstory, defaulting to the current installation ID

        :param string mark_type:
            The type of high water mark to set
        :param string obstory_name:
            The obstory ID to check for, or the default installation ID if not specified
        :return:
            A UTC datetime for the high water mark, or None if none was found.
        """
        if obstory_name is None:
            obstory_name = self.obstory_name

        obstory = self.get_obstory_from_name(obstory_name)
        key_id = self.get_hwm_key_id(mark_type)

        self.con.execute('SELECT time FROM archive_highWaterMarks WHERE markType=%s AND observatoryId=%s',
                         (key_id, obstory['uid']))
        results = self.con.fetchall()
        if len(results) > 0:
            return results[0]['time']
        return None

    def set_high_water_mark(self, mark_type, time, obstory_name=None):
        if obstory_name is None:
            obstory_name = self.obstory_name

        obstory = self.get_obstory_from_name(obstory_name)
        key_id = self.get_hwm_key_id(mark_type)

        self.con.execute('DELETE FROM archive_highWaterMarks WHERE markType=%s AND observatoryId=%s',
                         (key_id, obstory['uid']))
        self.con.execute('INSERT INTO archive_highWaterMarks (markType, observatoryId, time) VALUES (%s,%s,%s);',
                         (key_id, obstory['uid'], time))

    def clear_database(self, tmin=None, tmax=None, obstory_names=None):

        if obstory_names is None:
            obstory_names = self.get_obstory_names()
        if isinstance(obstory_names, basestring):
            obstory_names = [obstory_names]

        for obstory_name in obstory_names:
            obstory = self.get_obstory_from_name(obstory_name)
            # Purge tables - other tables are deleted by foreign key cascades from these ones.
            self.con.execute('SELECT publicId FROM archive_observations '
                             'WHERE obsTime>%s AND obsTime<%s AND observatory=%s',
                             (tmin, tmax, obstory['uid']))
            for obs in self.con.fetchall():
                self.delete_observation(obs['publicId'])
            self.con.execute('DELETE FROM archive_metadata WHERE time>%s AND time<%s AND observatory=%s',
                             (tmin, tmax, obstory['uid']))
