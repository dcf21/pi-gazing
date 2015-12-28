#!../../virtual-env/bin/python
# exportData.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# This exports observations to remote servers, if configured

import sys
from math import *

import meteorpi_db
from meteorpi_db.exporter import MeteorExporter

import mod_log
from mod_log import logTxt
from mod_settings import *
from mod_time import *


def export_data(utcNow, utcMustStop=0):
    logTxt("Starting export of images and events")

    # Work out how long we can do exporting for
    state = None
    tStop = time.time() + (utcMustStop - utcNow)

    # Open a database handle
    db_handle = meteorpi_db.MeteorDatabase(DBPATH, DBFILESTORE)

    # Search for items which need exporting
    for export_config in db_handle.get_export_configurations():
        if export_config.enabled:
            db_handle.mark_entities_to_export(export_config)

    # Create an exporter instance
    exporter = MeteorExporter(db=db_handle,
                              mark_interval_seconds=1,
                              max_failures_before_disable=4,
                              defer_on_failure_seconds=3)

    # Loop until either we run out of time, or we run out of files to export
    while (not utcMustStop) or (time.time() < tStop):
        state = exporter.handle_next_export()
        if not state:
            logTxt("Finished export of images and events")
            break
        print "Export status: %s" % state.state
        if state.state == "failed":
            logTxt("Backing off, because an export failed")
            time.sleep(300)

    # Exit
    return state


# If we're called as a script, run the method exportData()
if __name__ == "__main__":
    utcNow = time.time()
    if len(sys.argv) > 1:
        utcNow = float(sys.argv[1])
    mod_log.setUTCoffset(utcNow - time.time())
    export_data(utcNow, 0)
