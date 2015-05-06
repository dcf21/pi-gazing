from datetime import datetime, timedelta
import os.path as path
import os
import shutil
import uuid

import fdb

import meteorpi_model as mp














# http://www.firebirdsql.org/file/documentation/drivers_documentation/python/fdb/getting-started.html
# is helpful!

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
        """Search for events based on an EventSearch"""
        # ",".join(str(bit) for bit in l)
        def _search_events(camera_id=None):
            sql_args = []
            where_clauses = []
            if camera_id is not None:
                where_clauses.append('e.cameraID = (?)')
                sql_args.append(camera_id)
            if search.lat_min is not None:
                where_clauses.append('s.locationLatitude >= (?)')
                sql_args.append(search.lat_min)
            if search.lat_max is not None:
                where_clauses.append('s.locationLatitude <= (?)')
                sql_args.append(search.lat_max)
            if search.long_min is not None:
                where_clauses.append('s.locationLongitude >= (?)')
                sql_args.append(search.long_min)
            if search.long_max is not None:
                where_clauses.append('s.locationLongitude <= (?)')
                sql_args.append(search.long_max)
            if search.before is not None:
                where_clauses.append('e.eventTime <= (?)')
                sql_args.append(search.before)
            if search.after is not None:
                where_clauses.append('e.eventTime >= (?)')
                sql_args.append(search.after)
            # Build the SQL statement
            sql = 'SELECT e.cameraID, e.eventID, e.internalID, e.eventTime, e.intensity, ' \
                  'e.x1, e.y1, e.x2, e.y2, e.x3, e.y3, e.x4, e.y4 ' \
                  'FROM t_event e, t_cameraStatus s WHERE e.statusID = s.internalID'
            if len(sql_args) > 0:
                sql += ' AND '
            sql += ' AND '.join(where_clauses)
            cur = self.con.cursor()
            cur.execute(sql, sql_args)
            return self.get_events(cursor=cur)

        camera_ids = search.camera_ids
        if camera_ids is None:
            camera_ids = [None]
        result = []
        for camera_id in camera_ids:
            for event in _search_events(camera_id):
                result.append(event)
        return result


    def get_events(self, event_id=None, internal_ids=None, cursor=None):
        """Retrieve Events by an eventID, set of internalIDs or by a cursor
        which should contain a result set of rows from t_event."""
        if event_id is None and internal_ids is None and cursor is None:
            raise ValueError(
                'Must specify one of eventID, internalIDs or cursor!')
        # If we have a cursor use it, otherwise get one.
        if cursor is None:
            _cur = self.con.cursor()
            if event_id is not None:
                # Use event ID
                _cur.execute(
                    'SELECT cameraID, eventID, internalID, eventTime, '
                    'intensity, x1, y1, x2, y2, x3, y3, x4, y4 '
                    'FROM t_event '
                    'WHERE eventID = (?)', (event_id.bytes,))
            else:
                _cur.execute(
                    'SELECT cameraID, eventID, internalID, eventTime, '
                    'intensity, x1, y1, x2, y2, x3, y3, x4, y4 '
                    'FROM t_event '
                    'WHERE internalID IN (?)', (internal_ids,))
        else:
            _cur = cursor
        events = {}
        for row in _cur.fetchallmap():
            events[str(row['internalID'])] = mp.Event(
                row['cameraID'],
                row['eventTime'],
                uuid.UUID(bytes=row['eventID']),
                row['intensity'] / 1000.0,
                mp.Bezier(row['x1'], row['y1'], row['x2'], row['y2'],
                          row['x3'], row['y3'], row['x4'], row['y4']),
                [])
        result = []
        for internal_id, event in events.iteritems():
            _cur.execute(
                'SELECT fileID from t_event_to_file '
                'WHERE eventID = (?) '
                'ORDER BY sequenceNumber ASC', (internal_id,))
            for row in _cur.fetchallmap():
                event.file_records.append(self.get_file(internal_id=row['fileID']))
            result.append(event)
        return result


    def register_event(
            self,
            camera_id,
            event_time,
            intensity,
            bezier,
            file_records=[]):
        """Register a new row in t_event, returning the Event object."""
        if intensity > 1.0:
            raise ValueError('Intensity must be at most 1.0')
        if intensity < 0:
            raise ValueError('Intensity must not be negative')
        status_id = self._get_camera_status_id(camera_id=camera_id, time=event_time)
        if status_id is None:
            raise ValueError('No status defined for this ID and time!')
        cur = self.con.cursor()
        cur.execute(
            'INSERT INTO t_event (cameraID, eventTime, intensity, '
            'x1, y1, x2, y2, x3, y3, x4, y4, statusID) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) '
            'RETURNING internalID, eventID, eventTime',
            (camera_id,
             event_time,
             intensity * 1000,
             bezier[0]["x"],
             bezier[0]["y"],
             bezier[1]["x"],
             bezier[1]["y"],
             bezier[2]["x"],
             bezier[2]["y"],
             bezier[3]["x"],
             bezier[3]["y"],
             status_id))
        ids = cur.fetchone()
        event_internal_id = ids[0]
        event_id = uuid.UUID(bytes=ids[1])
        event = mp.Event(camera_id, ids[2], event_id, intensity, bezier)
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
        self.con.commit()
        return event


    def register_file(
            self,
            file_path,
            mime_type,
            namespace,
            semantic_type,
            file_time,
            file_metas,
            camera_id=get_installation_id()):
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
            raise ValueError('No status defined for this ID and time!')
        cur = self.con.cursor()
        cur.execute(
            'INSERT INTO t_file (cameraID, mimeType, namespace, '
            'semanticType, fileTime, fileSize, statusID) '
            'VALUES (?, ?, ?, ?, ?, ?, ?) '
            'RETURNING internalID, fileID, fileTime',
            (camera_id,
             mime_type,
             namespace,
             semantic_type,
             file_time,
             file_size_bytes,
             status_id))
        row = cur.fetchonemap()
        # Retrieve the internal ID of the file row to link fileMeta if required
        file_internal_id = row['internalID']
        # Retrieve the generated file ID, used to build the File object and to
        # name the source file
        file_id = uuid.UUID(bytes=row['fileID'])
        # Retrieve the file time as stored in the DB
        stored_file_time = row['fileTime']
        result_file = mp.FileRecord(camera_id, mime_type, namespace, semantic_type)
        result_file.file_time = stored_file_time
        result_file.file_id = file_id
        result_file.file_size = file_size_bytes
        # Store the fileMeta
        for file_meta_index, file_meta in enumerate(file_metas):
            cur.execute(
                'INSERT INTO t_fileMeta '
                '(fileID, namespace, key, stringValue, metaIndex) '
                'VALUES (?, ?, ?, ?, ?)',
                (file_internal_id,
                 file_meta.namespace,
                 file_meta.key,
                 file_meta.string_value,
                 file_meta_index))
            result_file.meta.append(
                mp.FileMeta(
                    file_meta.namespace,
                    file_meta.key,
                    file_meta.string_value))
        self.con.commit()
        # Move the original file from its path
        target_file_path = path.join(self.file_store_path, result_file.file_id.hex)
        shutil.move(file_path, target_file_path)
        # Return the resultant file object
        return result_file


    def get_file(self, file_id=None, internal_id=None):
        if file_id is None and internal_id is None:
            raise ValueError('Must specify either fileID or internalID!')
        cur = self.con.cursor()
        if internal_id is not None:
            cur.execute(
                'SELECT internalID, cameraID, mimeType, namespace, '
                'semanticType, fileTime, fileSize, fileID '
                'FROM t_file t WHERE t.internalID=(?)', (internal_id,))
        elif file_id is not None:
            cur.execute(
                'SELECT internalID, cameraID, mimeType, namespace, '
                'semanticType, fileTime, fileSize, fileID '
                'FROM t_file t WHERE t.fileID=(?)', (file_id.bytes,))
        row = cur.fetchonemap()
        if row is None:
            raise ValueError(
                'File with ID {0} or internal ID {1} not found!'.format(
                    file_id.hex,
                    internal_id))
        file_record = mp.FileRecord(row['cameraID'], row['mimeType'], row['namespace'], row['semanticType'])
        file_record.file_id = uuid.UUID(bytes=row['fileID'])
        file_record.file_size = row['fileSize']
        file_record.file_time = row['fileTime']
        internal_file_id = row['internalID']
        cur.execute(
            'SELECT namespace, key, stringValue '
            'FROM t_fileMeta t '
            'WHERE t.fileID = (?) '
            'ORDER BY metaIndex ASC',
            (internal_file_id,))
        for meta in cur.fetchallmap():
            file_record.meta.append(mp.FileMeta(meta['namespace'], meta['key'], meta['stringValue']))
        return file_record


    def get_cameras(self):
        """Get all Camera IDs for cameras in this database with current (i.e.
        validTo == None) status blocks."""
        cur = self.con.cursor()
        cur.execute(
            'SELECT DISTINCT cameraID from t_cameraStatus '
            'WHERE validTo IS NULL')
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
        high_water_mark = self.get_high_water_mark(camera_id=camera_id)
        if high_water_mark is not None and time < high_water_mark:
            # Establishing a status earlier than the current high water mark. This
            # means we need to set the high water mark back to the status validFrom
            # time, removing any computed products after this point.
            self.set_high_water_mark(time, camera_id)
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
            'orientationCertainty, locationLatitude, locationLongitude, '
            'locationGPS, lens, sensor, instURL, instName, locationCertainty) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) '
            'RETURNING internalID',
            (camera_id,
             time,
             None,
             SOFTWARE_VERSION,
             ns.orientation.altitude,
             ns.orientation.azimuth,
             ns.orientation.certainty,
             ns.location.latitude,
             ns.location.longitude,
             ns.location.gps,
             ns.lens,
             ns.sensor,
             ns.inst_url,
             ns.inst_name,
             ns.location.certainty))
        # Retrieve the newly created internal ID for the status block, use this to
        # insert visible regions
        status_id = cur.fetchone()[0]
        for region_index, region in enumerate(ns.regions):
            for point_index, point in enumerate(region):
                cur.execute(
                    'INSERT INTO t_visibleRegions (cameraStatusID, '
                    'region, pointOrder, x, y) VALUES (?,?,?,?,?)',
                    (status_id,
                     region_index,
                     point_index,
                     point['x'],
                     point['y']))
        self.con.commit()


    def _get_camera_status_id(
            self,
            time=None,
            camera_id=get_installation_id()):
        """Return the integer internal ID of the camera status block for the
        given time and camera, or None if there wasn't one."""
        if time is None:
            time = datetime.now()
        time = round_time(time)
        cur = self.con.cursor()
        cur.execute(
            'SELECT internalID from t_cameraStatus t '
            'WHERE t.cameraID = (?) AND t.validFrom <= (?) '
            'AND (t.validTo IS NULL OR t.validTo > (?))',
            (camera_id, time, time))
        row = cur.fetchone()
        if row is None:
            return None
        return row[0]


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
            'locationLongitude, locationGPS, locationCertainty, orientationAltitude, '
            'orientationAzimuth, orientationCertainty, validFrom, validTo, '
            'softwareVersion, internalID '
            'FROM t_cameraStatus t '
            'WHERE t.cameraID = (?) AND t.validFrom <= (?) '
            'AND (t.validTo IS NULL OR t.validTo > (?))',
            (camera_id,
             time,
             time))
        row = cur.fetchonemap()
        if row is None:
            return None
        cs = mp.CameraStatus(
            row['lens'], row['sensor'], row['instURL'], row['instName'], mp.Orientation(
                row['orientationAltitude'], row['orientationAzimuth'], row['orientationCertainty']), mp.Location(
                row['locationLatitude'], row['locationLongitude'], row['locationGPS'] == True,
                row['locationCertainty']))
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


    def set_high_water_mark(self, time, camera_id=get_installation_id()):
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
        cur = self.con.cursor()
        last = self.get_high_water_mark(camera_id)
        if last is None:
            # No high water mark defined, set it and return
            cur.execute(
                'INSERT INTO t_highWaterMark (cameraID, mark) VALUES (?,?)',
                (camera_id,
                 time))
        elif last < time:
            # Defined, but new one is later, we don't really have to do much
            cur.execute(
                'UPDATE t_highWaterMark t SET t.mark = (?) WHERE t.cameraID = (?)',
                (time,
                 camera_id))
        elif last > time:
            # More complicated, we're rolling back time so need to clean up a load
            # of future data
            cur.execute(
                'UPDATE t_highWaterMark t SET t.mark = (?) WHERE t.cameraID = (?)',
                (time,
                 camera_id))
            # First handle camera status, the visibility regions will be handled by
            # a CASCADE in the schema
            cur.execute(
                'DELETE FROM t_cameraStatus t '
                'WHERE t.validFrom > (?) AND t.cameraID = (?)',
                (time,
                 camera_id))
            cur.execute(
                'UPDATE t_cameraStatus t SET t.validTo = NULL '
                'WHERE t.validTo >= (?) AND t.cameraID = (?)',
                (time,
                 camera_id))
            # Delete files from the future
            cur.execute(
                'SELECT fileID FROM t_file t '
                'WHERE t.fileTime > (?) AND t.cameraID = (?)',
                (time, camera_id))
            for row in cur.fetchall():
                target_file_path = path.join(self.file_store_path, row[0])
                os.remove(target_file_path)
        self.con.commit()


    def clear_database(self):
        """
        Delete ALL THE THINGS!

        This doesn't reset any internal counters used to generate IDs
        but does otherwise remove all data from the database. Also
        purges all files from the fileStore
        """
        cur = self.con.cursor()
        cur.execute('DELETE FROM t_cameraStatus')
        cur.execute('DELETE FROM t_highWaterMark')
        cur.execute('DELETE FROM t_file')
        cur.execute('DELETE FROM t_fileMeta')
        cur.execute('DELETE FROM t_event')
        self.con.commit()
        shutil.rmtree(self.file_store_path)
        os.makedirs(self.file_store_path)


    def get_next_internal_id(self):
        """Retrieves and increments the internal ID from gidSequence, returning
        it as an integer."""
        self.con.begin()
        next_id = self.con.cursor().execute(
            'SELECT NEXT VALUE FOR gidSequence FROM RDB$DATABASE').fetchone()[0]
        self.con.commit()
        return next_id
