#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# list_orientation.py
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
List all orientation fixes for a particular observatory within a specified time period.
"""

import argparse
import logging
import os
import time
from operator import itemgetter

from pigazing_helpers import connect_db
from pigazing_helpers.dcf_ast import date_string
from pigazing_helpers.settings_read import settings, installation_info


def list_orientation_fixes(obstory_id, utc_min, utc_max):
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

    # Start compiling list of orientation fixes
    orientation_fixes = []

    # Select observations with orientation fits
    conn.execute("""
SELECT am1.floatValue AS altitude, am2.floatValue AS azimuth, am3.floatValue AS tilt,
       am4.floatValue AS width_x_field, am5.floatValue AS width_y_field,
       o.obsTime AS time
FROM archive_observations o
INNER JOIN archive_metadata am1 ON o.uid = am1.observationId AND
    am1.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="orientation:altitude")
INNER JOIN archive_metadata am2 ON o.uid = am2.observationId AND
    am2.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="orientation:azimuth")
INNER JOIN archive_metadata am3 ON o.uid = am3.observationId AND
    am3.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="orientation:tilt")
INNER JOIN archive_metadata am4 ON o.uid = am4.observationId AND
    am4.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="orientation:width_x_field")
INNER JOIN archive_metadata am5 ON o.uid = am5.observationId AND
    am5.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="orientation:width_y_field")
WHERE
    o.observatory = (SELECT uid FROM archive_observatories WHERE publicId=%s) AND
    o.obsTime BETWEEN %s AND %s;
""", (obstory_id, utc_min, utc_max))
    results = conn.fetchall()

    for item in results:
        orientation_fixes.append({
            'time': item['time'],
            'average': False,
            'fit': item
        })

    # Select observatory orientation fits
    conn.execute("""
SELECT am1.floatValue AS altitude, am2.floatValue AS azimuth, am3.floatValue AS tilt,
       am4.floatValue AS width_x_field, am5.floatValue AS width_y_field,
       am1.time AS time
FROM archive_observatories o
INNER JOIN archive_metadata am1 ON o.uid = am1.observatory AND
    am1.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="orientation:altitude")
INNER JOIN archive_metadata am2 ON o.uid = am2.observatory AND am2.time=am1.time AND
    am2.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="orientation:azimuth")
INNER JOIN archive_metadata am3 ON o.uid = am3.observatory AND am3.time=am1.time AND
    am3.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="orientation:tilt")
INNER JOIN archive_metadata am4 ON o.uid = am4.observatory AND am4.time=am1.time AND
    am4.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="orientation:width_x_field")
INNER JOIN archive_metadata am5 ON o.uid = am5.observatory AND am5.time=am1.time AND
    am5.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="orientation:width_y_field")
WHERE
    o.publicId=%s AND
    am1.time BETWEEN %s AND %s;
""", (obstory_id, utc_min, utc_max))
    results = conn.fetchall()

    for item in results:
        orientation_fixes.append({
            'time': item['time'],
            'average': True,
            'fit': item
        })

    # Sort fixes by time
    orientation_fixes.sort(key=itemgetter('time'))

    # Display column headings
    print("""\
{:1s} {:16s} {:9s} {:9s} {:9s} {:8s} {:8s}\
""".format("", "Time", "Alt", "Az", "Tilt", "FoV X", "FoV Y"))

    # Display fixes
    for item in orientation_fixes:
        print("""\
{:s} {:16s} {:9.4f} {:9.4f} {:9.4f} {:8.3f} {:8.3f} {:s}\
""".format("\n>" if item['average'] else " ",
           date_string(item['time']),
           item['fit']['altitude'], item['fit']['azimuth'], item['fit']['tilt'],
           item['fit']['width_x_field'], item['fit']['width_y_field'],
           "\n" if item['average'] else ""))

    # Clean up and exit
    return


# If we're called as a script, run the method list_orientation_fixes()
if __name__ == "__main__":
    # Read command-line arguments
    parser = argparse.ArgumentParser(description=__doc__)

    # By default, list the orientation of images taken over past 24 hours
    parser.add_argument('--utc-min', dest='utc_min', default=time.time() - 3600 * 24,
                        type=float,
                        help="Only list fixes recorded after the specified unix time")
    parser.add_argument('--utc-max', dest='utc_max', default=time.time(),
                        type=float,
                        help="Only list fixes recorded before the specified unix time")

    parser.add_argument('--observatory', dest='obstory_id', default=installation_info['observatoryId'],
                        help="ID of the observatory we are to list orientation fixes for")
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
    list_orientation_fixes(obstory_id=args.obstory_id,
                           utc_min=args.utc_min,
                           utc_max=args.utc_max)
