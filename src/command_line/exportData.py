#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# exportData.py
#
# -------------------------------------------------
# Copyright 2015-2020 Dominic Ford
#
# This file is part of Pi Gazing.
#
# Pi Gazing is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pi Gazing is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Pi Gazing.  If not, see <http://www.gnu.org/licenses/>.
# -------------------------------------------------

"""
This exports observations to remote servers, if configured.
"""

import argparse
import logging
import os
import time
import warnings

from pigazing_helpers.obsarchive import obsarchive_db
from pigazing_helpers.obsarchive.exporter import ObservationExporter
from pigazing_helpers.settings_read import settings, installation_info
from urllib3.exceptions import InsecureRequestWarning

# Don't spam the terminal with endless warnings about self-signed https certificates
warnings.filterwarnings("ignore", category=InsecureRequestWarning)


def export_data(db, utc_must_stop=None):
    logging.info("Starting export of images and events")

    # Search for items which need exporting, and add export tasks for them
    for export_config in db.get_export_configurations():
        if export_config.enabled:
            db.mark_entities_to_export(export_config)
    db.commit()

    # Create an exporter instance
    exporter = ObservationExporter(db=db)

    # If an export fails, we delay a short time before trying again. Successive failures lead to longer delays.
    back_off_delays = (30, 300, 600, 1200, 2400)
    fail_count = 0

    # Loop over export tasks
    while (utc_must_stop is None) or (time.time() < utc_must_stop):
        # If we've had too many failures, it's time to give up
        if fail_count >= len(back_off_delays):
            logging.info("Exceeded maximum allowed number of failures: giving up.")
            return

        # Attempt to do an export task
        state = exporter.handle_next_export()
        db.commit()

        # If we didn't find a task to do, that means we've finished
        if not state:
            logging.info("Finished export of images and events")
            return

        # Report status to user
        logging.info("Export of ID {}: {}".format(state.entity_id, state.state))

        # If we failed, them sleep for a short time
        if state.state == "failed":
            logging.info("Backing off, because an export failed")
            delay = back_off_delays[fail_count]
            if (utc_must_stop is not None) and (time.time() > utc_must_stop - delay):
                return
            time.sleep(back_off_delays[fail_count])
            fail_count += 1
        else:
            fail_count = 0


# If we're called as a script, run the method exportData()
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stop-by', default=None, type=float,
                        dest='stop_utc', help='Specify a unix time by which we need to exit')
    args = parser.parse_args()

    _db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                            db_host=installation_info['mysqlHost'],
                                            db_user=installation_info['mysqlUser'],
                                            db_password=installation_info['mysqlPassword'],
                                            db_name=installation_info['mysqlDatabase'],
                                            obstory_id=installation_info['observatoryId']
                                            )

    # Set up logging
    logging.basicConfig(level=logging.INFO,
                        format='[%(asctime)s] %(levelname)s:%(filename)s:%(message)s',
                        datefmt='%d/%m/%Y %H:%M:%S',
                        handlers=[
                            logging.FileHandler(os.path.join(settings['pythonPath'], "../datadir/pigazing.log")),
                            logging.StreamHandler()
                        ])
    logger = logging.getLogger(__name__)
    logger.info(__doc__.strip())

    export_data(db=_db,
                utc_must_stop=args.stop_utc
                )
