#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# list_triangulations.py
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
Display a list of all the trajectories of moving objects registered in the database.
"""

import argparse
import time

from pigazing_helpers import connect_db
from pigazing_helpers.dcf_ast import date_string

simultaneous_event_type = "pigazing:simultaneous"


def list_triangulations(utc_min=None, utc_max=None):
    """
    Display a list of all the trajectories of moving objects registered in the database.

    :param utc_min:
        Only show observations made after the specified time stamp.

    :type utc_min:
        float

    :param utc_max:
        Only show observations made before the specified time stamp.

    :type utc_max:
        float

    :return:
        None
    """
    # Open connection to database
    [db0, conn] = connect_db.connect_db()

    # Compile search criteria for observation groups
    where = ["g.semanticType = (SELECT uid FROM archive_semanticTypes WHERE name=\"{}\")".
                 format(simultaneous_event_type)
             ]
    args = []

    if utc_min is not None:
        where.append("g.time>=%s")
        args.append(utc_min)
    if utc_max is not None:
        where.append("g.time<=%s")
        args.append(utc_max)

    # Search for observation groups containing groups of simultaneous detections
    conn.execute("""
SELECT g.publicId AS groupId, g.time AS time, am.stringValue AS objectType,
       am2.floatValue AS speed, am3.floatValue AS mean_altitude, am4.floatValue AS max_angular_offset,
       am5.floatValue AS max_baseline, am6.stringValue AS radiant_direction, am7.floatValue AS sight_line_count,
       am8.stringValue AS path
FROM archive_obs_groups g
INNER JOIN archive_metadata am ON g.uid = am.groupId AND
    am.fieldId = (SELECT uid FROM archive_metadataFields WHERE metaKey="web:category")
INNER JOIN archive_metadata am2 ON g.uid = am2.groupId AND
    am2.fieldId = (SELECT uid FROM archive_metadataFields WHERE metaKey="triangulation:speed")
INNER JOIN archive_metadata am3 ON g.uid = am3.groupId AND
    am3.fieldId = (SELECT uid FROM archive_metadataFields WHERE metaKey="triangulation:mean_altitude")
INNER JOIN archive_metadata am4 ON g.uid = am4.groupId AND
    am4.fieldId = (SELECT uid FROM archive_metadataFields WHERE metaKey="triangulation:max_angular_offset")
INNER JOIN archive_metadata am5 ON g.uid = am5.groupId AND
    am5.fieldId = (SELECT uid FROM archive_metadataFields WHERE metaKey="triangulation:max_baseline")
INNER JOIN archive_metadata am6 ON g.uid = am6.groupId AND
    am6.fieldId = (SELECT uid FROM archive_metadataFields WHERE metaKey="triangulation:radiant_direction")
INNER JOIN archive_metadata am7 ON g.uid = am7.groupId AND
    am7.fieldId = (SELECT uid FROM archive_metadataFields WHERE metaKey="triangulation:sight_line_count")
INNER JOIN archive_metadata am8 ON g.uid = am8.groupId AND
    am8.fieldId = (SELECT uid FROM archive_metadataFields WHERE metaKey="triangulation:path")
WHERE """ + " AND ".join(where) + """
ORDER BY g.time;
""", args)
    results = conn.fetchall()

    # Count how many simultaneous detections we find by type
    detections_by_type = {}

    # Compile tally by type
    for item in results:
        # Add this triangulation to tally
        if item['objectType'] not in detections_by_type:
            detections_by_type[item['objectType']] = 0
        detections_by_type[item['objectType']] += 1

    # List information about each observation in turn
    print("{:16s} {:20s} {:20s} {:8s} {:10s}".format("GroupId", "Time", "Object type", "Speed", "Altitude"))
    for item in results:
        # Print triangulation information
        print("{:16s} {:20s} {:20s} {:8.0f} {:10.0f}".format(item['groupId'],
                                                             date_string(item['time']),
                                                             item['objectType'],
                                                             item['speed'],
                                                             item['mean_altitude']
                                                             ))

    # Report tally of events
    print("\nTally of events by type:")
    for event_type in sorted(detections_by_type.keys()):
        print("    * {:26s}: {:6d}".format(event_type, detections_by_type[event_type]))


if __name__ == "__main__":
    # Read commandline arguments
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--utc-min', dest='utc_min', default=0,
                        type=float,
                        help="Only list events seen after the specified unix time")
    parser.add_argument('--utc-max', dest='utc_max', default=time.time(),
                        type=float,
                        help="Only list events seen before the specified unix time")
    args = parser.parse_args()

    list_triangulations(utc_min=args.utc_min,
                        utc_max=args.utc_max
                        )
