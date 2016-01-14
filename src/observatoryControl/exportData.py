#!../../virtual-env/bin/python
# exportData.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# This exports observations to remote servers, if configured

import sys
import time

import meteorpi_db
from meteorpi_db.exporter import MeteorExporter

import mod_log
from mod_log import log_txt
import mod_settings


def export_data(utc_now, utc_must_stop=0):
    log_txt("Starting export of images and events")

    # Work out how long we can do exporting for
    state = None
    utc_stop = time.time() + (utc_must_stop - utc_now)

    # Open a database handle
    db = meteorpi_db.MeteorDatabase(mod_settings.settings['dbFilestore'])

    # Search for items which need exporting
    for export_config in db.get_export_configurations():
        if export_config.enabled:
            db.mark_entities_to_export(export_config)

    # Create an exporter instance
    exporter = MeteorExporter(db=db)

    # Loop until either we run out of time, or we run out of files to export
    while (not utc_must_stop) or (time.time() < utc_stop):
        state = exporter.handle_next_export()
        if not state:
            log_txt("Finished export of images and events")
            break
        print "Export status: %s" % state.state
        if state.state == "failed":
            log_txt("Backing off, because an export failed")
            time.sleep(300)

    # Exit
    return state


# If we're called as a script, run the method exportData()
if __name__ == "__main__":
    _utc_now = time.time()
    if len(sys.argv) > 1:
        _utc_now = float(sys.argv[1])
    mod_log.set_utc_offset(_utc_now - time.time())
    export_data(_utc_now, 0)
