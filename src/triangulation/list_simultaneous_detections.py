#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# list_simultaneous_detections.py
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
Display a list of all the images registered in the database.
"""

import argparse
import time

from pigazing_helpers import connect_db
from pigazing_helpers.dcf_ast import date_string

simultaneous_event_type = "pigazing:simultaneous"


def list_simultaneous_detections(utc_min=None, utc_max=None):
    """
    Display a list of all the simultaneous object detections registered in the database.

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
        where.append("o.obsTime>=%s")
        args.append(utc_min)
    if utc_max is not None:
        where.append("o.obsTime<=%s")
        args.append(utc_max)

    # Search for observation groups containing groups of simultaneous detections
    conn.execute("""
SELECT g.publicId AS groupId, o.publicId AS obsId, o.obsTime, am.stringValue AS objectType
FROM archive_obs_groups g
INNER JOIN archive_obs_group_members m on g.uid = m.groupId
INNER JOIN archive_observations o ON m.childObservation = o.uid
INNER JOIN archive_metadata am ON g.uid = am.groupId AND
    am.fieldId = (SELECT uid FROM archive_metadataFields WHERE metaKey="web:category")
WHERE """ + " AND ".join(where) + """
ORDER BY o.obsTime;
""", args)
    results = conn.fetchall()

    # Count how many simultaneous detections we find by type
    detections_by_type = {}

    # Compile list of groups
    obs_groups = {}
    obs_group_ids = []
    for item in results:
        key = item['groupId']
        if key not in obs_groups:
            obs_groups[key] = []
            obs_group_ids.append({
                'groupId': key,
                'time': item['obsTime'],
                'type': item['objectType']
            })

            # Add this simultaneous detection to tally
            if item['objectType'] not in detections_by_type:
                detections_by_type[item['objectType']] = 0
            detections_by_type[item['objectType']] += 1
        obs_groups[key].append(item['obsId'])

    # List information about each observation in turn
    print("{:16s} {:20s} {:20s} {:s}".format("Time", "groupId", "Object type", "Observations"))
    for group_info in obs_group_ids:
        # Print group information
        print("{:16s} {:20s} {:20s} {:s}".format(group_info['groupId'],
                                                 date_string(group_info['time']),
                                                 group_info['type'],
                                                 " ".join(obs_groups[group_info['groupId']])
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

    list_simultaneous_detections(utc_min=args.utc_min,
                                 utc_max=args.utc_max
                                 )
