#!../../virtualenv/bin/python3
# -*- coding: utf-8 -*-
# default_exports.py
#
# -------------------------------------------------
# Copyright 2015-2018 Dominic Ford
#
# This file is part of Meteor Pi.
#
# Meteor Pi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Meteor Pi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Meteor Pi.  If not, see <http://www.gnu.org/licenses/>.
# -------------------------------------------------

"""
This script is used to set up an observatory to use the default export configuration specified in installation_info.py

It is useful to run this after <init_database/rebuild.sh>
"""

import sys

from pigazing_helpers.obsarchive import archive_model as mp
from pigazing_helpers.obsarchive import archive_db

from pigazing_helpers import settings_read

db = archive_db.MeteorDatabase(settings_read.settings['dbFilestore'])

# List all current user accounts
print("Current export configurations")
print("-----------------------------")
configs = db.get_export_configurations()
for config in configs:
    print(config.as_dict())
print("\n")

confirm = input('Replace with default configuration? (Y/N) ')
if confirm not in 'Yy':
    sys.exit(0)

# Delete all export config
for config in configs:
    db.delete_export_configuration(config.config_id)

# Set up default observatory metadata export configuration
search = mp.ObservatoryMetadataSearch(limit=None)
config = mp.ExportConfiguration(target_url=installation_info.local_conf['exportURL'],
                                user_id=installation_info.local_conf['exportUsername'],
                                password=installation_info.local_conf['exportPassword'],
                                search=search, name="metadata_export",
                                description="Export all observatory metadata to remote server", enabled=True)
db.create_or_update_export_configuration(config)

# Set up default observation export configuration
search = mp.ObservationSearch(limit=None)
config = mp.ExportConfiguration(target_url=installation_info.local_conf['exportURL'],
                                user_id=installation_info.local_conf['exportUsername'],
                                password=installation_info.local_conf['exportPassword'],
                                search=search, name="obs_export",
                                description="Export all observation objects to remote server", enabled=True)
db.create_or_update_export_configuration(config)

# Set up default file export configuration
search = mp.FileRecordSearch(limit=None)
config = mp.ExportConfiguration(target_url=installation_info.local_conf['exportURL'],
                                user_id=installation_info.local_conf['exportUsername'],
                                password=installation_info.local_conf['exportPassword'],
                                search=search, name="file_export",
                                description="Export all image files to remote server", enabled=True)
db.create_or_update_export_configuration(config)

# Commit changes to database
db.commit()
