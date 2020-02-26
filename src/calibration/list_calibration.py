#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# list_calibration.py
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
List calibration fixes for a particular observatory
"""

import argparse
import logging
import os
import time
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
        The start of the time period in which we should list calibration fixes.
    :param utc_max:
        The end of the time period in which we should list calibration fixes.
    :return:
        None
    """

    # Open connection to database
    [db0, conn] = connect_db.connect_db()

    # Start compiling list of orientation fixes
    orientation_fixes = []

    # Select observations with orientation fits
    conn.execute("""
SELECT am1.floatValue AS barrel_a, am2.floatValue AS barrel_b, am3.floatValue AS barrel_c,
       am4.floatValue AS chi_squared, am5.floatValue AS point_count,
       o.obsTime AS time
FROM archive_observations o
INNER JOIN archive_metadata am1 ON o.uid = am1.observationId AND
    am1.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="calibration:lens_barrel_a")
INNER JOIN archive_metadata am2 ON o.uid = am2.observationId AND
    am2.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="calibration:lens_barrel_b")
INNER JOIN archive_metadata am3 ON o.uid = am3.observationId AND
    am3.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="calibration:lens_barrel_c")
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
        orientation_fixes.append({
            'time': item['time'],
            'average': False,
            'fit': item
        })

    # Sort fixes by time
    orientation_fixes.sort(key=itemgetter('time'))

    # Display column headings
    print("""\
{:1s} {:16s} {:7s} {:7s} {:7s} {:6s} {:6s}\
""".format("", "Time", "barrelA", "barrelB", "barrelC", "chi2", "points"))

    # Display fixes
    for item in orientation_fixes:
        print("""\
{:s} {:16s} {:7.2f} {:7.2f} {:7.2f} {:6.1f} {:6.1f} {:s}\
""".format("\n>" if item['average'] else " ",
           date_string(item['time']),
           item['fit']['barrel_a'], item['fit']['barrel_b'], item['fit']['barrel_c'],
           item['fit']['chi_squared'], item['fit']['point_count'],
           "\n" if item['average'] else ""))

    # Clean up and exit
    return


# If we're called as a script, run the method orientationCalc()
if __name__ == "__main__":
    # Read command-line arguments
    parser = argparse.ArgumentParser(description=__doc__)

    # By default, study images taken over past 24 hours
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

    # Calculate the orientation of images
    list_calibration_fixes(obstory_id=args.obstory_id,
                           utc_min=args.utc_min,
                           utc_max=args.utc_max)
