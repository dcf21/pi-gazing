#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# addObservatoryMaintenanceEvent.py
#
# -------------------------------------------------
# Copyright 2015-2021 Dominic Ford
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
This script is used to manually set up a "refresh" event for an observatory.
"""

import argparse
import time

from addObservatoryStatus import add_observatory_status
from pigazing_helpers.obsarchive import obsarchive_db
from pigazing_helpers.settings_read import settings, installation_info, known_observatories


def add_observatory_maintenance_event(metadata):
    db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                           db_host=installation_info['mysqlHost'],
                                           db_user=installation_info['mysqlUser'],
                                           db_password=installation_info['mysqlPassword'],
                                           db_name=installation_info['mysqlDatabase'],
                                           obstory_id=installation_info['observatoryId'])

    # Make sure that observatory exists in known_observatories list
    assert metadata['obstory_id'] in known_observatories

    db.register_obstory_metadata(obstory_id=metadata['obstory_id'],
                                 key="refresh",
                                 value=1,
                                 metadata_time=metadata['utc'],
                                 time_created=time.time(),
                                 user_created=metadata['username'])

    # Commit changes to database
    db.commit()

    # Make sure that all required fields are populated
    add_observatory_status(metadata)


if __name__ == "__main__":
    # Read input parameters
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observatory', dest='obstory_id', default=installation_info['observatoryId'],
                        help="ID of the observatory we are set the status for")
    parser.add_argument('--user', dest='username', default=settings['pigazingUser'],
                        help="Username of the user who is setting this status update")
    parser.add_argument('--utc', dest='utc', default=time.time(),
                        type=float,
                        help="Timestamp for status update")

    args = parser.parse_args()

    add_observatory_maintenance_event(metadata=vars(args))
