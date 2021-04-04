#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# worst_orientations.py
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
List the images which have the worst orientation fits
"""

import argparse
import json
import logging
import os
import time
from operator import itemgetter

from pigazing_helpers import connect_db
from pigazing_helpers.obsarchive import obsarchive_db
from pigazing_helpers.settings_read import settings, installation_info

from orientation_calculate import minimum_sky_clarity


def list_orientations(obstory_id, utc_min, utc_max):
    """
    List the worst orientation fits of a particular observatory within the time period between the unix times
    <utc_min> and <utc_max>.

    :param obstory_id:
        The ID of the observatory we want to determine the orientation for.
    :type obstory_id:
        str
    :param utc_min:
        The start of the time period in which we should determine the observatory's orientation (unix time).
    :type utc_min:
        float
    :param utc_max:
        The end of the time period in which we should determine the observatory's orientation (unix time).
    :type utc_max:
        float
    :return:
        None
    """

    # Open connection to database
    [db0, conn] = connect_db.connect_db()

    # Open connection to image archive
    db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                           db_host=installation_info['mysqlHost'],
                                           db_user=installation_info['mysqlUser'],
                                           db_password=installation_info['mysqlPassword'],
                                           db_name=installation_info['mysqlDatabase'],
                                           obstory_id=installation_info['observatoryId'])

    logging.info("Plotting camera alignment for <{}>".format(obstory_id))

    # Search for background-subtracted time lapse image with best sky clarity, and no existing orientation fit,
    # within this time period
    conn.execute("""
SELECT ao.obsTime, f.repositoryFname AS observationId,
       am.floatValue AS skyClarity, am2.stringValue AS fitQuality, am3.stringValue AS fitQualityToAverage
FROM archive_files f
INNER JOIN archive_observations ao on f.observationId = ao.uid
INNER JOIN archive_metadata am ON f.uid = am.fileId AND
    am.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="pigazing:skyClarity")
LEFT OUTER JOIN archive_metadata am2 ON ao.uid = am2.observationId AND
    am2.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="orientation:fit_quality")
LEFT OUTER JOIN archive_metadata am3 ON ao.uid = am3.observationId AND
    am3.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="orientation:fit_quality_to_daily")
WHERE ao.obsTime BETWEEN %s AND %s
    AND ao.observatory=(SELECT uid FROM archive_observatories WHERE publicId=%s)
    AND f.semanticType=(SELECT uid FROM archive_semanticTypes WHERE name="pigazing:timelapse/backgroundSubtracted")
    AND am.floatValue > %s
ORDER BY ao.obsTime
""", (utc_min, utc_max, obstory_id, minimum_sky_clarity))
    results = conn.fetchall()

    # Data filename
    filename = "/tmp/worst_orientations"

    # Loop over results
    data = []
    for item in results:
        utc = float(item['obsTime'])
        sky_clarity = float(item['skyClarity'])
        fit_quality = -99
        fit_quality_to_average = -99

        if item['fitQuality'] is not None:
            fit_quality = float(json.loads(item['fitQuality'])[0])

        if item['fitQualityToAverage'] is not None:
            fit_quality_to_average = float(json.loads(item['fitQualityToAverage'])[0])

        data.append({
            'uid': item['observationId'],
            'utc': utc,
            'sky_clarity': sky_clarity,
            'fit_quality': fit_quality,
            'fit_quality_to_average': fit_quality_to_average
        })

    # Sort on fit quality
    data.sort(key=itemgetter('fit_quality_to_average'))
    data.reverse()

    # Limit to 1000 worst points
    data = data[:1000]

    # Write to data file
    with open("{}.dat".format(filename), "w") as f:
        for item in data:
            f.write("{} {:6.1f} {:6.3f} {:6.3f}\n".
                    format(item['uid'], item['sky_clarity'],
                           item['fit_quality'], item['fit_quality_to_average']))

    # Close database handles
    db.close_db()
    conn.close()
    db0.close()
    return


# If we're called as a script, run the function orientation_calc()
if __name__ == "__main__":
    # Read command-line arguments
    parser = argparse.ArgumentParser(description=__doc__)

    # By default, study all images
    parser.add_argument('--utc-min', dest='utc_min', default=0,
                        type=float,
                        help="Only use images recorded after the specified unix time")
    parser.add_argument('--utc-max', dest='utc_max', default=time.time(),
                        type=float,
                        help="Only use images recorded before the specified unix time")

    parser.add_argument('--observatory', dest='obstory_id', default="cambridge-east-0",
                        help="ID of the observatory we are to calibrate")
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

    # List the worst orientation fits
    list_orientations(obstory_id=args.obstory_id,
                      utc_min=args.utc_min,
                      utc_max=args.utc_max)
