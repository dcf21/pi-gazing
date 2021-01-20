#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# listUsers.py
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
Display a list of all user accounts in the database.
"""

import operator

from pigazing_helpers import connect_db
from pigazing_helpers.obsarchive import obsarchive_db
from pigazing_helpers.settings_read import settings, installation_info


def list_users():
    """
    Display a list of all user accounts in the database.

    :return:
        None
    """
    # Open connection to image archive
    db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                           db_host=installation_info['mysqlHost'],
                                           db_user=installation_info['mysqlUser'],
                                           db_password=installation_info['mysqlPassword'],
                                           db_name=installation_info['mysqlDatabase'],
                                           obstory_id=installation_info['observatoryId'])

    # Fetch list of users
    user_ids = db.get_users()
    user_ids.sort(key=operator.attrgetter('user_id'))

    # Open connection to database
    [db0, conn] = connect_db.connect_db()

    # List information about each user in turn
    print("{:32s} {:32s} {:48s} {:s}".format("Username", "Name", "Roles", "Observations"))
    for user_info in user_ids:
        # Count observations
        conn.execute('SELECT COUNT(*) FROM archive_observations WHERE userId=%s;', (user_info.user_id,))
        results = conn.fetchall()
        obs_count = results[0]["COUNT(*)"]

        # Print user information
        print("{:32s} {:32s} {:48s} {:9d}".format(user_info.user_id, user_info.name, str(user_info.roles), obs_count))


if __name__ == "__main__":
    list_users()
