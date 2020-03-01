#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# checkDatabaseIntegrity.py
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
Checks for missing files
"""

import os

from pigazing_helpers.obsarchive import obsarchive_db
from pigazing_helpers.settings_read import settings, installation_info


def check_database_integrity():
    # Open connection to image archive
    db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                           db_host=installation_info['mysqlHost'],
                                           db_user=installation_info['mysqlUser'],
                                           db_password=installation_info['mysqlPassword'],
                                           db_name=installation_info['mysqlDatabase'],
                                           obstory_id=installation_info['observatoryId'])
    sql = db.con

    # Check files exist
    print("Checking whether files exist...")
    sql.execute("SELECT repositoryFname FROM archive_files;")
    for item in sql.fetchall():
        id = item['repositoryFname']
        if not os.path.exists(db.file_path_for_id(id)):
            print("Files: Missing file ID <{}>".format(id))
            continue
        file_size = os.stat(db.file_path_for_id(id)).st_size
        sql.execute("UPDATE archive_files SET fileSize=%s WHERE repositoryFname=%s;",
                    (file_size, id))

    # Commit changes to database
    db.commit()


if __name__ == "__main__":
    check_database_integrity()
