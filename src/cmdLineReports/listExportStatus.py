#!../../virtual-env/bin/python
# listExportStatus.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# Checks for missing files, duplicate publicIds, etc

import meteorpi_db
import mod_settings

db = meteorpi_db.MeteorDatabase(mod_settings.settings['dbFilestore'])
sql = db.con

sql.execute("SELECT * FROM archive_exportConfig;")
export_configs = sql.fetchall()

for config in export_configs:
    print "\n%s\n%s\n\n" % (config['exportName'], "-" * len(config['exportName']))

    if (config['active']):
        print "  * Active"
    else:
        print "  * Disabled"
    n_total = n_pending = -1
    if (config['exportType'] == "metadata"):
        sql.execute("SELECT COUNT(*) FROM archive_metadataExport;")
        n_total = sql.fetchall()[0]['COUNT(*)']
        sql.execute("SELECT COUNT(*) FROM archive_metadataExport WHERE exportState>0;")
        n_pending = sql.fetchall()[0]['COUNT(*)']
    elif (config['exportType'] == "observation"):
        sql.execute("SELECT COUNT(*) FROM archive_observationExport;")
        n_total = sql.fetchall()[0]['COUNT(*)']
        sql.execute("SELECT COUNT(*) FROM archive_observationExport WHERE exportState>0;")
        n_pending = sql.fetchall()[0]['COUNT(*)']
    elif (config['exportType'] == "file"):
        sql.execute("SELECT COUNT(*) FROM archive_fileExport;")
        n_total = sql.fetchall()[0]['COUNT(*)']
        sql.execute("SELECT COUNT(*) FROM archive_fileExport WHERE exportState>0;")
        n_pending = sql.fetchall()[0]['COUNT(*)']
    print "  * %9d jobs in export table" % n_total
    print "  * %9d jobs still to be done" % n_pending
