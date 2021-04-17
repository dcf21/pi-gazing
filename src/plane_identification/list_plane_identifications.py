#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# list_plane_identifications.py
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
List identifications for all planes detected by a particular observatory within a specified time period.
"""

import argparse
import logging
import os
import time
from operator import itemgetter

from pigazing_helpers import connect_db
from pigazing_helpers.dcf_ast import date_string
from pigazing_helpers.settings_read import settings, installation_info


def list_planes(obstory_id, utc_min, utc_max):
    """
    List all the plane identifications for a particular observatory.

    :param obstory_id:
        The ID of the observatory we want to list identifications for.
    :param utc_min:
        The start of the time period in which we should list identifications (unix time).
    :param utc_max:
        The end of the time period in which we should list identifications (unix time).
    :return:
        None
    """

    # Open connection to database
    [db0, conn] = connect_db.connect_db()

    # Start compiling list of plane identifications
    plane_identifications = []

    # Select moving objects with plane identifications
    conn.execute("""
SELECT am1.stringValue AS call_sign, am2.floatValue AS ang_offset,
       am3.floatValue AS clock_offset, am4.floatValue AS duration, am5.stringValue AS hex_ident,
       am6.floatValue AS distance,
       am7.stringValue AS operator, am8.stringValue AS model, am9.stringValue AS manufacturer,
       o.obsTime AS time, o.publicId AS obsId
FROM archive_observations o
INNER JOIN archive_metadata am1 ON o.uid = am1.observationId AND
    am1.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="plane:call_sign")
INNER JOIN archive_metadata am2 ON o.uid = am2.observationId AND
    am2.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="plane:angular_offset")
INNER JOIN archive_metadata am3 ON o.uid = am3.observationId AND
    am3.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="plane:clock_offset")
INNER JOIN archive_metadata am4 ON o.uid = am4.observationId AND
    am4.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="pigazing:duration")
INNER JOIN archive_metadata am5 ON o.uid = am5.observationId AND
    am5.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="plane:hex_ident")
LEFT JOIN archive_metadata am6 ON o.uid = am6.observationId AND
    am6.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="plane:distance")

LEFT JOIN archive_metadata am7 ON o.uid = am7.observationId AND
    am7.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="plane:operator")
LEFT JOIN archive_metadata am8 ON o.uid = am8.observationId AND
    am8.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="plane:model")
LEFT JOIN archive_metadata am9 ON o.uid = am9.observationId AND
    am9.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="plane:manufacturer")


WHERE
    o.observatory = (SELECT uid FROM archive_observatories WHERE publicId=%s) AND
    o.obsTime BETWEEN %s AND %s;
""", (obstory_id, utc_min, utc_max))
    results = conn.fetchall()

    for item in results:
        plane_identifications.append({
            'id': item['obsId'],
            'time': item['time'],
            'call_sign': item['call_sign'],
            'ang_offset': item['ang_offset'],
            'clock_offset': item['clock_offset'],
            'duration': item['duration'],
            'hex_ident': item['hex_ident'],
            'distance': item['distance'],
            'operator': item['operator'],
            'model': item['model'],
            'manufacturer': item['manufacturer']
        })

    # Sort identifications by time
    plane_identifications.sort(key=itemgetter('time'))

    # Display column headings
    print("""\
{:16s} {:18s} {:18s} {:8s} {:10s} {:10s} {:10s} {:30s} {:30s} {:30s}\
""".format("Time", "Call sign", "Hex ident", "Duration", "Ang offset", "Clock off", "Distance", "Operator", "Model",
           "Manufacturer"))

    # Display list of meteors
    for item in plane_identifications:
        print("""\
{:16s} {:18s} {:18s} {:8.1f} {:10.1f} {:10.1f} {:10.1f} {:30s} {:30s} {:30s}\
""".format(date_string(item['time']),
           item['call_sign'],
           item['hex_ident'],
           item['duration'],
           item['ang_offset'],
           item['clock_offset'],
           item['distance'],
           item['operator'], item['model'], item['manufacturer']
           ))

    # Clean up and exit
    return


# If we're called as a script, run the method list_satellites()
if __name__ == "__main__":
    # Read command-line arguments
    parser = argparse.ArgumentParser(description=__doc__)

    # By default, list the planes seen over past 24 hours
    parser.add_argument('--utc-min', dest='utc_min', default=0,
                        type=float,
                        help="Only list planes recorded after the specified unix time")
    parser.add_argument('--utc-max', dest='utc_max', default=time.time(),
                        type=float,
                        help="Only list planes recorded before the specified unix time")

    parser.add_argument('--observatory', dest='obstory_id', default=installation_info['observatoryId'],
                        help="ID of the observatory we are to list planes from")
    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(level=logging.INFO,
                        format='[%(asctime)s] %(levelname)s:%(filename)s:%(message)s',
                        datefmt='%d/%m/%Y %H:%M:%S',
                        handlers=[
                            logging.FileHandler(os.path.join(settings['pythonPath'], "../datadir/pigazing.log")),
                            logging.StreamHandler()
                        ])
    logger = logging.getLogger(__name__)
    logger.info(__doc__.strip())

    # List the orientation of images
    list_planes(obstory_id=args.obstory_id,
                utc_min=args.utc_min,
                utc_max=args.utc_max)
