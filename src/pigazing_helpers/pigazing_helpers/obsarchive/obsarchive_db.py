# -*- coding: utf-8 -*-
# obsarchive_db.py

# Classes which interact with the observation database

import json
import numbers
import os
import shutil
import sys
import time

import MySQLdb
import passlib.hash

from . import obsarchive_model as mp
from .generators import first_from_generator, ObservationDatabaseGenerators
from .obsarchive_sky_area import get_sky_area
from .sql_builder import search_observations_sql_builder, search_files_sql_builder, \
    search_metadata_sql_builder, search_obsgroups_sql_builder

SOFTWARE_VERSION = 2


class ObservationDatabase(object):
    """
    Class representing a single observation database and file store.

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

    def __init__(self, file_store_path, db_host='localhost', db_user='obsarchive', db_password='obsarchive',
                 db_name='obsarchive', obstory_id='Undefined'):
        """
        Create a new db instance. This connects to the specified database and retains a connection which is
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
        :param string obstory_id:
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
        self.obstory_id = obstory_id
        self.generators = ObservationDatabaseGenerators(db=self, con=self.con)

    def __str__(self):
        """Simple string representation of this db object

        :return:
            info about the db path and file store location
        """
        return ('ObservationDatabase(file_store_path={0}, db_path={1}, db_host={2}, db_user={3}, db_password={4}, '
                'db_name={5}, obstory_id={6})'.format(
            self.file_store_path,
            self.db_host,
            self.db_user,
            self.db_password,
            self.db_name,
            self.obstory_id))

    def commit(self):
        self.db.commit()

    def close_db(self):
        self.con.close()
        self.db.close()

    # Functions relating to observatories
    def has_obstory_id(self, obstory_id):
        self.con.execute('SELECT 1 FROM archive_observatories WHERE publicId=%s;', (obstory_id,))
        return len(self.con.fetchall()) > 0

    def get_obstory_from_id(self, obstory_id):
        self.con.execute("""
SELECT uid, publicId, userId, name, ST_X(location) AS longitude, ST_Y(location) AS latitude
FROM archive_observatories WHERE publicId=%s;""", (obstory_id,))
        results = self.con.fetchall()
        if len(results) < 1:
            raise ValueError("No such obstory: %s" % obstory_id)
        return results[0]

    def register_obstory(self, obstory_id, obstory_name, owner, latitude, longitude):
        self.con.execute("""
INSERT INTO archive_observatories
(publicId, name, location, userId)
VALUES
(%s, %s, POINT(%s, %s), %s);
""", (obstory_id, obstory_name, longitude, latitude, owner))
        return obstory_id

    def delete_obstory(self, obstory_id):
        self.con.execute("DELETE FROM archive_observatories WHERE publicId=%s;", (obstory_id,))

    def get_obstory_ids(self):
        """
        Retrieve the IDs of all obstorys.

        :return:
            A list of obstory IDs for all obstorys
        """
        self.con.execute('SELECT publicId FROM archive_observatories;')
        return [row['publicId'] for row in self.con.fetchall()]

    def get_obstory_names(self):
        self.con.execute('SELECT name FROM archive_observatories;')
        return [row['name'] for row in self.con.fetchall()]

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

    def register_obstory_metadata(self, obstory_id, key, value, metadata_time, user_created, time_created=None):
        if time_created is None:
            time_created = mp.now()
        obstory = self.get_obstory_from_id(obstory_id)
        item_id = mp.get_hash(metadata_time, obstory['publicId'], key)

        # If new value equals old value, no point re-entering it!
        previous_value = self.lookup_obstory_metadata(key, metadata_time, obstory_id)
        if previous_value == value:
            return None

        self.import_obstory_metadata(obstory['uid'], key, value, metadata_time, time_created, user_created, item_id)

        return mp.ObservatoryMetadata(metadata_id=item_id, obstory_id=obstory['uid'], obstory_name=obstory['name'],
                                      obstory_lat=obstory['latitude'], obstory_lng=obstory['longitude'],
                                      key=key, value=value, metadata_time=metadata_time,
                                      time_created=time_created, user_created=user_created)

    def import_obstory_metadata(self, obstory_id, key, value, metadata_time, time_created, user_created, item_id):
        if self.has_obstory_metadata(item_id):
            return

        obstory = self.get_obstory_from_id(obstory_id)
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

    def get_obstory_status(self, time=None, obstory_id=None):
        if time is None:
            time = mp.now()
        if obstory_id is None:
            obstory_id = self.obstory_id
        obstory = self.get_obstory_from_id(obstory_id)

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

    def lookup_obstory_metadata(self, key, time=None, obstory_id=None):
        if time is None:
            time = mp.now()
        if obstory_id is None:
            obstory_id = self.obstory_id
        obstory = self.get_obstory_from_id(obstory_id)

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
            True if we have a :class:`obsarchive_model.FileRecord` with this ID, False otherwise
        """
        self.con.execute('SELECT 1 FROM archive_files WHERE repositoryFname = %s', (repository_fname,))
        return len(self.con.fetchall()) > 0

    def delete_file(self, repository_fname):
        file_path = self.file_path_for_id(repository_fname)
        try:
            os.unlink(file_path)
        except OSError:
            print("Could not delete file <%s>" % file_path)
            pass
        self.con.execute('DELETE FROM archive_files WHERE repositoryFname = %s', (repository_fname,))

    def get_file(self, repository_fname):
        """
        Retrieve an existing :class:`obsarchive_model.FileRecord` by its ID

        :param string repository_fname:
            The file ID
        :return:
            A :class:`obsarchive_model.FileRecord` instance, or None if not found
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
        Search for :class:`obsarchive_model.FileRecord` entities

        :param search:
            an instance of :class:`obsarchive_model.FileRecordSearch` used to constrain the observations returned from
            the DB
        :return:
            a structure of {count:int total rows of an unrestricted search, observations:list of
            :class:`obsarchive_model.FileRecord`}
        """
        b = search_files_sql_builder(search)
        sql = b.get_select_sql(columns='f.uid, o.publicId AS observationId, f.mimeType, '
                                       'f.fileName, s2.name AS semanticType, f.fileTime, f.primaryImage, '
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
                      primary_image=False, file_md5=None, file_meta=None, random_id=False):
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
        :param boolean primary_image:
            Flag indicating whether this is the primary image to display within this observation.
        :param string file_md5:
            An MD5 hash of this file.
        :param list file_meta:
            A list of :class:`obsarchive_model.Meta` used to provide additional information about this file
        :param random_id:
            Boolean flag. If true, we pick a random publicId for this observation. If false, we pick a predictable
            one based on the image's metadata. The latter may be useful if we want repeatable behaviour.
        :return:
            The resultant :class:`obsarchive_model.FileRecord` as stored in the database
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

        # Pick a public Id for this file
        if random_id:
            repository_fname = mp.get_hash(obs['obsTime'], obs['obstory_id'], file_name, time.time())
        else:
            repository_fname = mp.get_hash(obs['obsTime'], obs['obstory_id'], file_name, obs['obsTime'])

        # Get ID code for obs_type
        semantic_type_id = self.get_obs_type_id(semantic_type)

        # Insert into database
        self.con.execute("""
INSERT INTO archive_files
(observationId, mimeType, fileName, semanticType, fileTime, fileSize, repositoryFname, fileMD5, primaryImage)
VALUES
((SELECT uid FROM archive_observations WHERE publicId=%s), %s, %s, %s, %s, %s, %s, %s, %s);
""", (observation_id, mime_type, file_name, semantic_type_id, file_time, file_size_bytes,
      repository_fname, file_md5, primary_image))

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
                                    primary_image=primary_image,
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
(observationId, mimeType, fileName, semanticType, fileTime, fileSize, repositoryFname, fileMD5, primaryImage)
VALUES
((SELECT uid FROM archive_observations WHERE publicId=%s), %s, %s, %s, %s, %s, %s, %s, %s);
""", (
            file_item.observation_id, file_item.mime_type, file_item.file_name, semantic_type_id,
            file_item.file_time, file_item.file_size,
            file_item.repository_fname, file_item.file_md5, file_item.primary_image))

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
            True if we have a :class:`obsarchive_model.Observation` with this Id, False otherwise
        """
        self.con.execute('SELECT 1 FROM archive_observations WHERE publicId=%s', (observation_id,))
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
        self.con.execute('DELETE FROM archive_observations WHERE publicId=%s', (observation_id,))

    def get_observation(self, observation_id):
        """
        Retrieve an existing :class:`obsarchive_model.Observation` by its ID

        :param string observation_id:
            UUID of the observation
        :return:
            A :class:`obsarchive_model.Observation` instance, or None if not found
        """
        search = mp.ObservationSearch(observation_id=observation_id)
        b = search_observations_sql_builder(search)
        sql = b.get_select_sql(columns='l.publicId AS obstory_id, l.name AS obstory_name, l.userId AS obstory_owner, '
                                       'o.obsTime, s.name AS obsType, o.publicId, o.uid, o.creationTime, '
                                       'o.published, o.moderated, o.featured, ST_X(o.position) AS ra, '
                                       'ST_Y(o.position) AS dec, o.fieldWidth, o.fieldHeight, o.positionAngle, '
                                       'o.centralConstellation, o.astrometryProcessed',
                               skip=0, limit=1, order='o.obsTime DESC')
        obs = list(self.generators.observation_generator(sql=sql, sql_args=b.sql_args))
        if not obs:
            return None
        return obs[0]

    def search_observations(self, search):
        """
        Search for :class:`obsarchive_model.Observation` entities

        :param search:
            an instance of :class:`obsarchive_model.ObservationSearch` used to constrain the observations returned from
            the DB
        :return:
            a structure of {count:int total rows of an unrestricted search, observations:list of
            :class:`obsarchive_model.Observation`}
        """
        b = search_observations_sql_builder(search)
        sql = b.get_select_sql(columns='l.publicId AS obstory_id, l.name AS obstory_name, l.userId AS obstory_owner, '
                                       'o.obsTime, s.name AS obsType, o.publicId, o.uid, o.creationTime, '
                                       'o.published, o.moderated, o.featured, ST_X(o.position) AS ra, '
                                       'ST_Y(o.position) AS dec, o.fieldWidth, o.fieldHeight, o.positionAngle, '
                                       'o.centralConstellation, o.astrometryProcessed',
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

    def register_observation(self, obstory_id, user_id, obs_time, obs_type, creation_time, published, moderated,
                             featured, ra, dec, field_width, field_height, position_angle, central_constellation,
                             astrometry_processed, obs_meta=None, random_id=False):
        """
        Register a new observation, updating the database and returning the corresponding Observation object

        :param string obstory_id:
            The ID of the obstory which produced this observation
        :param string user_id:
            The ID of the user who created this observation
        :param float obs_time:
            The UTC date/time of the observation
        :param string obs_type:
            A string describing the semantic type of this observation
        :param float creation_time:
            Time when this observation was created.
        :param integer published:
            flag indicating whether this observations has been published
        :param integer moderated:
            flag indicating whether this observation has been accepted by the moderators
        :param featured:
            flag indicating whether this is a "featured" observation
        :param ra:
            Right ascension of the centre of the field, in hours.
        :param dec:
            Declination of the centre of the field, in degrees.
        :param field_width:
            Width of the field of view, in degrees.
        :param field_height:
            Height of the field of view, in degrees.
        :param position_angle:
            Position angle at the centre of the image, in degrees.
        :param central_constellation:
            Constellation where the centre of the image falls.
        :param astrometry_processed:
            Unix time when the astrometric coordinates of this image were (last) processed.
        :param list obs_meta:
            A list of :class:`obsarchive_model.Meta` used to provide additional information about this observation
        :param random_id:
            Boolean flag. If true, we pick a random publicId for this observation. If false, we pick a predictable
            one based on the image's metadata. The latter may be useful if we want repeatable behaviour.
        :return:
            The :class:`obsarchive_model.Observation` as stored in the database
        """

        if obs_meta is None:
            obs_meta = []

        # Get obstory id from name
        obstory = self.get_obstory_from_id(obstory_id)

        # Create a unique ID for this observation
        if random_id:
            observation_id = mp.get_hash(obs_time, obstory['publicId'], obs_type, time.time())
        else:
            observation_id = mp.get_hash(obs_time, obstory['publicId'], obs_type)

        # Get ID code for obs_type
        obs_type_id = self.get_obs_type_id(obs_type)

        # Get a polygon representing the sky area of this image
        sky_area = get_sky_area(ra=ra, dec=dec, pa=position_angle, scale_x=field_width, scale_y=field_height)

        # Insert into database
        self.con.execute("""
INSERT INTO archive_observations (publicId, observatory, userId, obsTime, obsType, creationTime, published, moderated,
                                  featured, position, fieldWidth, fieldHeight, positionAngle, centralConstellation,
                                  astrometryProcessed, skyArea)
VALUES
(%s, %s, %s, %s, %s, %s, %s, %s,
 %s, POINT(%s, %s), %s, %s, %s, %s, %s, ST_GEOMFROMTEXT(%s));
""",
                         (observation_id, obstory['uid'], user_id, obs_time, obs_type_id,
                          creation_time, published, moderated,
                          featured, ra, dec, field_width, field_height, position_angle, central_constellation,
                          astrometry_processed, sky_area))

        # Store the observation metadata
        for meta in obs_meta:
            self.set_observation_metadata(user_id, observation_id, meta, obs_time)

        observation = mp.Observation(obstory_name=obstory['name'],
                                     obstory_id=obstory['publicId'],
                                     obstory_owner=obstory['userId'],
                                     obs_time=obs_time,
                                     obs_id=observation_id,
                                     obs_type=obs_type,
                                     creation_time=creation_time,
                                     published=published,
                                     moderated=moderated,
                                     featured=featured,
                                     ra=ra,
                                     dec=dec,
                                     field_width=field_width,
                                     field_height=field_height,
                                     position_angle=position_angle,
                                     central_constellation=central_constellation,
                                     astrometry_processed=astrometry_processed,
                                     file_records=[],
                                     meta=obs_meta)
        return observation

    def import_observation(self, observation, user_id):
        if self.has_observation_id(observation.obs_id):
            return

        # Get ID code for obs_type
        obs_type_id = self.get_obs_type_id(observation.obs_type)

        # Get a polygon representing the sky area of this image
        sky_area = get_sky_area(ra=ra, dec=dec, pa=position_angle,
                                scale_x=observation.field_width,
                                scale_y=observation.field_height)

        # Insert into database
        self.con.execute("""
INSERT INTO archive_observations (publicId, observatory, userId, obsTime, obsType, creationTime, published, moderated,
                                  featured, position, fieldWidth, fieldHeight, positionAngle, centralConstellation,
                                  astrometryProcessed, skyArea)
VALUES
(%s, (SELECT uid FROM archive_observatories WHERE publicId=%s), %s, %s, %s, %s, %s, %s,
 %s, POINT(%s, %s), %s, %s, %s, %s, %s, ST_GEOMFROMTEXT(%s));
""",
                         (observation.obs_id, observation.obstory_id, user_id, observation.obs_time, obs_type_id,
                          observation.creation_time, observation.published, observation.moderated,
                          observation.featured, observation.ra, observation.dec,
                          observation.field_width, observation.field_height,
                          observation.position_angle, observation.central_constellation,
                          observation.astrometry_processed, sky_area))

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
        self.con.execute('SELECT uid FROM inthesky_users WHERE userId = %s;', (user_id,))
        results = self.con.fetchall()
        if len(results) == 0:
            return None
        uid = results[0]['uid']
        self.con.execute('DELETE FROM archive_obs_likes WHERE userId=%s AND observationId=%d;',
                         (uid, observation_id))
        self.con.execute('INSERT INTO archive_obs_likes (userId, observationId) VALUES (%s,%s);',
                         (uid, observation_id))

    def unlike_observation(self, observation_id, user_id):
        self.con.execute('SELECT uid FROM inthesky_users WHERE userId = %s;', (user_id,))
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
            True if we have a :class:`obsarchive_model.ObservationGroup` with this Id, False otherwise
        """
        self.con.execute('SELECT 1 FROM archive_obs_groups WHERE publicId = %s', (group_id,))
        return len(self.con.fetchall()) > 0

    def delete_obsgroup(self, group_id):
        self.con.execute('DELETE FROM archive_obs_groups WHERE publicId = %s', (group_id,))

    def get_obsgroup(self, group_id):
        """
        Retrieve an existing :class:`obsarchive_model.ObservationGroup` by its ID

        :param string group_id:
            UUID of the observation
        :return:
            A :class:`obsarchive_model.Observation` instance, or None if not found
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
        Search for :class:`obsarchive_model.ObservationGroup` entities

        :param search:
            an instance of :class:`obsarchive_model.ObservationGroupSearch` used to constrain the observations returned
            from the DB
        :return:
            a structure of {count:int total rows of an unrestricted search, observations:list of
            :class:`obsarchive_model.ObservationGroup`}
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

    def register_obsgroup(self, title, user_id, semantic_type, obs_time, set_time, obs=None, subgroups=None,
                          grp_meta=None):
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
        :param list subgroups:
            A list of :class: publicIds of observation groups which are sub-members of this group
        :param list grp_meta:
            A list of :class:`obsarchive_model.Meta` used to provide additional information about this observation
        :return:
            The :class:`obsarchive_model.ObservationGroup` as stored in the database
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
        if obs is not None:
            for item in obs:
                self.con.execute("""
INSERT INTO archive_obs_group_members (groupId, childObservation)
VALUES
((SELECT uid FROM archive_obs_groups WHERE publicId=%s), (SELECT uid FROM archive_observations WHERE publicId=%s));
""", (group_id, item))

        # Store list of subgroups into the database
        if subgroups is not None:
            for item in subgroups:
                self.con.execute("""
INSERT INTO archive_obs_group_members (groupId, childGroup)
VALUES
((SELECT uid FROM archive_obs_groups WHERE publicId=%s), (SELECT uid FROM archive_obs_groups WHERE publicId=%s));
""", (group_id, item))

        # Store the observation metadata
        if grp_meta is not None:
            for meta in grp_meta:
                self.set_obsgroup_metadata(user_id, group_id, meta, obs_time)

        obs_group = mp.ObservationGroup(group_id=group_id,
                                        title=title,
                                        obs_time=obs_time,
                                        user_id=user_id,
                                        set_time=set_time,
                                        semantic_type=semantic_type,
                                        obs_records=[],
                                        subgroups=[],
                                        meta=grp_meta)
        return obs_group

    def add_obsgroup_member(self, group_id, observation_id):
        self.con.execute("REPLACE INTO archive_obs_group_members (groupId, childObservation)  VALUES "
                         "( (SELECT uid FROM archive_obs_groups WHERE publicId=%s),"
                         "  (SELECT uid FROM archive_observations WHERE publicId=%s) );",
                         (group_id, observation_id))

    def delete_obsgroup_member(self, group_id, observation_id):
        self.con.execute("DELETE FROM archive_obs_group_members WHERE "
                         "groupId=(SELECT uid FROM archive_obs_groups WHERE publicId=%s) AND "
                         "childObservation=(SELECT uid FROM archive_observations WHERE publicId=%s);",
                         (group_id, observation_id))

    def add_obsgroup_subgroup(self, group_id, subgroup_id):
        self.con.execute("REPLACE INTO archive_obs_group_members (groupId, childGroup)  VALUES "
                         "( (SELECT uid FROM archive_obs_groups WHERE publicId=%s),"
                         "  (SELECT uid FROM archive_obs_groups WHERE publicId=%s) );",
                         (group_id, subgroup_id))

    def delete_obsgroup_subgroup(self, group_id, subgroup_id):
        self.con.execute("DELETE FROM archive_obs_group_members WHERE "
                         "groupId=(SELECT uid FROM archive_obs_groups WHERE publicId=%s) AND "
                         "childGroup=(SELECT uid FROM archive_obs_groups WHERE publicId=%s);",
                         (group_id, subgroup_id))

    def set_obsgroup_metadata(self, user_id, group_id, meta, utc=None):
        meta_id = self.get_metadata_key_id(meta.key)
        if utc is None:
            utc = mp.now()
        public_id = mp.get_hash(utc, meta.key, user_id)
        self.con.execute("""
REPLACE INTO archive_metadata (publicId, fieldId, setAtTime, setByUser, stringValue, floatValue, groupId)
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
    def get_user(self, username, password):
        """
        Retrieve a user record

        :param username:
            the username
        :param password:
            password
        :return:
            A :class:`obsarchive_model.User` if everything is correct
        :raises:
            ValueError if the user is found but password is incorrect or if the user is not found.
        """
        self.con.execute('SELECT * FROM inthesky_users WHERE username = %s;', (username,))
        results = self.con.fetchall()
        if len(results) == 0:
            raise ValueError("No such user")
        pw_hash = results[0]['password']
        # Check the password
        if not passlib.hash.bcrypt.verify(password, pw_hash):
            raise ValueError("Incorrect password")

        # Fetch list of roles
        self.con.execute('SELECT name FROM inthesky_roles r INNER JOIN inthesky_user_roles u ON u.roleId=r.roleId '
                         'WHERE u.userId = %s;', (results[0]['userId'],))
        role_list = [row['name'] for row in self.con.fetchall()]
        return mp.User(user_id=username,
                       roles=role_list,
                       name=results[0]['name'],
                       job=results[0]['job'],
                       email=results[0]['email'],
                       join_date=results[0]['joinDate'],
                       profile_pic=results[0]['profilePic'],
                       profile_text=results[0]['profileText'])

    def get_users(self):
        """
        Retrieve all users in the system

        :return:
            A list of :class:`obsarchive_model.User`
        """
        output = []
        self.con.execute('SELECT * FROM inthesky_users;')
        results = self.con.fetchall()

        for result in results:
            # Fetch list of roles
            self.con.execute('SELECT name FROM inthesky_roles r INNER JOIN inthesky_user_roles u ON u.roleId=r.roleId '
                             'WHERE u.userId = %s;', (result['userId'],))
            role_list = [row['name'] for row in self.con.fetchall()]
            output.append(mp.User(user_id=result['username'],
                                  roles=role_list,
                                  name=result['name'],
                                  job=result['job'],
                                  email=result['email'],
                                  join_date=result['joinDate'],
                                  profile_pic=result['profilePic'],
                                  profile_text=result['profileText']))
        return output

    def create_or_update_user(self, username, password, roles, name, job, email, join_date, profile_pic, profile_text):
        """
        Create a new user record, or update an existing one

        :param username:
            username to update or create
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
        self.con.execute('SELECT 1 FROM inthesky_users WHERE username = %s;', (username,))
        results = self.con.fetchall()
        if len(results) == 0:
            if password is None:
                raise ValueError("Must specify an initial password when creating a new user!")
            action = "create"
            self.con.execute('INSERT INTO inthesky_users (username, password) VALUES (%s,%s)',
                             (username, passlib.hash.bcrypt.encrypt(password)))

        if name is not None:
            self.con.execute('UPDATE inthesky_users SET name = %s WHERE username = %s', (name, username))
        if job is not None:
            self.con.execute('UPDATE inthesky_users SET job = %s WHERE username = %s', (job, username))
        if email is not None:
            self.con.execute('UPDATE inthesky_users SET email = %s WHERE username = %s', (email, username))
        if join_date is not None:
            self.con.execute('UPDATE inthesky_users SET joinDate = %s WHERE username = %s', (join_date, username))
        if profile_pic is not None:
            self.con.execute('UPDATE inthesky_users SET profilePic = %s WHERE username = %s', (profile_pic, username))
        if profile_text is not None:
            self.con.execute('UPDATE inthesky_users SET profileText = %s WHERE username = %s', (profile_text, username))

        if password is None and roles is None:
            action = "none"
        if password is not None:
            self.con.execute('UPDATE inthesky_users SET password = %s WHERE username = %s',
                             (passlib.hash.bcrypt.encrypt(password), username))
        if roles is not None:

            # Clear out existing roles, and delete any unused roles
            self.con.execute("DELETE r FROM inthesky_user_roles AS r WHERE "
                             "(SELECT u.userId FROM  inthesky_users AS u WHERE r.userId=u.userId)=%s;", (username,))
            self.con.execute("DELETE r FROM inthesky_roles AS r WHERE r.roleId NOT IN "
                             "(SELECT roleId FROM inthesky_user_roles);")

            for role in roles:
                self.con.execute("SELECT roleId FROM inthesky_roles WHERE name=%s;", (role,))
                results = self.con.fetchall()
                if len(results) < 1:
                    self.con.execute("INSERT INTO inthesky_roles (name) VALUES (%s);", (role,))
                    self.con.execute("SELECT roleId FROM inthesky_roles WHERE name=%s;", (role,))
                    results = self.con.fetchall()

                self.con.execute('INSERT INTO inthesky_user_roles (userId, roleId) VALUES '
                                 '((SELECT u.userId FROM inthesky_users u WHERE u.username=%s),'
                                 '%s)', (username, results[0]['roleId']))
            return action

    def delete_user(self, username):
        """
        Completely remove the specified username from the system

        :param string username:
            The username to remove
        """
        self.con.execute('DELETE FROM inthesky_users WHERE username = %s', (username,))

    # Functions for handling export configurations
    def get_export_configuration(self, config_id):
        """
        Retrieve the ExportConfiguration with the given ID

        :param string config_id:
            ID for which to search
        :return:
            a :class:`obsarchive_model.ExportConfiguration` or None, or no match was found.
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

        :return: a list of all :class:`obsarchive_model.ExportConfiguration` on this server
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
            a :class:`obsarchive_model.ExportConfiguration` containing the specification for the export. If this
            doesn't include a 'config_id' field it will be inserted as a new record in the database and the field will
            be populated, updating the supplied object. If it does exist already this will update the other properties
            in the database to match the supplied object.
        :returns:
            The supplied :class:`obsarchive_model.ExportConfiguration` as stored in the DB. This is guaranteed to have
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
        Apply the specified :class:`obsarchive_model.ExportConfiguration` to the database, running its contained query and
        creating rows in t_observationExport or t_fileExport for matching entities.

        :param ExportConfiguration export_config:
            An instance of :class:`obsarchive_model.ExportConfiguration` to apply.
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

    def clear_database(self, tmin=None, tmax=None, obstory_ids=None):

        if obstory_ids is None:
            obstory_ids = self.get_obstory_ids()
        if isinstance(obstory_ids, str):
            obstory_ids = [obstory_ids]

        for obstory_id in obstory_ids:
            obstory = self.get_obstory_from_id(obstory_id)
            # Purge tables - other tables are deleted by foreign key cascades from these ones.
            self.con.execute('SELECT publicId FROM archive_observations '
                             'WHERE obsTime>%s AND obsTime<%s AND observatory=%s',
                             (tmin, tmax, obstory['uid']))
            for obs in self.con.fetchall():
                self.delete_observation(obs['publicId'])
            self.con.execute('DELETE FROM archive_metadata WHERE time>%s AND time<%s AND observatory=%s',
                             (tmin, tmax, obstory['uid']))
