#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# list_satellite_identifications.py
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
List identifications for all satellites detected by a particular observatory within a specified time period.
"""

import argparse
import logging
import os
import time
from operator import itemgetter

from pigazing_helpers import connect_db
from pigazing_helpers.dcf_ast import date_string
from pigazing_helpers.settings_read import settings, installation_info


def list_satellites(obstory_id, utc_min, utc_max):
    """
    List all the satellite identifications for a particular observatory.

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

    # Start compiling list of satellite identifications
    satellite_identifications = []

    # Select moving objects with satellite identifications
    conn.execute("""
SELECT am1.stringValue AS satellite_name, am2.floatValue AS ang_offset,
       am3.floatValue AS clock_offset, am4.floatValue AS duration, am5.floatValue AS norad_id,
       o.obsTime AS time, o.publicId AS obsId
FROM archive_observations o
INNER JOIN archive_metadata am1 ON o.uid = am1.observationId AND
    am1.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="satellite:name")
INNER JOIN archive_metadata am2 ON o.uid = am2.observationId AND
    am2.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="satellite:angular_offset")
INNER JOIN archive_metadata am3 ON o.uid = am3.observationId AND
    am3.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="satellite:clock_offset")
INNER JOIN archive_metadata am4 ON o.uid = am4.observationId AND
    am4.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="pigazing:duration")
INNER JOIN archive_metadata am5 ON o.uid = am5.observationId AND
    am5.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="satellite:norad_id")
WHERE
    o.observatory = (SELECT uid FROM archive_observatories WHERE publicId=%s) AND
    o.obsTime BETWEEN %s AND %s;
""", (obstory_id, utc_min, utc_max))
    results = conn.fetchall()

    for item in results:
        satellite_identifications.append({
            'id': item['obsId'],
            'time': item['time'],
            'satellite_name': item['satellite_name'],
            'ang_offset': item['ang_offset'],
            'clock_offset': item['clock_offset'],
            'duration': item['duration'],
            'norad_id': int(item['norad_id'])
        })

    # Sort identifications by time
    satellite_identifications.sort(key=itemgetter('time'))

    # Display column headings
    print("""\
{:16s} {:7s} {:32s} {:26s} {:8s} {:10s} {:10s}\
""".format("Time", "NORAD", "ID", "Satellite", "Duration", "Ang offset", "Clock offset"))

    # Display list of meteors
    for item in satellite_identifications:
        print("""\
{:16s} {:7d} {:32s} {:26s} {:8.1f} {:10.1f} {:10.1f}\
""".format(date_string(item['time']),
           item['norad_id'],
           item['id'],
           item['satellite_name'],
           item['duration'],
           item['ang_offset'],
           item['clock_offset'],
           ))

    # Clean up and exit
    return


# If we're called as a script, run the method list_satellites()
if __name__ == "__main__":
    # Read command-line arguments
    parser = argparse.ArgumentParser(description=__doc__)

    # By default, list the satellites seen over past 24 hours
    parser.add_argument('--utc-min', dest='utc_min', default=0,
                        type=float,
                        help="Only list satellites recorded after the specified unix time")
    parser.add_argument('--utc-max', dest='utc_max', default=time.time(),
                        type=float,
                        help="Only list satellites recorded before the specified unix time")

    parser.add_argument('--observatory', dest='obstory_id', default=installation_info['observatoryId'],
                        help="ID of the observatory we are to list satellites from")
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
    list_satellites(obstory_id=args.obstory_id,
                    utc_min=args.utc_min,
                    utc_max=args.utc_max)
