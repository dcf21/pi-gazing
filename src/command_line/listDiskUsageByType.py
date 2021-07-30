#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# listDiskUsageByType.py
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
Search through all of the files in the database, and give a breakdown of the disk usage of different kinds
of moving objects.
"""

import argparse
import sys
import time

from pigazing_helpers.obsarchive import obsarchive_db
from pigazing_helpers.settings_read import settings, installation_info

from listDiskUsage import render_data_size_list


def list_disk_usage(utc_min, utc_max):
    """
    Search through all of the files in the database, and give a breakdown of the disk usage of different kinds
    of moving objects.

    :param utc_min:
        Only list disk usage after the specified unix time
    :param utc_max:
        Only list disk usage before the specified unix time
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

    file_census = {}

    # Get list of files in each directory
    db.con.execute("""
SELECT f.mimeType, f.fileTime, f.fileSize, ot.name AS semanticType, am.stringValue AS web_type
FROM archive_files f
INNER JOIN archive_observations o on f.observationId = o.uid
INNER JOIN archive_semanticTypes ot on o.obsType = ot.uid
INNER JOIN archive_metadata am on o.uid = am.observationId
    AND am.fieldId=(SELECT x.uid FROM archive_metadataFields x WHERE x.metaKey="web:category")
WHERE f.fileTime BETWEEN %s AND %s;
""", (utc_min, utc_max))

    # Process each file in turn
    for item in db.con.fetchall():
        file_type = item['web_type']
        if file_type not in file_census:
            file_census[file_type] = 0
        file_census[file_type] += item['fileSize']

    # Render quick and dirty table
    out = sys.stdout
    cols = list(file_census.keys())
    cols.sort()

    # Render column headings
    for col_head in cols:
        out.write("{:25s} ".format(col_head))
    out.write("\n")

    # Render data
    data = []
    for col_head in cols:
        data.append(file_census[col_head])
    data_string = render_data_size_list(file_sizes=data)
    for i in range(len(cols)):
        out.write("{:25s} ".format(data_string[i]))
    out.write("\n")


if __name__ == "__main__":
    # Read input parameters
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--t-min', dest='utc_min', default=0,
                        type=float,
                        help="Only list disk usage after the specified unix time")
    parser.add_argument('--t-max', dest='utc_max', default=time.time(),
                        type=float,
                        help="Only list disk usage before the specified unix time")
    args = parser.parse_args()

    list_disk_usage(utc_min=args.utc_min,
                    utc_max=args.utc_max
                    )
