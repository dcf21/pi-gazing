import shutil
import uuid
from contextlib import closing
import json

from passlib.hash import pbkdf2_sha256
import os.path as path
import os
import fdb
import meteorpi_model as mp
from meteorpi_fdb.sql_builder import search_events_sql_builder, search_files_sql_builder
from meteorpi_fdb.generators import MeteorDatabaseGenerators, first_from_generator, first_non_null
from backports.functools_lru_cache import lru_cache
from meteorpi_fdb.exporter import FileExportTask, EventExportTask

SOFTWARE_VERSION = 1


class MeteorDatabase(object):
    """
    Class representing a single MeteorPi relational database and file store.

    :ivar con:
        Database connection used to access the db
    :ivar db_path:
        Path to the database
    :ivar file_store_path:
        Path to the file store on disk
    :ivar generators:
        Helper object containing generator functions to retrieve entities lazily
    :ivar string installation_id:
        The installation ID, either supplied explicitly in the constructor or derived automatically from the network
        interface MAC address (used if None is passed to the constructor for this property)
    """

    def __init__(self, db_path, file_store_path, db_user='meteorpi', db_password='meteorpi', installation_id=None):
        """
        Create a new db instance. This connects to the specified firebird database and retains a connection which is
        then used by methods in this class when querying or updating the database.

        :param string db_path:
            String passed to the firebird database driver and specifying a file location. Defaults to
        :param string file_store_path:
            File data is stored on the file system in a flat structure within the specified directory. If this location
            doesn't exist it will be created, along with any necessary parent directories.
        :param string db_user:
            User for the database, defaults to 'meteorpi'
        :param string db_password:
            Password for the database, defaults to 'meteorpi'
        :param string installation_id:
            12 Character string containing the installation ID which will be used as the default when registering new
            files and events to this database. If set to none this will default to an attempt to calculate the ID from
            the MAC address of the first network interface found.
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
        self.generators = MeteorDatabaseGenerators(db=self)
        if installation_id is None:
            def _to_array(number):
                result = ''
                n = number
                while n > 0:
                    (div, mod) = divmod(n, 256)
                    n = (n - mod) / 256
                    result = ('%0.2x' % mod) + result
                return result

            installation_id = _to_array(uuid.getnode())
        if len(installation_id) != 12:
            raise ValueError("Installation ID must be exactly 12 characters long, but was {0}".format(installation_id))
        self.installation_id = installation_id

    def __str__(self):
        """Simple string representation of this db object

        :return:
            info about the db path and file store location
        """
        return 'MeteorDatabase(db={0}, file_store_path={1}'.format(
            self.db_path,
            self.file_store_path)

    def file_path_for_id(self, file_id):
        """
        Get the system file path for a given file ID. Does not guarantee that the file exists!

        :param uuid.UUID file_id:
            ID of a file (which may or may not exist, this method doesn't check)
        :return:
            System file path for the file
        """
        return path.join(self.file_store_path, file_id.hex)

    def has_file_id(self, file_id):
        """
        Check for the presence of the given file_id

        :param uuid.UUID event_id:
            The file ID
        :return:
            True if we have a :class:`meteorpi_model.FileRecord` with this ID, False otherwise
        """
        with closing(self.con.cursor()) as cursor:
            cursor.execute('SELECT * FROM t_file WHERE fileID = (?)', (file_id.bytes,))
            return cursor.fetchone() is not None

    def get_file(self, file_id):
        """
        Retrieve an existing :class:`meteorpi_model.FileRecord` by its ID

        :param uuid.UUID file_id:
            UUID of the file record
        :return:
            A :class:`meteorpi_model.FileRecord` instance, or None if not found
        """
        sql = 'SELECT t.internalID, t.cameraID, t.mimeType, ' \
              't.semanticType, t.fileTime, t.fileSize, t.fileID, t.fileName, s.statusID, t.MD5HEX ' \
              'FROM t_file t, t_cameraStatus s WHERE t.fileID=(?) AND t.statusID = s.internalID'
        return first_from_generator(self.generators.file_generator(sql=sql, sql_args=(file_id.bytes,)))

    def search_files(self, search):
        """
        Search for :class:`meteorpi_model.FileRecord` entities

        :param search:
            an instance of :class:`meteorpi_model.FileRecordSearch` used to constrain the events returned from the DB
        :return:
            a structure of {count:int total rows of an unrestricted search, events:list of
            :class:`meteorpi_model.FileRecord`}
        """
        b = search_files_sql_builder(search)
        sql = b.get_select_sql(columns='f.internalID, f.cameraID, f.mimeType, f.semanticType, f.fileTime, '
                                       'f.fileSize, f.fileID, f.fileName, s.statusID, f.md5Hex',
                               skip=search.skip,
                               limit=search.limit,
                               order='f.fileTime DESC')
        files = list(self.generators.file_generator(sql=sql, sql_args=b.sql_args))
        rows_returned = len(files)
        total_rows = rows_returned + search.skip
        if (rows_returned == search.limit > 0) or (rows_returned == 0 and search.skip > 0):
            with closing(self.con.cursor()) as cur:
                cur.execute(b.get_count_sql(), b.sql_args)
                total_rows = cur.fetchone()[0]
        return {"count": total_rows,
                "files": files}

    def register_file(self, file_path, mime_type, semantic_type, file_time, file_metas, camera_id=None, file_name=None):
        """
        Register a file in the database, also moving the file into the file store. Returns the corresponding FileRecord
        object.

        :param string file_path:
            The path of the file on disk to register. This file will be moved into the file store and renamed.
        :param string mime_type:
            MIME type of the file
        :param NSString semantic_type:
            A :class:`meteorpi_model.NSString` defining the semantic type of the file
        :param datetime file_time:
            UTC datetime for the file
        :param list[Meta] file_metas:
            A list of :class:`meteorpi_model.Meta` describing additional properties of the file
        :param string camera_id:
            The camera ID which created this file. If not specified defaults to the current installation ID
        :param string file_name:
            An optional file name, primarily used to display in the UI and provide help when downloading.
        :return:
            The resultant :class:`meteorpi_model.FileRecord` as stored in the database
        """
        # Check the file exists, and retrieve its size
        if camera_id is None:
            camera_id = self.installation_id
        if not path.exists(file_path):
            raise ValueError('No file exists at {0}'.format(file_path))
        file_size_bytes = os.stat(file_path).st_size
        md5 = mp.get_md5_hash(file_path)
        # Handle the database parts
        status_id = self._get_camera_status_id(camera_id=camera_id, time=file_time)
        if status_id is None:
            raise ValueError('No status defined for camera id {0} at time {1}!'.format(camera_id, file_time))
        with closing(self.con.trans()) as transaction:
            with closing(transaction.cursor()) as cur:
                day_and_offset = mp.get_day_and_offset(file_time)
                cur.execute(
                    'INSERT INTO t_file (cameraID, mimeType, '
                    'semanticType, fileTime, fileOffset, fileSize, statusID, fileName, md5Hex) '
                    'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) '
                    'RETURNING internalID, fileID, fileTime',
                    (camera_id,
                     mime_type,
                     str(semantic_type),
                     mp.utc_datetime_to_milliseconds(file_time),
                     day_and_offset['seconds'],
                     file_size_bytes,
                     status_id['internal_id'],
                     file_name,
                     md5))
                row = cur.fetchonemap()
                # Retrieve the internal ID of the file row to link fileMeta if required
                file_internal_id = row['internalID']
                # Retrieve the generated file ID, used to build the File object and to
                # name the source file
                file_id = uuid.UUID(bytes=row['fileID'])
                # Retrieve the file time as stored in the DB
                stored_file_time = row['fileTime']
                result_file = mp.FileRecord(camera_id=camera_id, mime_type=mime_type, semantic_type=semantic_type,
                                            status_id=status_id['status_id'], md5=md5)
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
            transaction.commit()
        # Move the original file from its path
        target_file_path = path.join(self.file_store_path, result_file.file_id.hex)
        shutil.move(file_path, target_file_path)
        # Return the resultant file object
        return result_file

    def has_event_id(self, event_id):
        """
        Check for the presence of the given event_id

        :param uuid.UUID event_id:
            The event ID
        :return:
            True if we have a :class:`meteorpi_model.Event` with this ID, False otherwise
        """
        with closing(self.con.cursor()) as cursor:
            cursor.execute('SELECT * FROM t_event WHERE eventID = (?)', (event_id.bytes,))
            return cursor.fetchone() is not None

    def get_event(self, event_id):
        """
        Retrieve an existing :class:`meteorpi_model.Event` by its ID

        :param uuid.UUID event_id:
            UUID of the event
        :return:
            A :class:`meteorpi_model.Event` instance, or None if not found
        """
        sql = 'SELECT e.cameraID, e.eventID, e.internalID, e.eventTime, ' \
              'e.eventType, s.statusID ' \
              'FROM t_event e, t_cameraStatus s ' \
              'WHERE e.eventID = (?) AND s.internalID = e.statusID'
        return first_from_generator(self.generators.event_generator(sql=sql, sql_args=(event_id.bytes,)))

    def search_events(self, search):
        """
        Search for :class:`meteorpi_model.Event` entities

        :param search:
            an instance of :class:`meteorpi_model.EventSearch` used to constrain the events returned from the DB
        :return:
            a structure of {count:int total rows of an unrestricted search, events:list of
            :class:`meteorpi_model.Event`}
        """
        b = search_events_sql_builder(search)
        sql = b.get_select_sql(columns='e.cameraID, e.eventID, e.internalID, e.eventTime, e.eventType, s.statusID',
                               skip=search.skip,
                               limit=search.limit,
                               order='e.eventTime DESC')
        events = list(self.generators.event_generator(sql, b.sql_args))
        rows_returned = len(events)
        total_rows = rows_returned + search.skip
        if (rows_returned == search.limit > 0) or (rows_returned == 0 and search.skip > 0):
            with closing(self.con.cursor()) as count_cur:
                count_cur.execute(b.get_count_sql(), b.sql_args)
                total_rows = count_cur.fetchone()[0]
        return {"count": total_rows,
                "events": events}

    def register_event(self, camera_id, event_time, event_type, file_records=None, event_meta=None):
        """
        Register a new event, updating the database and returning the corresponding Event object

        :param string camera_id:
            The ID of the camera which produced this event
        :param datetime event_time:
            The UTC datetime of the event
        :param NSString event_type:
            A :class:`meteorpi_model.NSString` describing the semantic type of this event
        :param file_records:
            A list of :class:`meteorpi_model.FileRecord` associated with this event. These must already exist, typically
            multiple calls would be made to register_file() before registering the associated event
        :param event_meta:
            A list of :class:`meteorpi_model.Meta` used to provide additional information about this event
        :return:
            The :class:`meteorpi_model.Event` as stored in the database
        """
        if file_records is None:
            file_records = []
        if event_meta is None:
            event_meta = []
        status_id = self._get_camera_status_id(camera_id=camera_id, time=event_time)
        if status_id is None:
            raise ValueError('No status defined for camera id <%s> at time <%s>!' % (camera_id, event_time))
        with closing(self.con.trans()) as transaction:
            with closing(transaction.cursor()) as cur:
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
            transaction.commit()
        return event

    def get_cameras(self):
        """
        Retrieve the IDs of all cameras with active status blocks. As the model has changed somewhat since this code
        was first written this in effect means the IDs of all cameras we've ever seen, as we no longer have a 'valid_to'
        entry in the status table.

        :return:
            A list of camera IDs for all cameras with status blocks
        """
        with closing(self.con.cursor()) as cur:
            cur.execute(
                'SELECT DISTINCT cameraID FROM t_cameraStatus '
                'ORDER BY cameraID DESC')
            return map(lambda row: row[0], cur.fetchall())

    def has_status_id(self, status_id):
        """
        Check for the presence of the given status_id

        :param uuid.UUID status_id:
            The camera status ID
        :return:
            True if we have a :class:`meteorpi_model.CameraStatus` with this ID, False otherwise
        """
        with closing(self.con.cursor()) as cursor:
            cursor.execute('SELECT * FROM t_cameraStatus WHERE statusID = (?)', (status_id.bytes,))
            return cursor.fetchone() is not None

    def get_camera_status(self, time=None, camera_id=None):
        """
        Return the camera status for a given time, or None if no status is available.

        :param datetime.datetime time:
            UTC time at which we want to know the camera status ID, defaults to model.now() if not specified
        :param string camera_id:
            The ID of the camera to query, defaults to the current installation ID if not specified
        :return:
            A :class:`meteorpi_model.CameraStatus` or None if no status was available
        """
        if time is None:
            time = mp.now()
        if camera_id is None:
            camera_id = self.installation_id
        sql = ('SELECT lens, sensor, instURL, instName, locationLatitude, '
               'locationLongitude, locationGPS, locationError, orientationAltitude, '
               'orientationAzimuth, orientationError, orientationRotation, widthOfField, validFrom, '
               'softwareVersion, internalID, statusID, cameraID '
               'FROM t_cameraStatus t '
               'WHERE t.cameraID = (?) AND t.validFrom <= (?) '
               'ORDER BY t.validFrom DESC '
               'ROWS 1')
        return first_from_generator(
            self.generators.camera_status_generator(sql, (camera_id, mp.utc_datetime_to_milliseconds(time))))

    def get_camera_status_by_id(self, status_id):
        """
        Return the camera status block with the given UUID

        :param uuid.UUID status_id:
            UUID of the camera status
        :return:
            An instance of :class:`meteorpi_model.CameraStatus` or None if none matched.
        """
        sql = ('SELECT lens, sensor, instURL, instName, locationLatitude, '
               'locationLongitude, locationGPS, locationError, orientationAltitude, '
               'orientationAzimuth, orientationError, orientationRotation, widthOfField, validFrom, '
               'softwareVersion, internalID, statusID, cameraID '
               'FROM t_cameraStatus t '
               'WHERE t.statusID = (?)')
        return first_from_generator(self.generators.camera_status_generator(sql, (status_id.bytes,)))

    def update_camera_status(self, ns, time=None, camera_id=None):
        """
        Update the status for a camera, optionally specify a time (defaults to model.now()).

        If the time is earlier than the current high water mark for this
        camera any data products derived after that time will be deleted
        as if setHighWaterMark was called.

        Clears the status cache.

        :param CameraStatus ns:
            The new camera status. If an existing camera status is supplied (one with an assigned ID) the ID will be
            ignored and a new one generated, this makes it easier to update a camera status by retrieving it, modifying
            fields and then calling this method.
        :param datetime.datetime time:
            The time from which the new status should apply, defaults to now if not specified, should be a UTC time.
        :param string camera_id:
            The camera to which this status applies, or the default installation ID if not specified
        """
        if time is None:
            time = mp.now()
        if camera_id is None:
            camera_id = self.installation_id
        # Set the high water mark, allowing it to advance to this point or to rollback if
        # we have data products produced after this status' time.
        self.set_high_water_mark(camera_id=camera_id, time=time, allow_rollback=True, allow_advance=True)
        with closing(self.con.trans()) as transaction:
            with closing(transaction.cursor()) as cur:
                # Insert the new status into the database
                cur.execute(
                    'INSERT INTO t_cameraStatus (cameraID, validFrom, '
                    'softwareVersion, orientationAltitude, orientationAzimuth, '
                    'orientationRotation, orientationError, widthOfField, locationLatitude, locationLongitude, '
                    'locationGPS, lens, sensor, instURL, instName, locationError) '
                    'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) '
                    'RETURNING internalID',
                    (camera_id,
                     mp.utc_datetime_to_milliseconds(time),
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
            transaction.commit()
        self.generators.cache_clear(cache='status')

    @lru_cache(maxsize=128)
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
        with closing(self.con.cursor()) as cur:
            cur.execute('SELECT userID, pwHash, roleMask FROM t_user WHERE userID = (?)', (user_id,))
            row = cur.fetchonemap()
            if row is None:
                raise ValueError("No such user")
            pw_hash = row['pwHash']
            role_mask = row['roleMask']
            # Check the password
            if pbkdf2_sha256.verify(password, pw_hash):
                return mp.User(user_id=user_id, role_mask=role_mask)
            else:
                raise ValueError("Incorrect password")

    def get_users(self):
        """
        Retrieve all users in the system

        :return:
            A list of :class:`meteorpi_model.User`
        """
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
        with closing(self.con.trans()) as transaction:
            with closing(transaction.cursor()) as cur:
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
                    transaction.commit()
                    self.get_user.cache_clear()
                    return "create"
                else:
                    transaction.commit()
                    self.get_user.cache_clear()
                    return "update"

    def delete_user(self, user_id):
        """
        Completely remove the specified user ID from the system

        :param string user_id:
            The user_id to remove
        """
        with closing(self.con.trans()) as transaction:
            with closing(transaction.cursor()) as cur:
                cur.execute('DELETE FROM t_user WHERE userID = (?)', (user_id,))
            transaction.commit()
        self.get_user.cache_clear()

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
        return first_from_generator(
            self.generators.export_configuration_generator(sql=sql, sql_args=(config_id.bytes,)))

    def get_export_configurations(self):
        """
        Retrieve all ExportConfigurations held in this db

        :return: a list of all :class:`meteorpi_model.ExportConfiguration` on this server
        """
        sql = (
            'SELECT internalID, exportConfigID, exportType, searchString, targetURL, '
            'targetUser, targetPassword, exportName, description, active '
            'FROM t_exportConfig ORDER BY internalID DESC')
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
        with closing(self.con.trans()) as transaction:
            with closing(transaction.cursor()) as cur:
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
            transaction.commit()
        self.generators.cache_clear(cache='export')
        return export_config

    def delete_export_configuration(self, config_id):
        """
        Delete a file export configuration by external UUID

        :param uuid.UUID config_id: the ID of the config to delete
        """
        self.generators.cache_clear(cache='export')
        with closing(self.con.trans()) as transaction:
            with closing(transaction.cursor()) as cur:
                cur.execute('DELETE FROM t_exportConfig c WHERE c.exportConfigId = (?)', (config_id.bytes,))
            transaction.commit()

    def mark_entities_to_export(self, export_config):
        """
        Apply the specified :class:`meteorpi_model.ExportConfiguration` to the database, running its contained query and
        creating rows in t_eventExport or t_fileExport for matching entities.

        :param ExportConfiguration export_config:
            An instance of :class:`meteorpi_model.ExportConfiguration` to apply.
        :returns:
            The integer number of rows added to the export tables
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
            search.exclude_export_to = export_config.config_id
            b = search_events_sql_builder(search)
            with closing(self.con.trans()) as transaction:
                with closing(self.con.cursor()) as read_cursor, closing(transaction.cursor()) as write_cursor:
                    read_cursor.execute(b.get_select_sql(columns='e.internalID'), b.sql_args)
                    for (internalID,) in read_cursor:
                        write_cursor.execute('INSERT INTO t_eventExport '
                                             '(eventID, exportConfig, exportTime, exportState) '
                                             'VALUES (?,?,?,?)',
                                             (internalID, export_config_id, timestamp, 1))
                        rows_created += 1
                transaction.commit()
        # Handle FileRecordSearch
        elif isinstance(export_config.search, mp.FileRecordSearch):
            # Create a deep copy of the search and set the properties required when creating exports
            search = mp.FileRecordSearch.from_dict(export_config.search.as_dict())
            search.exclude_events = True
            search.exclude_export_to = export_config.config_id
            b = search_files_sql_builder(search)
            with closing(self.con.trans()) as transaction:
                with closing(self.con.cursor()) as read_cursor, closing(transaction.cursor()) as write_cursor:
                    read_cursor.execute(b.get_select_sql(columns='f.internalID'), b.sql_args)
                    for (internalID,) in read_cursor:
                        write_cursor.execute('INSERT INTO t_fileExport '
                                             '(fileID, exportConfig, exportTime, exportState) '
                                             'VALUES (?,?,?,?)',
                                             (internalID, export_config_id, timestamp, 1))
                        rows_created += 1
                transaction.commit()
        # Complain if it's anything other than these two (nothing should be at the moment but we might introduce
        # more search types in the future
        else:
            raise ValueError("Unknown search type")
        return rows_created

    def defer_export_tasks(self, config_id, seconds):
        """
        Increment the export time of all events for a given config such that the earliest is `seconds` into the future

        :param uuid.UUID config_id:
            The UUID of an export configuration
        :param int seconds:
            The number of seconds by which tasks associated with this export configuration should be delayed. Any tasks
            that would occur before (now + seconds) are instead marked to occur at exactly that time. Tasks which were
            scheduled for further in the future, or for other export configurations, are not changed.
        """
        later = mp.utc_datetime_to_milliseconds(mp.now()) + 1000 * seconds
        with closing(self.con.trans()) as transaction:
            with closing(transaction.cursor()) as cursor:
                cursor.execute('SELECT c.internalID FROM t_exportConfig c WHERE c.exportConfigID=(?)',
                               (config_id.bytes,))
                row = cursor.fetchone()
                if row is None:
                    raise ValueError("No configuration with id {0} found!".format(config_id))
                config_internal_id = row[0]
                cursor.execute('UPDATE t_eventExport ex SET ex.exportTime = (?) '
                               'WHERE ex.exportTime < (?) '
                               'AND ex.exportConfig = (?) ',
                               (later, later, config_internal_id))
                cursor.execute('UPDATE t_fileExport fx SET fx.exportTime = (?) '
                               'WHERE fx.exportTime < (?) '
                               'AND fx.exportConfig = (?) ',
                               (later, later, config_internal_id))
            transaction.commit()

    def get_next_entity_to_export(self):
        """
        Examines the t_fileExport and t_eventExport tables, finds the earliest incomplete export task and builds
        either a :class:`meteorpi_fdb.FileExportTask` or a :class:`meteorpi_fdb.EventExportTask` as appropriate. These
        task objects can be used to retrieve the underlying entity and export configuration, and to update the
        completion state or push the timestamp into the future, deferring evaluation of the task until later. Only
        considers tasks where the timestamp is before (or equal to) the current time.

        :returns:
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

    def import_event(self, event, user_id):
        """
        Functionality used by the import API, pulls in a :class:`meteorpi_model.Event` including its pre-existing links
        to camera status and UUID. Do not use this to register a new event, it is only for use by the import system,
        this system ensures that all pre-requisites (files, camera status etc) are in place. If you use it outside of
        this context you will break your database. Don't.

        :param Event event:
            The :class:`meteorpi_model.Event` instance to import
        :param string user_id:
            The user_id of the importing :class:`meteorpi_model.User`
        :internal:
        """
        if self.has_event_id(event.event_id):
            return
        status_id = self._get_camera_status_id(camera_id=event.camera_id, time=event.event_time)
        if status_id is None:
            raise ValueError(
                'No status defined for camera id {0} at time {1}!'.format(event.camera_id, event.event_time))
        if status_id['status_id'].hex != event.status_id.hex:
            raise ValueError('Existing status and supplied status IDs must be equal')
        day_and_offset = mp.get_day_and_offset(event.event_time)
        # Import the file records first
        file_internal_ids = list(self.import_file_record(file_record=f, user_id=user_id) for f in event.file_records)
        # Import the event
        with closing(self.con.trans()) as transaction:
            with closing(transaction.cursor()) as cur:
                cur.execute(
                    'INSERT INTO t_event (cameraID, eventTime, eventOffset, eventType, '
                    'statusID, eventID) '
                    'VALUES (?, ?, ?, ?, ?, ?) '
                    'RETURNING internalID, eventID, eventTime',
                    (event.camera_id,
                     mp.utc_datetime_to_milliseconds(event.event_time),
                     day_and_offset['seconds'],
                     str(event.event_type),
                     status_id['internal_id'],
                     event.event_id.bytes))
                ids = cur.fetchone()
                event_internal_id = ids[0]
                # Insert into event import table
                cur.execute('INSERT INTO t_eventImport (eventID, importUser, importTime) VALUES (?, ?, ?)',
                            (event_internal_id, user_id, mp.utc_datetime_to_milliseconds(mp.now())))
                for file_record_index, file_internal_id in enumerate(file_internal_ids):
                    cur.execute(
                        'INSERT INTO t_event_to_file '
                        '(fileID, eventID, sequenceNumber) '
                        'VALUES (?, ?, ?)',
                        (file_internal_id,
                         event_internal_id,
                         file_record_index))
                for meta_index, meta in enumerate(event.meta):
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
            transaction.commit()

    def import_file_record(self, file_record, user_id):
        """
        Used by the import system to import a previously instantiated and named :class:`meteorpi_model.FileRecord`. Do
        not use this method outside of the import system, this system will ensure that any pre-requisite status or file
        data is in place, using this method directly will certainly break your database.

        :param FileRecord file_record:
            The :class:`meteorpi_model.FileRecord` to import
        :param string user_id:
            The user_id of the importing :class:`meteorpi_model.User`
        :return:
            The integer internal ID of the imported record, used when importing events to create the link tables without
            additional database queries.
        :internal:
        """
        if self.has_file_id(file_record.file_id):
            return
        if not path.exists(self.file_path_for_id(file_record.file_id)):
            raise ValueError('Must get the binary file before importing FileRecord')
        status_id = self._get_camera_status_id(camera_id=file_record.camera_id, time=file_record.file_time)
        if status_id is None:
            raise ValueError(
                'No status defined for camera id {0} at time {1}!'.format(file_record.camera_id, file_record.file_time))
        if status_id['status_id'].hex != file_record.status_id.hex:
            raise ValueError('Existing status and supplied status IDs must be equal')
        day_and_offset = mp.get_day_and_offset(file_record.file_time)
        with closing(self.con.trans()) as transaction:
            with closing(transaction.cursor()) as cur:
                cur.execute(
                    'INSERT INTO t_file (cameraID, mimeType, '
                    'semanticType, fileTime, fileOffset, fileSize, statusID, fileName, fileID, md5Hex) '
                    'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) '
                    'RETURNING internalID, fileID, fileTime',
                    (file_record.camera_id,
                     file_record.mime_type,
                     str(file_record.semantic_type),
                     mp.utc_datetime_to_milliseconds(file_record.file_time),
                     day_and_offset['seconds'],
                     file_record.file_size,
                     status_id['internal_id'],
                     file_record.file_name,
                     file_record.file_id.bytes,
                     file_record.md5))
                row = cur.fetchonemap()
                # Retrieve the internal ID of the file row to link fileMeta if required
                file_internal_id = row['internalID']
                # Insert into file import table
                cur.execute('INSERT INTO t_fileImport (fileID, importUser, importTime) VALUES (?, ?, ?)',
                            (file_internal_id, user_id, mp.utc_datetime_to_milliseconds(mp.now())))
                for file_meta_index, file_meta in enumerate(file_record.meta):
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
            transaction.commit()
        return file_internal_id

    def import_camera_status(self, status):
        """
        Import a new camera status block, used by the import server - do not use this for local status changes, it
        doesn't update high water marks and will not execute any kind of roll-back. Clears the status cache, as camera
        status instances are somewhat dynamically generated based on other instances, most particularly for their time
        ranges.

        :param status:
            The new camera status block to import, this must be pre-populated with all required fields.
        """
        with closing(self.con.trans()) as transaction:
            with closing(transaction.cursor()) as cur:
                # Insert the new status into the database
                cur.execute(
                    'INSERT INTO t_cameraStatus (statusID, cameraID, validFrom, '
                    'softwareVersion, orientationAltitude, orientationAzimuth, '
                    'orientationRotation, orientationError, widthOfField, locationLatitude, locationLongitude, '
                    'locationGPS, lens, sensor, instURL, instName, locationError) '
                    'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) '
                    'RETURNING internalID',
                    (status.status_id.bytes,
                     status.camera_id,
                     mp.utc_datetime_to_milliseconds(status.valid_from),
                     SOFTWARE_VERSION,
                     status.orientation.altitude,
                     status.orientation.azimuth,
                     status.orientation.rotation,
                     status.orientation.error,
                     status.orientation.width_of_field,
                     status.location.latitude,
                     status.location.longitude,
                     status.location.gps,
                     status.lens,
                     status.sensor,
                     status.inst_url,
                     status.inst_name,
                     status.location.error))
                # Retrieve the newly created internal ID for the status block, use this to
                # insert visible regions
                status_internal_id = cur.fetchone()[0]
                for region_index, region in enumerate(status.regions):
                    for point_index, point in enumerate(region):
                        cur.execute(
                            'INSERT INTO t_visibleRegions (cameraStatusID, '
                            'region, pointOrder, x, y) VALUES (?,?,?,?,?)',
                            (status_internal_id,
                             region_index,
                             point_index,
                             point['x'],
                             point['y']))
            transaction.commit()
        self.generators.cache_clear(cache='status')

    def get_high_water_mark(self, camera_id=None):
        """
        Retrieves the high water mark for a given camera, defaulting to the current installation ID

        :param string camera_id:
            The camera ID to check for, or the default installation ID if not specified
        :return:
            A UTC datetime for the high water mark, or None if none was found.
        """
        if camera_id is None:
            camera_id = self.installation_id
        with closing(self.con.cursor()) as cur:
            cur.execute(
                'SELECT mark FROM t_highWaterMark t WHERE t.cameraID = (?)',
                (camera_id,))
            row = cur.fetchone()
            if row is None:
                return None
            return mp.milliseconds_to_utc_datetime(row[0])

    def set_high_water_mark(self, time, camera_id=None, allow_rollback=True, allow_advance=True):
        """
        Sets the 'high water mark' for this installation.

        This is the latest point before which all data has been
        processed, when this call is made any data products (events,
        images etc) with time stamps later than the high water mark will
        be removed from the database. Any camera status blocks with
        validFrom dates after the high water mark will be removed.

        :internal:
        """
        if camera_id is None:
            camera_id = self.installation_id
        last = self.get_high_water_mark(camera_id)
        with closing(self.con.trans()) as transaction:
            if last is None and allow_advance:
                # No high water mark defined, set it and return
                with closing(transaction.cursor()) as cur:
                    cur.execute(
                        'INSERT INTO t_highWaterMark (cameraID, mark) VALUES (?,?)',
                        (camera_id,
                         mp.utc_datetime_to_milliseconds(time)))
            elif last is not None and last < time and allow_advance:
                # Defined, but new one is later, we don't really have to do much
                with closing(transaction.cursor()) as cur:
                    cur.execute(
                        'UPDATE t_highWaterMark t SET t.mark = (?) WHERE t.cameraID = (?)',
                        (mp.utc_datetime_to_milliseconds(time),
                         camera_id))
            elif last is not None and last > time and allow_rollback:
                # More complicated, we're rolling back time so need to clean up a load
                # of future data
                with closing(self.con.cursor()) as read_cursor, closing(transaction.cursor()) as update_cursor:
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
            transaction.commit()

    def _get_camera_status_id(self, time=None, camera_id=None):
        """
        Return the integer internal ID and UUID of the camera status block for the given time and camera, or None if
        there wasn't one available

        :param datetime.datetime time:
            UTC time at which we want to know the camera status ID, defaults to model.now() if not specified
        :param string camera_id:
            The ID of the camera to query, defaults to the current installation ID if not specified
        :return:
            A dict with 'internal_id' set to the integer ID of the row, and 'status_id' to the UUID of the status block
        :internal:
        """
        if time is None:
            time = mp.now()
        if camera_id is None:
            camera_id = self.installation_id
        with closing(self.con.cursor()) as cur:
            cur.execute(
                'SELECT internalID, statusID FROM t_cameraStatus t '
                'WHERE t.cameraID = (?) AND t.validFrom <= (?) '
                'ORDER BY t.validFrom DESC '
                'ROWS 1',
                (camera_id, mp.utc_datetime_to_milliseconds(time), mp.utc_datetime_to_milliseconds(time)))
            row = cur.fetchone()
            if row is None:
                return None
            return {'internal_id': row[0], 'status_id': uuid.UUID(bytes=row[1])}

    def clear_database(self):
        """
        Delete ALL THE THINGS!

        This doesn't reset any internal counters used to generate IDs
        but does otherwise remove all data from the database. Also
        purges all files from the fileStore
        """
        # Purge tables - other tables are deleted by foreign key cascades from these ones.
        with closing(self.con.trans()) as transaction:
            with closing(transaction.cursor()) as cur:
                cur.execute('DELETE FROM t_cameraStatus')
                cur.execute('DELETE FROM t_highWaterMark')
                cur.execute('DELETE FROM t_user')
                cur.execute('DELETE FROM t_exportConfig')
            transaction.commit()
        self.get_user.cache_clear()
        for cache_name in ['file', 'status', 'event', 'export']:
            self.generators.cache_clear(cache=cache_name)
        shutil.rmtree(self.file_store_path)
        os.makedirs(self.file_store_path)
