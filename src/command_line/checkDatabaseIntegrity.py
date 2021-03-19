#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# checkDatabaseIntegrity.py
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
Checks for missing files
"""

import glob
import logging
import os

from pigazing_helpers.obsarchive import obsarchive_db
from pigazing_helpers.settings_read import settings, installation_info


def check_database_integrity(purge=False):
    # Open connection to image archive
    db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                           db_host=installation_info['mysqlHost'],
                                           db_user=installation_info['mysqlUser'],
                                           db_password=installation_info['mysqlPassword'],
                                           db_name=installation_info['mysqlDatabase'],
                                           obstory_id=installation_info['observatoryId'])
    sql = db.con

    # Check files exist
    file_list = {}
    logging.info("Checking whether files exist...")
    sql.execute("SELECT repositoryFname FROM archive_files;")
    for item in sql.fetchall():
        id = item['repositoryFname']
        file_list[id] = True
        if not os.path.exists(db.file_path_for_id(id)):
            logging.info("Files: Missing file ID <{}>".format(id))

            if purge:
                sql.execute("DELETE FROM archive_files WHERE repositoryFname=%s;", (id,))

    # Check for files which aren't in database
    logging.info("Checking for files with no database record...")
    for item in glob.glob(os.path.join(db.file_store_path, "*")):
        filename = os.path.split(item)[1]
        if filename not in file_list:
            logging.info("Files: File not in database <{}>".format(filename))

    # Checking for observations with no files
    logging.info("Checking for observations with no files...")
    sql.execute("SELECT publicId FROM archive_observations WHERE uid NOT IN (SELECT observationId FROM archive_files)")
    for item in sql.fetchall():
        logging.info("Files: Observation with no files <{}>".format(item['publicId']))

        if purge:
            sql.execute("DELETE FROM archive_observations WHERE publicId=%s;", (item['publicId'],))

    # Commit changes to database
    db.commit()
    db.close_db()


if __name__ == "__main__":
    check_database_integrity()
