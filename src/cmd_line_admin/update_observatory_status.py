#!../../virtualenv/bin/python3
# -*- coding: utf-8 -*-
# update_observatory_status.py
#
# -------------------------------------------------
# Copyright 2015-2019 Dominic Ford
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

It is useful to run this after <sql/rebuild.sh> to specify the lens, camera, etc being used.
"""

import argparse
import os
import sys
import time

from pigazing_helpers import hardware_properties
from pigazing_helpers.obsarchive import obsarchive_db
from pigazing_helpers.settings_read import settings, installation_info

db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                       db_host=installation_info['mysqlHost'],
                                       db_user=installation_info['mysqlUser'],
                                       db_password=installation_info['mysqlPassword'],
                                       db_name=installation_info['mysqlDatabase'],
                                       obstory_id=installation_info['observatoryId'])

hw = hardware_properties.HardwareProps(os.path.join(settings['pythonPath'], "camera_properties"))

# Read arguments
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--obstory-name',
                    help="Name of the observatory",
                    dest="obstory_name",
                    default=None)
parser.add_argument('--obstory-id',
                    help="Observatory ID code",
                    dest="obstory_id",
                    default=None)
parser.add_argument('--latitude',
                    help="Latitude",
                    dest="latitude", type=float,
                    default=None)
parser.add_argument('--longitude',
                    help="Longitude",
                    dest="longitude", type=float,
                    default=None)
parser.add_argument('--metadata_time',
                    help="Unix time stamp for update",
                    dest="metadata_time", type=float,
                    default=None)
parser.add_argument('--camera',
                    help="New camera model",
                    dest="camera",
                    default=None)
parser.add_argument('--lens',
                    help="Name of new lens",
                    dest="lens",
                    default=None)
args = parser.parse_args()

# List current observatory statuses
print("Current observatory statuses")
print("----------------------------")
obstory_id_list = db.get_obstory_ids()
for obstory_id in obstory_id_list:
    print("{}\n".format(obstory_id))
    print("  * Observatory configuration")
    o = db.get_obstory_from_id(obstory_id=obstory_id)
    for item in ['latitude', 'longitude', 'name', 'publicId']:
        print("    * {} = {}".format(item, o[item]))
    status = db.get_obstory_status(obstory_id=obstory_id)
    status_keys = list(status.keys())
    status_keys.sort()
    print("\n  * Additional metadata")
    for item in status_keys:
        print("    * {} = {}".format(item, status[item]))
    print("\n")
if len(obstory_id_list) == 0:
    print("None!\n")

# If no observatory specified to update, do nothing more
if args.obstory_id is None:
    sys.exit(0)

# Find out time that metadata update should be applied to
if args.metadata_time is None:
    args.metadata_time = time.time()
metadata_time = float(args.metadata_time)

# If observatory doesn't exist yet, create a new observatory
if args.obstory_id not in obstory_id_list:
    # If input parameters have not been supplied, read the defaults from configuration file
    if args.latitude is None:
        args.latitude = installation_info['latitude']
    if args.longitude is None:
        args.longitude = installation_info['longitude']
    if args.obstory_name is None:
        args.obstory_name = installation_info['observatoryName']
    if args.camera is None:
        args.camera = installation_info['defaultCamera']
    if args.lens is None:
        args.lens = installation_info['defaultLens']

    # Create new observatory
    db.register_obstory(obstory_id=args.obstory_id,
                        obstory_name=args.obstory_name,
                        latitude=args.latitude,
                        longitude=args.longitude,
                        owner=settings['pigazingUser'])

    # Set location of new observatory
    db.register_obstory_metadata(obstory_id=args.obstory_id,
                                 key="latitude",
                                 value=args.latitude,
                                 metadata_time=metadata_time,
                                 time_created=time.time(),
                                 user_created=settings['pigazingUser'])
    db.register_obstory_metadata(obstory_id=args.obstory_id,
                                 key="longitude",
                                 value=args.longitude,
                                 metadata_time=metadata_time,
                                 time_created=time.time(),
                                 user_created=settings['pigazingUser'])
    db.register_obstory_metadata(obstory_id=args.obstory_id,
                                 key="location_source",
                                 value="manual",
                                 metadata_time=metadata_time,
                                 time_created=time.time(),
                                 user_created=settings['pigazingUser'])
    # Newly created observatory has no metadata
    obstory_status = {}
else:
    # Fetch metadata about the observatory we are updating
    obstory_status = db.get_obstory_status(obstory_id=args.obstory_id)

# Register software version in use
db.register_obstory_metadata(obstory_id=args.obstory_id,
                             key="software_version",
                             value=settings['softwareVersion'],
                             metadata_time=metadata_time,
                             time_created=time.time(),
                             user_created=settings['pigazingUser'])

# Offer user options to update metadata
if args.camera is not None:
    hw.update_camera(db=db, obstory_id=args.obstory_id, utc=metadata_time, name=args.camera)

if args.lens is not None:
    hw.update_lens(db=db, obstory_id=args.obstory_id, utc=metadata_time, name=args.lens)

# Commit changes to database
db.commit()
