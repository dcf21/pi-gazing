import fdb
import meteorpi_model as mp
from uuid import getnode as get_mac
		
# http://www.firebirdsql.org/file/documentation/drivers_documentation/python/fdb/getting-started.html is helpful!

con = fdb.connect(dsn='/var/lib/firebird/2.5/data/meteorpi.fdb', user='meteorpi', password='meteorpi')

def getCameras():
	cur = con.cursor()
	cur.execute('SELECT DISTINCT cameraID from t_cameraStatus where validTo IS NULL')
	for fieldDesc in cur.description:
    		print fieldDesc[fdb.DESCRIPTION_NAME].ljust(fieldDesc[fdb.DESCRIPTION_DISPLAY_SIZE]) ,
		print # Finish the header with a newline.
		print '-' * 78
	fieldIndices = range(len(cur.description))
	for row in cur:
    		for fieldIndex in fieldIndices:
        		fieldValue = str(row[fieldIndex])
        		fieldMaxWidth = cur.description[fieldIndex][fdb.DESCRIPTION_DISPLAY_SIZE]
			print fieldValue.ljust(fieldMaxWidth) ,
    		print # Finish the row with a newline.

def getInstallationId():
	mac = get_mac()
	return mac
