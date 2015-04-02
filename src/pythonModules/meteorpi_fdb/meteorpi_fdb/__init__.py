import fdb
import uuid
import meteorpi_model as mp
from datetime import datetime
		
# http://www.firebirdsql.org/file/documentation/drivers_documentation/python/fdb/getting-started.html is helpful!

con = fdb.connect(dsn='/var/lib/firebird/2.5/data/meteorpi.fdb', user='meteorpi', password='meteorpi')

# Return a sequence of Camera IDs for all cameras with current status blocks
def getCameras():
	con.begin()
	cur = con.cursor()
	cur.execute('SELECT DISTINCT cameraID from t_cameraStatus where validTo IS NULL')
	return map(lambda row: row[0], cur.fetchall())

# Update the camera status for the installed camera, taking its ID from getInstallationID()
def updateCameraStatus(ns):
	trans = con.trans()
	timeNow = datetime.now()
	cameraID = getInstallationID()
	cur = trans.cursor()
	# If there's an existing status block then set its end time to now
	cur.execute('UPDATE t_cameraStatus t SET t.validTo = (?) WHERE t.validTo IS NULL AND t.cameraID = (?)', (timeNow, cameraID))
	cur.execute('INSERT INTO t_cameraStatus (internalId, cameraID, validFrom, validTo, softwareVersion, orientationAltitude, orientationAzimuth, orientationCertainty, locationLatitude, locationLongitude, locationGPS, lens, camera, instURL, instName) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING internalID', (0, cameraID, timeNow, None, 1, ns.orientation.altitude, ns.orientation.azimuth, ns.orientation.certainty, ns.location.latitude, ns.location.longitude, ns.location.gps, ns.lens, ns.camera, ns.instURL, ns.instName))
	print 'Newly created row with ID = ', cur.fetchone()[0]
	trans.commit()
	print 'Updated camera status'

def getCameraStatus(time = datetime.now()):
	trans = con.trans()
	cur = trans.cursor()
	cameraID = getInstallationID()
	cur.execute('SELECT lens, camera, instURL, instName, locationLatitude, locationLongitude, locationGPS, orientationAltitude, orientationAzimuth, orientationCertainty, validFrom, validTo, softwareVersion FROM t_cameraStatus t WHERE t.cameraID = (?) AND t.validFrom <= (?) AND t.validTo IS NULL', ( cameraID,  time))
	row = cur.fetchone()
	print row
	cs = mp.CameraStatus(row[0], row[1], row[2], row[3], mp.Orientation(row[7], row[8], row[9]), mp.Location(row[4], row[5], row[6]==True))
	cs.validFrom = row[10]
	cs.validTo = row[11]
	cs.softwareVersion = row[12]
	return cs;
	

# Get a 48 bit integer from the MAC address of the first network interface on this machine, render as a 12 character hex string
def getInstallationID():
	def toArray(number):
		result = ''
		n = number
		while (n > 0):
			(div, mod) = divmod(n, 256)
			n = (n - mod) / 256
			result = ('%0.2x' % mod) + result
		return result
	return toArray(uuid.getnode())

# -----------------------------------------
# DATABASE UTILITY METHODS BELOW THIS POINT
# -----------------------------------------

# Retrieves and increments the internal ID from gidSequence, returning it as an integer
def getNextInternalID():
	con.begin()
	nextID = con.cursor().execute('SELECT NEXT VALUE FOR gidSequence FROM RDB$DATABASE').fetchone()[0]
	con.commit()
	return nextID

# Debug method to print the results from a cursor as a table
def printResultSet(cur):
	con.begin()
	fieldIndices = range(len(cur.description))
	for row in cur:
    		for fieldIndex in fieldIndices:
        		fieldValue = str(row[fieldIndex])
        		fieldMaxWidth = cur.description[fieldIndex][fdb.DESCRIPTION_DISPLAY_SIZE]
			print fieldValue.ljust(fieldMaxWidth) ,
    		print # Finish the row with a newline.
