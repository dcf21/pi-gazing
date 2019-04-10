#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# deleteExport.py
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
This script is used to delete an export configuration, used to export observations to a remote installation
"""

import sys
import argparse

from pigazing_helpers.obsarchive import obsarchive_db
from pigazing_helpers.settings_read import settings, installation_info


def delete_export(export_id):
    # Open connection to image archive
    db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                           db_host=installation_info['mysqlHost'],
                                           db_user=installation_info['mysqlUser'],
                                           db_password=installation_info['mysqlPassword'],
                                           db_name=installation_info['mysqlDatabase'],
                                           obstory_id=installation_info['observatoryId'])

    # Check that requested export exists
    configs = [item.id for item in db.get_export_configurations()]

    if export_id not in configs:
        print("Export <{}> does not exist".format(export_id))
        sys.exit(0)

    # Delete all export config
    db.delete_export_configuration(export_id)

    # Commit changes to database
    db.commit()


if __name__ == "__main__":
    # Read commandline arguments
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--id',
                        required=True,
                        dest='id',
                        help='The ID of the export to be deleted')
    args = parser.parse_args()

    delete_export(export_id=args.id)
