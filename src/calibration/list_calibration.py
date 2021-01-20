#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# list_calibration.py
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
List calibration fixes for a particular observatory within a specified time period.
"""

import argparse
import logging
import os
import time
import json
from operator import itemgetter

from pigazing_helpers import connect_db
from pigazing_helpers.dcf_ast import date_string
from pigazing_helpers.settings_read import settings, installation_info


def list_calibration_fixes(obstory_id, utc_min, utc_max):
    """
    List all the calibration fixes for a particular observatory.

    :param obstory_id:
        The ID of the observatory we want to list calibration fixes for.
    :param utc_min:
        The start of the time period in which we should list calibration fixes (unix time).
    :param utc_max:
        The end of the time period in which we should list calibration fixes (unix time).
    :return:
        None
    """

    # Open connection to database
    [db0, conn] = connect_db.connect_db()

    # Start compiling list of calibration fixes
    calibration_fixes = []

    # Select observatory with calibration fits
    conn.execute("""
SELECT am1.stringValue AS barrel_parameters,
       am4.floatValue AS chi_squared, am5.stringValue AS point_count,
       o.obsTime AS time
FROM archive_observations o
INNER JOIN archive_metadata am1 ON o.uid = am1.observationId AND
    am1.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="calibration:lens_barrel_parameters")
INNER JOIN archive_metadata am4 ON o.uid = am4.observationId AND
    am4.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="calibration:chi_squared")
INNER JOIN archive_metadata am5 ON o.uid = am5.observationId AND
    am5.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="calibration:point_count")
WHERE
    o.observatory = (SELECT uid FROM archive_observatories WHERE publicId=%s) AND
    o.obsTime BETWEEN %s AND %s;
""", (obstory_id, utc_min, utc_max))
    results = conn.fetchall()

    for item in results:
        calibration_fixes.append({
            'time': item['time'],
            'average': False,
            'fit': item
        })

    # Select observation calibration fits
    conn.execute("""
SELECT am1.stringValue AS barrel_parameters,
       am3.floatValue AS chi_squared, am4.stringValue AS point_count,
       am1.time AS time
FROM archive_observatories o
INNER JOIN archive_metadata am1 ON o.uid = am1.observatory AND
    am1.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="calibration:lens_barrel_parameters")
LEFT OUTER JOIN archive_metadata am3 ON o.uid = am3.observatory AND am3.time=am1.time AND
    am3.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="calibration:chi_squared")
LEFT OUTER JOIN archive_metadata am4 ON o.uid = am4.observatory AND am4.time=am1.time AND
    am4.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="calibration:point_count")
WHERE
    o.publicId=%s AND
    am1.time BETWEEN %s AND %s;
""", (obstory_id, utc_min, utc_max))
    results = conn.fetchall()

    for item in results:
        calibration_fixes.append({
            'time': item['time'],
            'average': True,
            'fit': item
        })

    # Sort fixes by time
    calibration_fixes.sort(key=itemgetter('time'))

    # Display column headings
    print("""\
{:1s} {:16s} {:8s} {:8s} {:10s} {:12s} {:6s}\
""".format("", "Time", "barrelK1", "barrelK2", "barrelK3", "chi2", "points"))

    # Display fixes
    for item in calibration_fixes:
        # Deal with missing data
        if item['fit']['chi_squared'] is None:
            item['fit']['chi_squared'] = -1
        if item['fit']['point_count'] is None:
            item['fit']['point_count'] = "-"

        # Display calibration fix
        barrel_parameters = json.loads(item['fit']['barrel_parameters'])
        print("""\
{:s} {:16s} {:8.4f} {:8.4f} {:10.7f} {:12.9f} {:s} {:s}\
""".format("\n>" if item['average'] else " ",
           date_string(item['time']),
           barrel_parameters[2], barrel_parameters[3], barrel_parameters[4],
           item['fit']['chi_squared'], item['fit']['point_count'],
           "\n" if item['average'] else ""))

    # Clean up and exit
    return


# If we're called as a script, run the method list_calibration_fixes()
if __name__ == "__main__":
    # Read command-line arguments
    parser = argparse.ArgumentParser(description=__doc__)

    # By default, list the calibration of images taken over past 24 hours
    parser.add_argument('--utc-min', dest='utc_min', default=time.time() - 3600 * 24,
                        type=float,
                        help="Only list fixes recorded after the specified unix time")
    parser.add_argument('--utc-max', dest='utc_max', default=time.time(),
                        type=float,
                        help="Only list fixes recorded before the specified unix time")

    parser.add_argument('--observatory', dest='obstory_id', default=installation_info['observatoryId'],
                        help="ID of the observatory we are to list calibration fixes for")
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

    # List the calibrations derived from images
    list_calibration_fixes(obstory_id=args.obstory_id,
                           utc_min=args.utc_min,
                           utc_max=args.utc_max)
