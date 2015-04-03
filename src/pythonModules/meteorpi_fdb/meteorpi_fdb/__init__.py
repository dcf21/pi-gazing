import fdb
import uuid
import meteorpi_model as mp
from datetime import datetime, timedelta

# http://www.firebirdsql.org/file/documentation/drivers_documentation/python/fdb/getting-started.html
# is helpful!

con = fdb.connect(
    dsn='/var/lib/firebird/2.5/data/meteorpi.fdb',
    user='meteorpi',
    password='meteorpi')


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


def getCameras():
    """Get all Camera IDs for cameras in this database with current (i.e.
    validTo == None) status blocks."""
    cur = con.cursor()
    cur.execute(
        'SELECT DISTINCT cameraID from t_cameraStatus '
        'WHERE validTo IS NULL')
    return map(lambda row: row[0], cur.fetchall())


def updateCameraStatus(ns, time=datetime.now()):
    """Update the status for this installation's camera, optionally specify a
    time (defaults to datetime.now())."""
    time = roundTime(time)
    cameraID = getInstallationID()
    highWaterMark = getHighWaterMark(cameraID)
    if highWaterMark is not None and time < highWaterMark:
        # Establishing a status earlier than the current high water mark. This
        # means we need to set the high water mark back to the status validFrom
        # time, removing any computed products after this point.
        setHighWaterMark(time, cameraID)
    cur = con.cursor()
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
        'locationGPS, lens, camera, instURL, instName) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) '
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
         ns.camera,
         ns.instURL,
         ns.instName))
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
    con.commit()


def getCameraStatus(time=datetime.now()):
    """Return the camera status for a given time, or None if no status is
    available time : datetime.datetime object, default now."""
    time = roundTime(time)
    cur = con.cursor()
    cameraID = getInstallationID()
    cur.execute(
        'SELECT lens, camera, instURL, instName, locationLatitude, '
        'locationLongitude, locationGPS, orientationAltitude, '
        'orientationAzimuth, orientationCertainty, validFrom, validTo, '
        'softwareVersion, internalID '
        'FROM t_cameraStatus t '
        'WHERE t.cameraID = (?) AND t.validFrom <= (?) '
        'AND (t.validTo IS NULL OR t.validTo>(?))',
        (cameraID,
         time,
         time))
    row = cur.fetchone()
    if row is None:
        return None
    cs = mp.CameraStatus(
        row[0], row[1], row[2], row[3], mp.Orientation(
            row[7], row[8], row[9]), mp.Location(
            row[4], row[5], row[6] == True))
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
        cs.regions[point["region"]].append({"x": point["x"], "y": point["y"]})
    return cs


def getHighWaterMark(cameraID=getInstallationID()):
    """Retrieves the current high water mark for a camera installation, or None
    if none has been set."""
    cur = con.cursor()
    cur.execute(
        'SELECT mark FROM t_highWaterMark t WHERE t.cameraID = (?)',
        [cameraID])
    row = cur.fetchone()
    if row is None:
        return None
    return row[0]


def setHighWaterMark(time, cameraID=getInstallationID()):
    """
    Sets the 'high water mark' for this installation.

    This is the latest point before which all data has been processed,
    when this call is made any data products (events, images etc) with
    time stamps later than the high water mark will be removed from the
    database. Any camera status blocks with validFrom dates after the
    high water mark will be removed, and any status blocks with validTo
    dates after the high water mark will have their validTo set to None
    to make them current
    """
    cur = con.cursor()
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
    else:
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
        # TODO events and images
    con.commit()


def clearDatabase():
    """
    Delete ALL THE THINGS!

    This doesn't reset any internal counters used to generate IDs but
    does otherwise remove all data from the database.
    """
    cur = con.cursor()
    cur.execute('DELETE FROM t_cameraStatus')
    cur.execute('DELETE FROM t_highWaterMark')
    cur.execute('DELETE FROM t_file')
    cur.execute('DELETE FROM t_fileMeta')
    cur.execute('DELETE FROM t_event')
    con.commit()


def roundTime(time=datetime.now()):
    """
    Rounds a datetime, discarding the millisecond part.

    Needed because Python and Firebird precision is different!
    """
    return time + timedelta(0, 0, -time.microsecond)


def getNextInternalID():
    """Retrieves and increments the internal ID from gidSequence, returning it
    as an integer."""
    con.begin()
    nextID = con.cursor().execute(
        'SELECT NEXT VALUE FOR gidSequence FROM RDB$DATABASE').fetchone()[0]
    con.commit()
    return nextID


def printResultSet(cur):
    """Debug method to print the results from a cursor as a table."""
    con.begin()
    fieldIndices = range(len(cur.description))
    for row in cur:
        for fieldIndex in fieldIndices:
            fieldValue = str(row[fieldIndex])
            fieldMaxWidth = cur.description[fieldIndex][
                fdb.DESCRIPTION_DISPLAY_SIZE]
            print fieldValue.ljust(fieldMaxWidth),
        print  # Finish the row with a newline.
