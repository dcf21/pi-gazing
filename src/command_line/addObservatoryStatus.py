#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# addObservatoryStatus.py
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
This script is used to manually set up metadata about an observatory in the database.
"""

import argparse
import os
import time

from pigazing_helpers import hardware_properties
from pigazing_helpers.obsarchive import obsarchive_db
from pigazing_helpers.settings_read import settings, installation_info, known_observatories


def add_observatory_status(metadata):
    db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                           db_host=installation_info['mysqlHost'],
                                           db_user=installation_info['mysqlUser'],
                                           db_password=installation_info['mysqlPassword'],
                                           db_name=installation_info['mysqlDatabase'],
                                           obstory_id=installation_info['observatoryId'])

    # Make sure that observatory exists in known_observatories list
    assert metadata['obstory_id'] in known_observatories

    hw = hardware_properties.HardwareProps(
        path=os.path.join(settings['pythonPath'], "..", "configuration_global", "camera_properties")
    )

    obstory_id_list = db.get_obstory_ids()

    metadata_existing = {}

    # If observatory already exists, get existing metadata fields
    if metadata['obstory_id'] in obstory_id_list:
        metadata_existing = db.get_obstory_status(obstory_id=metadata['obstory_id'], time=metadata['utc'])

    metadata = {**metadata_existing, **metadata}

    # If input parameters have not been supplied, read the defaults from configuration file
    if "latitude" not in metadata:
        metadata['latitude'] = known_observatories[metadata['obstory_id']]['latitude']
    if "longitude" not in metadata:
        metadata['longitude'] = known_observatories[metadata['obstory_id']]['longitude']
    if "obstory_name" not in metadata:
        metadata['obstory_name'] = known_observatories[metadata['obstory_id']]['observatoryName']
    if "camera" not in metadata:
        metadata['camera'] = known_observatories[metadata['obstory_id']]['defaultCamera']
    if "lens" not in metadata:
        metadata['lens'] = known_observatories[metadata['obstory_id']]['defaultLens']
    if "software_version" not in metadata:
        metadata['software_version'] = settings['softwareVersion']
    if "user" is None:
        metadata['username'] = known_observatories[metadata['obstory_id']]['owner']

    # If observatory doesn't exist yet, create a new observatory
    if metadata['obstory_id'] not in obstory_id_list:
        # Create new observatory
        db.register_obstory(obstory_id=metadata['obstory_id'],
                            obstory_name=metadata['obstory_name'],
                            latitude=metadata['latitude'],
                            longitude=metadata['longitude'],
                            owner=metadata['username'])

    for item, value in metadata.items():
        if item not in ["obstory_id", "username", "utc", "latitude", "longitude", "name"]:

            # Offer user options to update metadata
            if item == "camera":
                hw.update_camera(db=db, obstory_id=metadata['obstory_id'], utc=metadata['utc'], name=value)

            elif item == "lens":
                hw.update_lens(db=db, obstory_id=metadata['obstory_id'], utc=metadata['utc'], name=value)

            # Register arbitrary metadata
            else:
                db.register_obstory_metadata(obstory_id=metadata['obstory_id'],
                                             key=item,
                                             value=value,
                                             metadata_time=metadata['utc'],
                                             time_created=time.time(),
                                             user_created=metadata['username'])

    # Commit changes to database
    db.commit()


if __name__ == "__main__":
    # Read input parameters
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observatory', dest='obstory_id', default=installation_info['observatoryId'],
                        help="ID of the observatory we are set the status for")
    parser.add_argument('--user', dest='username', default=None,
                        help="Username of the user who is setting this status update")
    parser.add_argument('--utc', dest='utc', default=time.time(),
                        type=float,
                        help="Timestamp for status update")
    parsed, unknown = parser.parse_known_args()

    for arg in unknown:
        if arg.startswith(("-", "--")):
            parser.add_argument(arg)

    args = parser.parse_args()

    add_observatory_status(metadata=vars(args))
