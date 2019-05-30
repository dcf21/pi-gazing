#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# listObservatoryStatusHistory.py
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
Lists all of the metadata updates posted by a particular observatory between two given unix times
"""

import argparse
import sys
import time

from pigazing_helpers import dcf_ast
from pigazing_helpers.obsarchive import obsarchive_db
from pigazing_helpers.obsarchive import obsarchive_model as mp
from pigazing_helpers.settings_read import settings, installation_info


def list_observatory_status(utc_min, utc_max, obstory):
    # Open connection to image archive
    db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                           db_host=installation_info['mysqlHost'],
                                           db_user=installation_info['mysqlUser'],
                                           db_password=installation_info['mysqlPassword'],
                                           db_name=installation_info['mysqlDatabase'],
                                           obstory_id=installation_info['observatoryId'])

    try:
        obstory_info = db.get_obstory_from_id(obstory_id=obstory)
    except ValueError:
        print("Unknown observatory <{}>. Run ./list_observatories.py to see a list of available observatories.".
              format(obstory))
        sys.exit(0)

    title = "Observatory <{}>".format(obstory)
    print("\n\n{}\n{}".format(title, "-" * len(title)))

    search = mp.ObservatoryMetadataSearch(obstory_ids=[obstory], time_min=utc_min, time_max=utc_max)
    data = db.search_obstory_metadata(search)
    data = data['items']
    data.sort(key=lambda x: x.time)
    print("  * {:d} matching metadata items in time range {} --> {}".format(len(data),
                                                                            dcf_ast.date_string(utc_min),
                                                                            dcf_ast.date_string(utc_max)))

    # Check which items remain current
    refreshed = False
    data.reverse()
    keys_seen = []
    for item in data:
        # The magic metadata keyword "pigazing:refresh" causes all older metadata to be superseded
        if item.key == "refresh" and not refreshed:
            item.still_current = True
            refreshed = True
        # If we don't have a later metadata update for the same keyword, then this metadata remains current
        elif item.key not in keys_seen and not refreshed:
            item.still_current = True
            keys_seen.append(item.key)
        # This metadata item has been superseded
        else:
            item.still_current = False
    data.reverse()

    # Display list of items
    for item in data:
        if item.still_current:
            current_flag = "+"
        else:
            current_flag = " "
        print("  * {} [ID {}] {} -- {:16s} = {}".format(current_flag, item.id, dcf_ast.date_string(item.time),
                                                        item.key, item.value))


if __name__ == "__main__":
    # Read input parameters
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--t-min', dest='utc_min', default=0,
                        type=float,
                        help="Only list metadata updates after the specified unix time")
    parser.add_argument('--t-max', dest='utc_max', default=time.time(),
                        type=float,
                        help="Only list metadata updates before the specified unix time")
    parser.add_argument('--observatory', dest='obstory_id', default=installation_info['observatoryId'],
                        help="ID of the observatory we are to list events from")
    args = parser.parse_args()

    list_observatory_status(utc_min=args.utc_min,
                            utc_max=args.utc_max,
                            obstory=args.obstory_id,
                            )
