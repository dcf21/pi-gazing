#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# list_shower_identifications.py
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
List the parent showers calculated for all meteors detected by a particular observatory within a specified time period.
"""

import argparse
import logging
import os
import time
from operator import itemgetter

from pigazing_helpers import connect_db
from pigazing_helpers.dcf_ast import date_string
from pigazing_helpers.settings_read import settings, installation_info


def list_meteors(obstory_id, utc_min, utc_max):
    """
    List all the orientation fixes for a particular observatory.

    :param obstory_id:
        The ID of the observatory we want to list orientation fixes for.
    :param utc_min:
        The start of the time period in which we should list orientation fixes (unix time).
    :param utc_max:
        The end of the time period in which we should list orientation fixes (unix time).
    :return:
        None
    """

    # Open connection to database
    [db0, conn] = connect_db.connect_db()

    # Start compiling list of meteor identifications
    meteor_identifications = []

    # Count how many meteors we find in each shower
    meteor_count_by_shower = {}

    # Select observations with orientation fits
    conn.execute("""
SELECT am1.stringValue AS name, am2.floatValue AS radiant_offset,
       o.obsTime AS time, o.publicId AS obsId
FROM archive_observations o
INNER JOIN archive_metadata am1 ON o.uid = am1.observationId AND
    am1.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="shower:name")
INNER JOIN archive_metadata am2 ON o.uid = am2.observationId AND
    am2.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="shower:radiant_offset")
WHERE
    o.observatory = (SELECT uid FROM archive_observatories WHERE publicId=%s) AND
    o.obsTime BETWEEN %s AND %s;
""", (obstory_id, utc_min, utc_max))
    results = conn.fetchall()

    for item in results:
        meteor_identifications.append({
            'id': item['obsId'],
            'time': item['time'],
            'shower': item['name'],
            'offset': item['radiant_offset']
        })

        # Update tally of meteors
        if item['name'] not in meteor_count_by_shower:
            meteor_count_by_shower[item['name']] = 0
        meteor_count_by_shower[item['name']] += 1

    # Sort meteors by time
    meteor_identifications.sort(key=itemgetter('time'))

    # Display column headings
    print("""\
{:16s} {:20s} {:20s} {:5s}\
""".format("Time", "ID", "Shower", "Offset"))

    # Display list of meteors
    for item in meteor_identifications:
        print("""\
{:16s} {:20s} {:26s} {:5.1f}\
""".format(date_string(item['time']),
           item['id'],
           item['shower'],
           item['offset']
           ))

    # Report tally of meteors
    logging.info("Tally of meteors by shower:")
    for shower in sorted(meteor_count_by_shower.keys()):
        logging.info("    * {:26s}: {:6d}".format(shower, meteor_count_by_shower[shower]))

    # Clean up and exit
    return


# If we're called as a script, run the method list_meteors()
if __name__ == "__main__":
    # Read command-line arguments
    parser = argparse.ArgumentParser(description=__doc__)

    # By default, list the orientation of images taken over past 24 hours
    parser.add_argument('--utc-min', dest='utc_min', default=0,
                        type=float,
                        help="Only list meteors recorded after the specified unix time")
    parser.add_argument('--utc-max', dest='utc_max', default=time.time(),
                        type=float,
                        help="Only list meteors recorded before the specified unix time")

    parser.add_argument('--observatory', dest='obstory_id', default=installation_info['observatoryId'],
                        help="ID of the observatory we are to list meteors from")
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
    list_meteors(obstory_id=args.obstory_id,
                 utc_min=args.utc_min,
                 utc_max=args.utc_max)
