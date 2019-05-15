#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# addExport.py
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
This script is used to set up an observatory to export data to a remote installation
"""

import argparse
import sys

from pigazing_helpers.obsarchive import obsarchive_model, obsarchive_db
from pigazing_helpers.settings_read import settings, installation_info


def add_export(url, username, password):
    # Open connection to image archive
    db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                           db_host=installation_info['mysqlHost'],
                                           db_user=installation_info['mysqlUser'],
                                           db_password=installation_info['mysqlPassword'],
                                           db_name=installation_info['mysqlDatabase'],
                                           obstory_id=installation_info['observatoryId'])

    # Set up default observatory metadata export configuration
    search = obsarchive_model.ObservatoryMetadataSearch(limit=None)
    config = obsarchive_model.ExportConfiguration(target_url=url,
                                                  user_id=username,
                                                  password=password,
                                                  search=search, name="metadata_export",
                                                  description="Export all observatory metadata to remote server",
                                                  enabled=True)
    db.create_or_update_export_configuration(config)

    # Set up default observation export configuration
    search = obsarchive_model.ObservationSearch(limit=None)
    config = obsarchive_model.ExportConfiguration(target_url=url,
                                                  user_id=username,
                                                  password=password,
                                                  search=search, name="obs_export",
                                                  description="Export all observation objects to remote server",
                                                  enabled=True)
    db.create_or_update_export_configuration(config)

    # Set up default file export configuration
    search = obsarchive_model.FileRecordSearch(limit=None)
    config = obsarchive_model.ExportConfiguration(target_url=url,
                                                  user_id=username,
                                                  password=password,
                                                  search=search, name="file_export",
                                                  description="Export all image files to remote server",
                                                  enabled=True)
    db.create_or_update_export_configuration(config)

    # Commit changes to database
    db.commit()


if __name__ == "__main__":
    # Read commandline arguments
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default=installation_info['exportURL'],
                        dest='url', help='The URL we are to export to')
    parser.add_argument('--username', default=installation_info['exportUsername'],
                        dest='username', help='The username of the account on the remote server used for importing')
    parser.add_argument('--password', default=installation_info['exportPassword'],
                        dest='password', help='The password of the account on the remote server used for importing')
    args = parser.parse_args()

    if args.url.strip() == "":
        print("No export URL specified.")
        sys.exit(0)

    add_export(url=args.url,
               username=args.username,
               password=args.password
               )
