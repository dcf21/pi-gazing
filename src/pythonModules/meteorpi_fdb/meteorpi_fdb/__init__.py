import fdb
import uuid
import meteorpi_model as mp
from datetime import datetime, timedelta
import os.path as path
import os
import shutil
import uuid

# http://www.firebirdsql.org/file/documentation/drivers_documentation/python/fdb/getting-started.html
# is helpful!


def getInstallationID():
    """Get the installation ID of the current system, using the MAC address
    rendered as a 12 character hex string."""
    def toArray(number):
        result = ''
        n = number
        while (n > 0):
            (div, mod) = divmod(n, 256)
            n = (n - mod) / 256
            result = ('%0.2x' % mod) + result
        return result
    return toArray(uuid.getnode())


def roundTime(time=datetime.now()):
    """
    Rounds a datetime, discarding the millisecond part.

    Needed because Python and Firebird precision is different!
    """
    return time + timedelta(0, 0, -time.microsecond)


class MeteorDatabase:

    """Class representing a single MeteorPi relational database and file
    store."""

    def __init__(
            self,
            dbPath='localhost:/var/lib/firebird/2.5/data/meteorpi.fdb',
            fileStorePath=path.expanduser("~/meteorpi_files")):
        self.con = fdb.connect(
            dsn=dbPath,
            user='meteorpi',
            password='meteorpi')
        self.dbPath = dbPath
        if path.exists(fileStorePath) == False:
            os.makedirs(fileStorePath)
        if path.isdir(fileStorePath) == False:
            raise ValueError(
                'File store path already exists but is not a directory!')
        self.fileStorePath = fileStorePath

    def __str__(self):
        return 'MeteorDatabase(db={0}, fileStorePath={1}'.format(
            self.dbPath,
            self.fileStorePath)

    def getEvents(self, eventID=None, internalIDs=None, cursor=None):
        """Retrieve Events by an eventID, set of internalIDs or by a cursor
        which should contain a result set of rows from t_event."""
        if eventID is None and internalIDs is None and cursor is None:
            raise ValueError(
                'Must specify one of eventID, internalIDs or cursor!')
        # If we have a cursor use it, otherwise get one.
        if (cursor is None):
            _cur = self.con.cursor()
            if eventID is not None:
                # Use event ID
                _cur.execute(
                    'SELECT cameraID, eventID, internalID, eventTime, '
                    'intensity, x1, y1, x2, y2, x3, y3, x4, y4 '
                    'FROM t_event '
                    'WHERE eventID = (?)', (eventID.bytes,))
            else:
                _cur.execute(
                    'SELECT cameraID, eventID, internalID, eventTime, '
                    'intensity, x1, y1, x2, y2, x3, y3, x4, y4 '
                    'FROM t_event '
                    'WHERE internalID IN (?)', (internalIDs,))
        else:
            _cur = cursor
        events = {}
        for row in _cur.fetchallmap():
            internalID = row['internalID']
            events[str(internalID)] = mp.Event(
                row['cameraID'],
                row['eventTime'],
                uuid.UUID(bytes=row['eventID']),
                row['intensity'] / 1000.0,
                mp.Bezier(row['x1'], row['y1'], row['x2'], row['y2'],
                          row['x3'], row['y3'], row['x4'], row['y4']),
                [])
        result = []
        for internalID, event in events.iteritems():
            _cur.execute(
                'SELECT fileID from t_event_to_file '
                'WHERE eventID = (?) '
                'ORDER BY sequenceNumber ASC', (internalID,))
            for row in _cur.fetchall():
                event.fileRecords.append(self.getFile(internalID=row[0]))
            result.append(event)
        return result

    def registerEvent(
            self,
            cameraID,
            eventTime,
            intensity,
            bezier,
            fileRecords=[]):
        """Register a new row in t_event, returning the Event object."""
        if intensity > 1.0:
            raise ValueError('Intensity must be at most 1.0')
        if intensity < 0:
            raise ValueError('Intensity must not be negative')
        statusID = self._getCameraStatusID(cameraID=cameraID, time=eventTime)
        if statusID is None:
            raise ValueError('No status defined for this ID and time!')
        cur = self.con.cursor()
        cur.execute(
            'INSERT INTO t_event (cameraID, eventTime, intensity, '
            'x1, y1, x2, y2, x3, y3, x4, y4, statusID) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) '
            'RETURNING internalID, eventID, eventTime',
            (cameraID,
             eventTime,
             intensity * 1000,
             bezier[0]["x"],
             bezier[0]["y"],
             bezier[1]["x"],
             bezier[1]["y"],
             bezier[2]["x"],
             bezier[2]["y"],
             bezier[3]["x"],
             bezier[3]["y"],
             statusID))
        ids = cur.fetchone()
        eventInternalID = ids[0]
        eventID = uuid.UUID(bytes=ids[1])
        event = mp.Event(cameraID, ids[2], eventID, intensity, bezier)
        for fileRecordIndex, fileRecord in enumerate(fileRecords):
            event.fileRecords.append(fileRecord)
            cur.execute(
                'SELECT internalID FROM t_file WHERE fileID = (?)',
                (fileRecord.fileID.bytes,
                 ))
            fileInternalID = cur.fetchone()[0]
            cur.execute(
                'INSERT INTO t_event_to_file '
                '(fileID, eventID, sequenceNumber) '
                'VALUES (?, ?, ?)',
                (fileInternalID,
                 eventInternalID,
                 fileRecordIndex))
        self.con.commit()
        return event

    def registerFile(
            self,
            filePath,
            mimeType,
            namespace,
            semanticType,
            fileTime,
            fileMetas,
            cameraID=getInstallationID()):
        """
        Register a new row in t_file representing a file on disk.

        At the same time once the transaction has committed, move the
        file at the specified path to the local store. Returns the
        FileRecord object produced.
        """
        # Check the file exists, and retrieve its size
        if path.exists(filePath) == False:
            raise ValueError('No file exists at {0}'.format(filePath))
        fileSizeBytes = os.stat(filePath).st_size
        # Handle the database parts
        statusID = self._getCameraStatusID(cameraID=cameraID, time=fileTime)
        if statusID is None:
            raise ValueError('No status defined for this ID and time!')
        cur = self.con.cursor()
        cur.execute(
            'INSERT INTO t_file (cameraID, mimeType, namespace, '
            'semanticType, fileTime, fileSize, statusID) '
            'VALUES (?, ?, ?, ?, ?, ?, ?) '
            'RETURNING internalID, fileID, fileTime',
            (cameraID,
             mimeType,
             namespace,
             semanticType,
             fileTime,
             fileSizeBytes,
             statusID))
        resultRow = cur.fetchone()
        # Retrieve the internal ID of the file row to link fileMeta if required
        fileInternalID = resultRow[0]
        # Retrieve the generated file ID, used to build the File object and to
        # name the source file
        fileID = uuid.UUID(bytes=resultRow[1])
        # Retrieve the file time as stored in the DB
        storedFileTime = resultRow[2]
        resultFile = mp.FileRecord(cameraID, mimeType, namespace, semanticType)
        resultFile.fileTime = storedFileTime
        resultFile.fileID = fileID
        resultFile.fileSize = fileSizeBytes
        # Store the fileMeta
        for fileMetaIndex, fileMeta in enumerate(fileMetas):
            cur.execute(
                'INSERT INTO t_fileMeta '
                '(fileID, namespace, key, stringValue, metaIndex) '
                'VALUES (?, ?, ?, ?, ?)',
                (fileInternalID,
                 fileMeta.namespace,
                 fileMeta.key,
                 fileMeta.stringValue,
                 fileMetaIndex))
            resultFile.meta.append(
                mp.FileMeta(
                    fileMeta.namespace,
                    fileMeta.key,
                    fileMeta.stringValue))
        self.con.commit()
        # Move the original file from its path
        targetFilePath = path.join(self.fileStorePath, resultFile.fileID.hex)
        shutil.move(filePath, targetFilePath)
        # Return the resultant file object
        return resultFile

    def getFile(self, fileID=None, internalID=None):
        if (fileID is None and internalID is None):
            raise ValueError('Must specify either fileID or internalID!')
        cur = self.con.cursor()
        if (internalID is not None):
            cur.execute(
                'SELECT internalID, cameraID, mimeType, namespace, '
                'semanticType, fileTime, fileSize, fileID '
                'FROM t_file t WHERE t.internalID=(?)', (internalID,))
        elif (fileID is not None):
            cur.execute(
                'SELECT internalID, cameraID, mimeType, namespace, '
                'semanticType, fileTime, fileSize, fileID '
                'FROM t_file t WHERE t.fileID=(?)', (fileID.bytes,))
        row = cur.fetchone()
        if row is None:
            raise ValueError(
                'File with ID {0} or internal ID {1} not found!'.format(
                    fileID.hex,
                    internalID))
        fileRecord = mp.FileRecord(row[1], row[2], row[3], row[4])
        fileRecord.fileID = uuid.UUID(bytes=row[7])
        fileRecord.fileSize = row[6]
        fileRecord.fileTime = row[5]
        internalFileID = row[0]
        cur.execute(
            'SELECT namespace, key, stringValue '
            'FROM t_fileMeta t '
            'WHERE t.fileID = (?) '
            'ORDER BY metaIndex ASC',
            (internalFileID,))
        for meta in cur.fetchall():
            fileRecord.meta.append(mp.FileMeta(meta[0], meta[1], meta[2]))
        return fileRecord

    def getCameras(self):
        """Get all Camera IDs for cameras in this database with current (i.e.
        validTo == None) status blocks."""
        cur = self.con.cursor()
        cur.execute(
            'SELECT DISTINCT cameraID from t_cameraStatus '
            'WHERE validTo IS NULL')
        return map(lambda row: row[0], cur.fetchall())

    def updateCameraStatus(self, ns, time=datetime.now()):
        """
        Update the status for this installation's camera, optionally specify a
        time (defaults to datetime.now()).

        If the time is earlier than the current high water mark for this
        camera any data products derived after that time will be deleted
        as if setHighWaterMark was called.
        """
        time = roundTime(time)
        cameraID = getInstallationID()
        highWaterMark = self.getHighWaterMark(cameraID)
        if highWaterMark is not None and time < highWaterMark:
            # Establishing a status earlier than the current high water mark. This
            # means we need to set the high water mark back to the status validFrom
            # time, removing any computed products after this point.
            setHighWaterMark(time, cameraID)
        cur = self.con.cursor()
        # If there's an existing status block then set its end time to now
        cur.execute(
            'UPDATE t_cameraStatus t SET t.validTo = (?) '
            'WHERE t.validTo IS NULL AND t.cameraID = (?)',
            (time,
             cameraID))
        # Insert the new status into the database
        cur.execute(
            'INSERT INTO t_cameraStatus (cameraID, validFrom, validTo, '
            'softwareVersion, orientationAltitude, orientationAzimuth, '
            'orientationCertainty, locationLatitude, locationLongitude, '
            'locationGPS, lens, sensor, instURL, instName, locationCertainty) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) '
            'RETURNING internalID',
            (cameraID,
             time,
             None,
             1,
             ns.orientation.altitude,
             ns.orientation.azimuth,
             ns.orientation.certainty,
             ns.location.latitude,
             ns.location.longitude,
             ns.location.gps,
             ns.lens,
             ns.sensor,
             ns.instURL,
             ns.instName,
             ns.location.certainty))
        # Retrieve the newly created internal ID for the status block, use this to
        # insert visible regions
        statusID = cur.fetchone()[0]
        for regionIndex, region in enumerate(ns.regions):
            for pointIndex, point in enumerate(region):
                cur.execute(
                    'INSERT INTO t_visibleRegions (cameraStatusID, '
                    'region, pointOrder, x, y) VALUES (?,?,?,?,?)',
                    (statusID,
                     regionIndex,
                     pointIndex,
                     point["x"],
                     point["y"]))
        self.con.commit()

    def _getCameraStatusID(
            self,
            time=datetime.now(),
            cameraID=getInstallationID()):
        """Return the integer internal ID of the camera status block for the
        given time and camera, or None if there wasn't one."""
        time = roundTime(time)
        cur = self.con.cursor()
        cur.execute(
            'SELECT internalID from t_cameraStatus t '
            'WHERE t.cameraID = (?) AND t.validFrom <= (?) '
            'AND (t.validTo IS NULL OR t.validTo > (?))',
            (cameraID, time, time))
        row = cur.fetchone()
        if row is None:
            return None
        return row[0]

    def getCameraStatus(
            self,
            time=datetime.now(),
            cameraID=getInstallationID()):
        """Return the camera status for a given time, or None if no status is
        available time : datetime.datetime object, default now."""
        time = roundTime(time)
        cur = self.con.cursor()
        cur.execute(
            'SELECT lens, sensor, instURL, instName, locationLatitude, '
            'locationLongitude, locationGPS, orientationAltitude, '
            'orientationAzimuth, orientationCertainty, validFrom, validTo, '
            'softwareVersion, internalID, locationCertainty '
            'FROM t_cameraStatus t '
            'WHERE t.cameraID = (?) AND t.validFrom <= (?) '
            'AND (t.validTo IS NULL OR t.validTo > (?))',
            (cameraID,
             time,
             time))
        row = cur.fetchone()
        if row is None:
            return None
        cs = mp.CameraStatus(
            row[0], row[1], row[2], row[3], mp.Orientation(
                row[7], row[8], row[9]), mp.Location(
                row[4], row[5], row[6] == True, row[14]))
        cs.validFrom = row[10]
        cs.validTo = row[11]
        cs.softwareVersion = row[12]
        cameraStatusID = row[13]
        cur.execute('SELECT region, pointOrder, x, y FROM t_visibleRegions t '
                    'WHERE t.cameraStatusID = (?) '
                    'ORDER BY region ASC, pointOrder ASC', [cameraStatusID])
        for point in cur.fetchallmap():
            if len(cs.regions) <= point["region"]:
                cs.regions.append([])
            cs.regions[point["region"]].append(
                {"x": point["x"], "y": point["y"]})
        return cs

    def getHighWaterMark(self, cameraID=getInstallationID()):
        """Retrieves the current high water mark for a camera installation, or
        None if none has been set."""
        cur = self.con.cursor()
        cur.execute(
            'SELECT mark FROM t_highWaterMark t WHERE t.cameraID = (?)',
            [cameraID])
        row = cur.fetchone()
        if row is None:
            return None
        return row[0]

    def setHighWaterMark(self, time, cameraID=getInstallationID()):
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
        last = getHighWaterMark(cameraID)
        if last is None:
            # No high water mark defined, set it and return
            cur.execute(
                'INSERT INTO t_highWaterMark (cameraID, mark) VALUES (?,?)',
                (cameraID,
                 time))
        elif last < time:
            # Defined, but new one is later, we don't really have to do much
            cur.execute(
                'UPDATE t_highWaterMark t SET t.mark = (?) WHERE t.cameraID = (?)',
                (time,
                 cameraID))
        elif last > time:
            # More complicated, we're rolling back time so need to clean up a load
            # of future data
            cur.execute(
                'UPDATE t_highWaterMark t SET t.mark = (?) WHERE t.cameraID = (?)',
                (time,
                 cameraID))
            # First handle camera status, the visibility regions will be handled by
            # a CASCADE in the schema
            cur.execute(
                'DELETE FROM t_cameraStatus t '
                'WHERE t.validFrom > (?) AND t.cameraID = (?)',
                (time,
                 cameraID))
            cur.execute(
                'UPDATE t_cameraStatus t SET t.validTo = NULL '
                'WHERE t.validTo >= (?) AND t.cameraID = (?)',
                (time,
                 cameraID))
            # Delete files from the future
            cur.execute(
                'SELECT fileID FROM t_file t '
                'WHERE t.fileTime > (?) AND t.cameraID = (?)',
                (time, cameraID))
            for row in cur.fetchAll():
                targetFilePath = path.join(fileStorePath, row[0])
                os.remove(targetFilePath)
        self.con.commit()

    def clearDatabase(self):
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
        shutil.rmtree(self.fileStorePath)
        os.makedirs(self.fileStorePath)

    def getNextInternalID(self):
        """Retrieves and increments the internal ID from gidSequence, returning
        it as an integer."""
        self.con.begin()
        nextID = self.con.cursor().execute(
            'SELECT NEXT VALUE FOR gidSequence FROM RDB$DATABASE').fetchone()[0]
        self.con.commit()
        return nextID
