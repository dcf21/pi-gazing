#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# listObservatories.py
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
Display a list of all the observatories registered in the database.
"""


from pigazing_helpers import connect_db
from pigazing_helpers.obsarchive import obsarchive_db
from pigazing_helpers.settings_read import settings, installation_info


def list_observatories():
    """
    Display a list of all the observatories registered in the database.

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

    # Fetch observatory IDs
    obstory_ids = db.get_obstory_ids()
    obstory_ids.sort()

    # Open connection to database
    [db0, conn] = connect_db.connect_db()

    # List information about each observatory
    print("{:6s} {:32s} {:32s} {:6s} {:6s} {:s}".format("ObsID", "Public ID", "Name", "Lat", "Lng", "Observations"))
    for item in obstory_ids:
        obstory_info = db.get_obstory_from_id(obstory_id=item)

        # Count observations
        conn.execute('SELECT COUNT(*) FROM archive_observations WHERE observatory=%s;', (obstory_info['uid'],))
        results = conn.fetchall()
        obs_count = results[0]["COUNT(*)"]

        print("{:6d} {:32s} {:32s} {:6.1f} {:6.1f} {:7d}".format(obstory_info['uid'], obstory_info['publicId'],
                                                                 obstory_info['name'],
                                                                 obstory_info['latitude'], obstory_info['longitude'],
                                                                 obs_count))


if __name__ == "__main__":
    list_observatories()
