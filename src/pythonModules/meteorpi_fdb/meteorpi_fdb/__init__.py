from datetime import datetime, timedelta
import shutil
import uuid
from contextlib import closing

from passlib.hash import pbkdf2_sha256
import os.path as path
import os
import fdb
import meteorpi_model as mp


def first_non_null(values):
    for item in values:
        if item is not None:
            return item
    raise ValueError("No non-null item in supplied list.")


def get_installation_id():
    """Get the installation ID of the current system, using the MAC address
    rendered as a 12 character hex string."""

    def _to_array(number):
        result = ''
        n = number
        while n > 0:
            (div, mod) = divmod(n, 256)
            n = (n - mod) / 256
            result = ('%0.2x' % mod) + result
        return result

    return _to_array(uuid.getnode())


def get_day_and_offset(date):
    """
    Get the day, as a date, in which the preceding midday occurred, as well as the number of seconds since that
    midday for the specified date.
    :param date: a datetime
    :return: {day:date, seconds:int}
    """
    if date.hour <= 12:
        cdate = date - timedelta(days=1)
    else:
        cdate = date
    noon = datetime(year=cdate.year, month=cdate.month, day=cdate.day, hour=12)
    return {"day": noon, "seconds": (date - noon).total_seconds()}


def round_time(time=None):
    """
    Rounds a datetime, discarding the millisecond part.

    Needed because Python and Firebird precision is different! Default value returned is the rounded version of datetime.now()
    """
    if time is None:
        time = datetime.now()
    return time + timedelta(0, 0, -time.microsecond)


SOFTWARE_VERSION = 1


class MeteorDatabase:
    """Class representing a single MeteorPi relational database and file
    store."""

    def __init__(
            self,
            db_path='localhost:/var/lib/firebird/2.5/data/meteorpi.fdb',
            file_store_path=path.expanduser("~/meteorpi_files")):
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
        return 'MeteorDatabase(db={0}, file_store_path={1}'.format(
            self.db_path,
            self.file_store_path)

    def search_events(self, search):
        sql_args = []
        where_clauses = ['e.statusID = s.internalID']

        def _add_sql(value, clause):
            if value is not None:
                where_clauses.append(clause)
                sql_args.append(value)

        if search.camera_ids is not None and len(search.camera_ids) > 0:
            unknowns = ', '.join(list("?" for id in search.camera_ids))
            where_clauses.append('e.cameraID IN ({0})'.format(unknowns))
            for camera_id in search.camera_ids:
                sql_args.append(camera_id)
        _add_sql(search.lat_min, 's.locationLatitude >= (?)')
        _add_sql(search.lat_max, 's.locationLatitude <= (?)')
        _add_sql(search.long_min, 's.locationLongitude >= (?)')
        _add_sql(search.long_max, 's.locationLongitude <= (?)')
        _add_sql(search.before, 'e.eventTime < (?)')
        _add_sql(search.after, 'e.eventTime > (?)')
        _add_sql(search.before_offset, 'e.eventOffset < (?)')
        _add_sql(search.after_offset, 'e.eventOffset > (?)')
        # Have to handle this a bit differently as we have an NS string
        if search.event_type is not None:
            _add_sql(str(search.event_type), 'e.eventType = (?)')

        # Check for meta based constraints
        for fmc in search.meta_constraints:
            meta_key = str(fmc.key)
            ct = fmc.constraint_type
            sql_template = 'e.internalID IN (' \
                           'SELECT em.eventID FROM t_eventMeta em WHERE em.{0} {1} (?) AND em.metaKey = (?))'
            sql_args.append(fmc.value)
            sql_args.append(str(fmc.key))
            if ct == 'after':
                where_clauses.append(sql_template.format('dateValue', '>', meta_key))
            elif ct == 'before':
                where_clauses.append(sql_template.format('dateValue', '<', meta_key))
            elif ct == 'less':
                where_clauses.append(sql_template.format('floatValue', '<', meta_key))
            elif ct == 'greater':
                where_clauses.append(sql_template.format('floatValue', '>', meta_key))
            elif ct == 'number_equals':
                where_clauses.append(sql_template.format('floatValue', '=', meta_key))
            elif ct == 'string_equals':
                where_clauses.append(sql_template.format('stringValue', '=', meta_key))
            else:
                raise ValueError("Unknown meta constraint type!")

        # Build the SQL statement
        sql = 'SELECT '
        if search.limit > 0:
            sql += 'FIRST {0} '.format(search.limit)
        if search.skip > 0:
            sql += 'SKIP {0} '.format(search.skip)
        sql += 'e.cameraID, e.eventID, e.internalID, e.eventTime, e.eventType, s.statusID ' \
               'FROM t_event e, t_cameraStatus s WHERE '
        sql += ' AND '.join(where_clauses)
        sql += ' ORDER BY e.eventTime DESC'

        with closing(self.con.cursor()) as cur:
            cur.execute(sql, sql_args)
            events = list(self.get_events(cursor=cur))
            rows_returned = len(events)
            total_rows = rows_returned + search.skip
            if (rows_returned == search.limit > 0) or (rows_returned == 0 and search.skip > 0):
                count_sql = 'SELECT count(*) FROM t_event e, t_cameraStatus s WHERE ' + ' AND '.join(where_clauses)
                count_cur = self.con.cursor()
                print count_sql
                count_cur.execute(count_sql, sql_args)
                total_rows = count_cur.fetchone()[0]
            return {"count": total_rows,
                    "events": events}

    def search_files(self, search):
        sql_args = []
        where_clauses = ['f.statusID = s.internalID']

        def _add_sql(value, clause):
            if value is not None:
                where_clauses.append(clause)
                sql_args.append(value)

        if search.camera_ids is not None and len(search.camera_ids) > 0:
            unknowns = ', '.join(list("?" for id in search.camera_ids))
            where_clauses.append('f.cameraID IN ({0})'.format(unknowns))
            for camera_id in search.camera_ids:
                sql_args.append(camera_id)
        _add_sql(search.lat_min, 's.locationLatitude >= (?)')
        _add_sql(search.lat_max, 's.locationLatitude <= (?)')
        _add_sql(search.long_min, 's.locationLongitude >= (?)')
        _add_sql(search.long_max, 's.locationLongitude <= (?)')
        _add_sql(search.before, 'f.fileTime < (?)')
        _add_sql(search.after, 'f.fileTime > (?)')
        _add_sql(search.before_offset, 'f.fileOffset < (?)')
        _add_sql(search.after_offset, 'f.fileOffset > (?)')
        _add_sql(search.mime_type, 'f.mimeType = (?)')
        # Handle semantic type differently as it's based on an NSString
        if search.semantic_type is not None:
            _add_sql(str(search.semantic_type), 'f.semanticType = (?)')
        # Check for file-meta based constraints
        for fmc in search.meta_constraints:
            meta_key = str(fmc.key)
            ct = fmc.constraint_type
            sql_template = 'f.internalID IN (' \
                           'SELECT fm.fileID FROM t_fileMeta fm WHERE fm.{0} {1} (?) AND fm.metaKey = (?))'
            sql_args.append(fmc.value)
            sql_args.append(str(fmc.key))
            if ct == 'after':
                where_clauses.append(sql_template.format('dateValue', '>', meta_key))
            elif ct == 'before':
                where_clauses.append(sql_template.format('dateValue', '<', meta_key))
            elif ct == 'less':
                where_clauses.append(sql_template.format('floatValue', '<', meta_key))
            elif ct == 'greater':
                where_clauses.append(sql_template.format('floatValue', '>', meta_key))
            elif ct == 'number_equals':
                where_clauses.append(sql_template.format('floatValue', '=', meta_key))
            elif ct == 'string_equals':
                where_clauses.append(sql_template.format('stringValue', '=', meta_key))
            else:
                raise ValueError("Unknown meta constraint type!")
        # Check for avoiding event files
        if search.exclude_events:
            where_clauses.append('f.internalID NOT IN (SELECT fileID from t_event_to_file)')
        # Build the SQL statement
        sql = 'SELECT '
        if search.limit > 0:
            sql += 'FIRST {0} '.format(search.limit)
        if search.skip > 0:
            sql += 'SKIP {0} '.format(search.skip)
        sql += 'f.internalID, f.cameraID, f.mimeType, ' \
               'f.semanticType, f.fileTime, f.fileSize, f.fileID, f.fileName, s.statusID ' \
               'FROM t_file f, t_cameraStatus s WHERE ' + ' AND '.join(where_clauses)
        sql += ' ORDER BY f.fileTime DESC'

        with closing(self.con.cursor()) as cur:
            cur.execute(sql, sql_args)
            files = list(self.get_files(cursor=cur))
            rows_returned = len(files)
            total_rows = rows_returned + search.skip
            if (rows_returned == search.limit > 0) or (rows_returned == 0 and search.skip > 0):
                count_sql = 'SELECT count(*) FROM t_file f, t_cameraStatus s WHERE ' + ' AND '.join(where_clauses)
                count_cur = self.con.cursor()
                count_cur.execute(count_sql, sql_args)
                total_rows = count_cur.fetchone()[0]
            return {"count": total_rows,
                    "files": files}

    def get_events(self, event_id=None, cursor=None):
        """Retrieve Events by an eventID, or by a cursor
        which should contain a result set of rows from t_event."""
        if event_id is None and cursor is None:
            raise ValueError(
                'Must specify one of eventID or cursor!')

        # If we have a cursor use it, otherwise get one.
        _cur = cursor
        if _cur is None:
            _cur = self.con.cursor()
            _cur.execute(
                'SELECT e.cameraID, e.eventID, e.internalID, e.eventTime, '
                'e.eventType, s.statusID '
                'FROM t_event e, t_cameraStatus s '
                'WHERE e.eventID = (?) AND s.internalID = e.statusID', (event_id.bytes,))

        # Retrieve events based on supplied cursor
        def event_generator(cursor):
            for (cameraID, eventID, internalID, eventTime, eventType, statusID) in cursor:
                event = mp.Event(
                    camera_id=cameraID,
                    event_time=eventTime,
                    event_id=uuid.UUID(bytes=eventID),
                    event_type=mp.NSString.from_string(eventType),
                    status_id=uuid.UUID(bytes=statusID))
                with closing(self.con.cursor()) as cur:
                    cur.execute(
                        'SELECT f.internalID, f.cameraID, f.mimeType, '
                        'f.semanticType, f.fileTime, f.fileSize, f.fileID, f.fileName, s.statusID '
                        'FROM t_file f, t_cameraStatus s, t_event_to_file ef '
                        'WHERE f.statusID = s.internalID AND ef.fileID = f.internalID AND ef.eventID = (?)',
                        (internalID,))
                    event.file_records = list(self.get_files(cursor=cur))
                    cur.execute(
                        'SELECT metaKey, stringValue, floatValue, dateValue '
                        'FROM t_eventMeta t '
                        'WHERE t.eventID = (?) '
                        'ORDER BY metaIndex ASC',
                        (internalID,))
                    for (metaKey, stringValue, floatValue, dateValue) in cur:
                        event.meta.append(
                            mp.Meta(key=mp.NSString.from_string(metaKey),
                                    value=first_non_null([stringValue, floatValue, dateValue])))
                yield event

        return event_generator(_cur)

    def get_files(self, file_id=None, internal_id=None, cursor=None):
        if file_id is None and internal_id is None and cursor is None:
            raise ValueError('Must specify either fileID, internalID, or cursor!')

        _cur = cursor
        if _cur is None:
            _cur = self.con.cursor()
            if internal_id is not None:
                _cur.execute(
                    'SELECT t.internalID, t.cameraID, t.mimeType, '
                    't.semanticType, t.fileTime, t.fileSize, t.fileID, t.fileName, s.statusID '
                    'FROM t_file t, t_cameraStatus s WHERE t.internalID=(?) AND t.statusID = s.internalID',
                    (internal_id,))
            else:
                _cur.execute(
                    'SELECT t.internalID, t.cameraID, t.mimeType, '
                    't.semanticType, t.fileTime, t.fileSize, t.fileID, t.fileName, s.statusID '
                    'FROM t_file t, t_cameraStatus s WHERE t.fileID=(?) AND t.statusID = s.internalID',
                    (file_id.bytes,))

        def file_generator(cursor):
            for (internalID, cameraID, mimeType, semanticType, fileTime, fileSize, fileID, fileName,
                 statusID) in cursor:
                fr = mp.FileRecord(
                    camera_id=cameraID,
                    mime_type=mimeType,
                    semantic_type=mp.NSString.from_string(semanticType),
                    status_id=uuid.UUID(bytes=statusID))
                fr.file_id = uuid.UUID(bytes=fileID)
                fr.file_size = fileSize
                fr.file_time = fileTime
                fr.file_name = fileName
                fr.get_path = lambda: path.join(self.file_store_path, file_id.hex)
                with closing(self.con.cursor()) as cur:
                    cur.execute(
                        'SELECT metaKey, stringValue, floatValue, dateValue '
                        'FROM t_fileMeta t '
                        'WHERE t.fileID = (?) '
                        'ORDER BY metaIndex ASC',
                        (internalID,))
                    for (metaKey, stringValue, floatValue, dateValue) in cur:
                        fr.meta.append(
                            mp.Meta(key=mp.NSString.from_string(metaKey),
                                    value=first_non_null([stringValue, floatValue, dateValue])))
                yield fr

        return file_generator(_cur)

    def register_event(
            self,
            camera_id,
            event_time,
            event_type,
            file_records=None,
            event_meta=None):
        """Register a new row in t_event, returning the Event object."""
        if file_records is None:
            file_records = []
        if event_meta is None:
            event_meta = []
        status_id = self._get_camera_status_id(camera_id=camera_id, time=event_time)
        if status_id is None:
            raise ValueError('No status defined for camera id <%s> at time <%s>!' % (camera_id, event_time))
        cur = self.con.cursor()
        day_and_offset = get_day_and_offset(event_time)
        cur.execute(
            'INSERT INTO t_event (cameraID, eventTime, eventDay, eventOffset, eventType, '
            'statusID) '
            'VALUES (?, ?, ?, ?, ?, ?) '
            'RETURNING internalID, eventID, eventTime',
            (camera_id,
             event_time,
             day_and_offset['day'],
             day_and_offset['seconds'],
             str(event_type),
             status_id['internal_id']))
        ids = cur.fetchone()
        event_internal_id = ids[0]
        event_id = uuid.UUID(bytes=ids[1])
        event = mp.Event(camera_id=camera_id, event_time=ids[2], event_id=event_id, event_type=event_type,
                         status_id=status_id['status_id'])
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
                 meta.date_value(),
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
        Register a new row in t_file representing a file on disk.

        At the same time once the transaction has committed, move the
        file at the specified path to the local store. Returns the
        FileRecord object produced.
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
        day_and_offset = get_day_and_offset(file_time)
        cur.execute(
            'INSERT INTO t_file (cameraID, mimeType, '
            'semanticType, fileTime, fileDay, fileOffset, fileSize, statusID, fileName) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) '
            'RETURNING internalID, fileID, fileTime',
            (camera_id,
             mime_type,
             str(semantic_type),
             file_time,
             day_and_offset['day'],
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
        result_file.file_time = stored_file_time
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
                 file_meta.date_value(),
                 file_meta_index))
            result_file.meta.append(
                mp.Meta(key=file_meta.key, value=file_meta.value))
        self.con.commit()
        # Move the original file from its path
        target_file_path = path.join(self.file_store_path, result_file.file_id.hex)
        shutil.move(file_path, target_file_path)
        # Return the resultant file object
        return result_file

    def get_cameras(self):
        """Get all Camera IDs for cameras in this database with current (i.e.
        validTo == None) status blocks."""
        cur = self.con.cursor()
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
            time = datetime.now()
        time = round_time(time)
        # Set the high water mark, allowing it to advance to this point or to rollback if
        # we have data products produced after this status' time.
        self.set_high_water_mark(camera_id=camera_id, time=time, allow_rollback=True, allow_advance=True)
        cur = self.con.cursor()
        # If there's an existing status block then set its end time to now
        cur.execute(
            'UPDATE t_cameraStatus t SET t.validTo = (?) '
            'WHERE t.validTo IS NULL AND t.cameraID = (?)',
            (time,
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
             time,
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
            time = datetime.now()
        time = round_time(time)
        cur = self.con.cursor()
        cur.execute(
            'SELECT internalID, statusID FROM t_cameraStatus t '
            'WHERE t.cameraID = (?) AND t.validFrom <= (?) '
            'AND (t.validTo IS NULL OR t.validTo > (?))',
            (camera_id, time, time))
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
            time = datetime.now()
        time = round_time(time)
        cur = self.con.cursor()
        cur.execute(
            'SELECT lens, sensor, instURL, instName, locationLatitude, '
            'locationLongitude, locationGPS, locationError, orientationAltitude, '
            'orientationAzimuth, orientationError, orientationRotation, widthOfField, validFrom, validTo, '
            'softwareVersion, internalID, statusID '
            'FROM t_cameraStatus t '
            'WHERE t.cameraID = (?) AND t.validFrom <= (?) '
            'AND (t.validTo IS NULL OR t.validTo > (?))',
            (camera_id,
             time,
             time))
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
                                 gps=row['locationGPS'] == True,
                                 error=row['locationError']),
                             camera_id=camera_id,
                             status_id=uuid.UUID(bytes=row['statusID']))
        cs.valid_from = row['validFrom']
        cs.valid_to = row['validTo']
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
        cur = self.con.cursor()
        cur.execute(
            'SELECT mark FROM t_highWaterMark t WHERE t.cameraID = (?)',
            (camera_id,))
        row = cur.fetchone()
        if row is None:
            return None
        return row[0]

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
                     time))
        elif last is not None and last < time and allow_advance:
            # Defined, but new one is later, we don't really have to do much
            with closing(self.con.cursor()) as cur:
                cur.execute(
                    'UPDATE t_highWaterMark t SET t.mark = (?) WHERE t.cameraID = (?)',
                    (time,
                     camera_id))
        elif last is not None and last > time and allow_rollback:
            # More complicated, we're rolling back time so need to clean up a load
            # of future data
            with closing(self.con.cursor()) as read_cursor, closing(self.con.cursor()) as update_cursor:
                read_cursor.execute(
                    'SELECT fileID AS file_id FROM t_file '
                    'WHERE fileTime > (?) AND cameraID = (?) FOR UPDATE',
                    (time, camera_id))
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
                    (time, camera_id))
                update_cursor.execute(
                    'UPDATE t_highWaterMark t SET t.mark = (?) WHERE t.cameraID = (?)',
                    (time, camera_id))
                # Delete future status blocks
                update_cursor.execute(
                    'DELETE FROM t_cameraStatus t '
                    'WHERE t.validFrom > (?) AND t.cameraID = (?)',
                    (time, camera_id))
                # Set the new current camera status block
                update_cursor.execute(
                    'UPDATE t_cameraStatus t SET t.validTo = NULL '
                    'WHERE t.validTo >= (?) AND t.cameraID = (?)',
                    (time, camera_id))

        self.con.commit()

    def get_user(self, user_id, password):
        """
        Retrieve a user record
        :param user_id: the user ID
        :param password: password
        :return: null if the specified user isn't found, a User if everything is correct
        :raises: ValueError if the user is found but password is incorrect
        """
        cur = self.con.cursor()
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
        cur = self.con.cursor()
        cur.execute('SELECT userID, roleMask FROM t_user ORDER BY userID ASC')
        return list(mp.User(user_id=row['userID'], role_mask=row['roleMask]']) for row in cur.fetchallmap)

    def create_or_update_user(self, user_id, password, roles):
        """
        Create a new user record, or update an existing one
        :param user_id: user ID to update or create
        :param password: new password, or None to leave unchanged
        :param roles: new roles, or None to leave unchanged
        :return: the action taken, one of "none", "update", "create"
        :raises: ValueError if there is no existing user and either password or roles is None
        """
        if password is None and roles is None:
            return "none"
        cur = self.con.cursor()
        if password is not None:
            cur.execute('UPDATE t_user SET pwHash = (?) WHERE userID = (?)',
                        (pbkdf2_sha256.encrypt(password), user_id))
        if roles is not None:
            cur.execute('UPDATE t_user SET roleMask = (?) WHERE userID = (?)',
                        (mp.User.role_mask_from_roles(roles), user_id))
        if cur.rowcount == 0:
            if password is None or roles is None:
                raise ValueError("Must specify both password and roles when creating a user!")
            cur.execute('INSERT INTO t_user (userID, pwHash, roleMask) VALUES (?, ?, ?)',
                        (user_id, pbkdf2_sha256.encrypt(password), mp.User.role_mask_from_roles(roles)))
            self.con.commit()
            return "create"
        else:
            self.con.commit()
            return "update"

    def delete_user(self, user_id):
        cur = self.con.cursor()
        cur.execute('DELETE FROM t_user WHERE userID = (?)', (user_id,))
        self.con.commit()

    def clear_database(self):
        """
        Delete ALL THE THINGS!

        This doesn't reset any internal counters used to generate IDs
        but does otherwise remove all data from the database. Also
        purges all files from the fileStore
        """
        cur = self.con.cursor()
        # Purge tables - other tables are deleted by foreign key cascades from these ones.
        cur.execute('DELETE FROM t_cameraStatus')
        cur.execute('DELETE FROM t_highWaterMark')
        cur.execute('DELETE FROM t_user')
        self.con.commit()
        shutil.rmtree(self.file_store_path)
        os.makedirs(self.file_store_path)
