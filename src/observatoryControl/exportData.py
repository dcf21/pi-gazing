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
from mod_log import log_txt, get_utc
import mod_settings


def export_data(db, utc_now, utc_must_stop=0):
    log_txt("Starting export of images and events")

    # Work out how long we can do exporting for
    utc_stop = get_utc() + (utc_must_stop - utc_now)

    # Search for items which need exporting
    for export_config in db.get_export_configurations():
        if export_config.enabled:
            db.mark_entities_to_export(export_config)
    db.commit()

    # Create an exporter instance
    exporter = MeteorExporter(db=db)

    # Loop until either we run out of time, or we run out of files to export
    max_failures = 5
    fail_count = 0
    while ((not utc_must_stop) or (time.time() < utc_stop)) and (fail_count < max_failures):
        state = exporter.handle_next_export()
        db.commit()
        if not state:
            log_txt("Finished export of images and events")
            break
        print "Export status: %s" % state.state
        if state.state == "failed":
            log_txt("Backing off, because an export failed")
            time.sleep(600)
            fail_count += 1

    # Exit
    if fail_count >= max_failures:
        log_txt("Exceeded maximum allowed number of failures: giving up.")


# If we're called as a script, run the method exportData()
if __name__ == "__main__":
    _utc_now = time.time()
    if len(sys.argv) > 1:
        _utc_now = float(sys.argv[1])
    mod_log.set_utc_offset(_utc_now - time.time())
    _db = meteorpi_db.MeteorDatabase(mod_settings.settings['dbFilestore'])
    export_data(db=_db,
                utc_now=_utc_now,
                utc_must_stop=0)
