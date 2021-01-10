#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# meteor_shower_identification.py
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
This script searches through all the moving objects detected within a given time span, and makes single-station
estimates of which meteor showers they belong to. For each meteor, a likelihood probability is calculated that it
belongs to each shower that is active on that day of the year. This probability is based on the ZHR of each shower,
and the degree of alignment of the meteor's path with the shower's radiant. A probability is also calculated for the
possibility that this is a sporadic meteor.

These models are then compared to determine the most likely meteor shower that the meteor belongs to.
"""

import argparse
import logging
import os
import time

from pigazing_helpers import connect_db, hardware_properties
from pigazing_helpers.dcf_ast import month_name, unix_from_jd, julian_day, date_string
from pigazing_helpers.obsarchive import obsarchive_db
from pigazing_helpers.settings_read import settings, installation_info
from pigazing_helpers.vendor import xmltodict


def longitude_offset(date_str: str, peak_longitude: float):
    """
    Return the solar longitude offset of the Sun's position on a date of the form "Jan 1" from peak_longitude.

    :param date_str:
        Date when we should calculate the solar longitude offset
    :param peak_longitude:
        Longitude of the Sun relative to which we calculate the offset on the day given by <date_str>, degrees
    :return:
        Longitude offset, degrees
    """

    # Decompose <date_str> into a month number and the day of the month
    month_str = date_str.split()[0]
    month_number = month_name.index(month_str) + 1
    day_number = int(date_str.split()[1])

    # Work out the unix time of noon on this day of the year in 2010
    unix_time_2010 = unix_from_jd(julian_day(year=2010, month=month_number, day=day_number, hour=12, minute=0, sec=0))
    equinox_2010 = unix_from_jd(julian_day(year=2010, month=3, day=20, hour=17, minute=30, sec=0))
    year_length = 86400 * 365.2524

    # Work out the separation of this unix time from the equinox in 2010 (when Sun is at zero longitude)
    longitude_of_date = (unix_time_2010 - equinox_2010) / year_length * 360  # degrees

    # Work out longitude offset, and ensure it is between -180 degrees and 180 degrees
    longitude_offset = longitude_of_date - peak_longitude
    while longitude_offset < -180:
        longitude_offset += 360
    while longitude_offset > 180:
        longitude_offset -= 360

    # Return result
    return longitude_offset


def read_shower_list():
    """
    Read the IMO working list of meteor showers from XML.

    :return:
        List of meteor showers
    """

    # Path to XML file
    xml_path = os.path.join(
        os.path.split(__file__)[0],
        "IMO_Working_Meteor_Shower_List.xml"
    )

    # Open XML file
    shower_list = xmltodict.parse(open(xml_path, "rb"))['meteor_shower_list']['shower']

    # Extract data
    output = []

    for item in shower_list:
        # Fix non-float values
        if item['IAU_code'] == 'ANT':
            continue
        if ('ZHR' not in item) or (item['ZHR'] is None):
            item['ZHR'] = 0

        # Create descriptor for this meteor shower
        shower_descriptor = {
            'IAU_code': item['IAU_code'],
            'name': item['name'],
            'peak': float(item['peak']),  # longitude
            'start': longitude_offset(item['start'], float(item['peak'])),
            'end': longitude_offset(item['end'], float(item['peak'])),
            'RA': float(item['RA']) * 12 / 180.,  # hours
            'Decl': float(item['DE']),  # degrees
            'v': float(item['V']),  # km/s
            'zhr': float(item['ZHR'])
        }

        # Append to list of showers
        logging.info(shower_descriptor)
        output.append(shower_descriptor)

    # Return output
    return output


def shower_determination(utc_min, utc_max):
    """
    Estimate the parent showers of all meteors observed between the unix times <utc_min> and <utc_max>.

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

    # Load list of meteor showers
    shower_list = read_shower_list()

    # Open connection to database
    [db0, conn] = connect_db.connect_db()

    # Open connection to image archive
    db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                           db_host=installation_info['mysqlHost'],
                                           db_user=installation_info['mysqlUser'],
                                           db_password=installation_info['mysqlPassword'],
                                           db_name=installation_info['mysqlDatabase'],
                                           obstory_id=installation_info['observatoryId'])

    logging.info("Starting meteor shower identification.")

    # Fetch source Id for data generated by this python script (used to record data provenance in the database)
    source_id = connect_db.fetch_source_id(c=conn, source_info=("astrometry.net", "astrometry.net", "astrometry.net"))
    db0.commit()

    # Count how many images we manage to successfully fit
    successful_fits = 0

    # Read properties of known lenses, which give us the default radial distortion models to assume for them
    hw = hardware_properties.HardwareProps(
        path=os.path.join(settings['pythonPath'], "..", "configuration_global", "camera_properties")
    )

    # Status update
    logging.info("Searching for meteors within period {} to {}".format(date_string(utc_min), date_string(utc_max)))

    # Search for meteors within this time period
    conn.execute("""
SELECT ao.obsTime, ao.publicId AS observationId, f.repositoryFname, am.stringValue AS path, l.publicId AS observatory
FROM archive_files f
INNER JOIN archive_observations ao ON f.observationId = ao.uid
INNER JOIN archive_observatories l ON ao.observatory = l.uid
INNER JOIN archive_metadata am ON f.uid = am.fileId AND
    am.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="pigazing:path")
INNER JOIN archive_metadata am2 ON ao.uid = am2.observationId AND
    am2.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="web:category")
WHERE ao.obsTime BETWEEN %s AND %s
    AND f.semanticType=(SELECT uid FROM archive_semanticTypes WHERE name="pigazing:movingObject/video")
    AND am2.stringValue = "Meteor"
ORDER BY ao.obsTime
""", (utc_min, utc_max))
    results = conn.fetchall()

    # Display logging list of the images we are going to work on
    logging.info("Estimating the parents of {:d} meteors.".format(len(results)))

    # Analyse each meteor in turn
    for item_index, item in enumerate(results):
        # Fetch observatory status at time of observation
        obstory_status = db.get_obstory_status(obstory_id=item['observatory'], time=item['obsTime'])
        if not obstory_status:
            logging.info("Aborting -- no observatory status available.")
            continue

        # Fetch properties of the lens being used at the time of the observation
        lens_name = obstory_status['lens']
        lens_props = hw.lens_data[lens_name]

    # Report how many fits we achieved
    logging.info("Total of {:d} meteors successfully identified.".format(successful_fits))

    # Clean up and exit
    db.commit()
    db.close_db()
    db0.commit()
    conn.close()
    db0.close()
    return


def flush_identifications(utc_min, utc_max):
    """
    Remove all meteor identifications within a specified time period.

    :param utc_min:
        The earliest time for which we are to flush shower data.
    :param utc_max:
        The latest time for which we are to flush shower data.
    :return:
        None
    """
    # Open connection to database
    [db0, conn] = connect_db.connect_db()

    # Delete observation metadata fields that start 'shower:*'
    conn.execute("""
DELETE m
FROM archive_metadata m
INNER JOIN archive_observations o ON m.observationId = o.uid
WHERE
    fieldId IN (SELECT uid FROM archive_metadataFields WHERE metaKey LIKE 'shower:%%') AND
    o.obsTime BETWEEN %s AND %s;
""", (utc_min, utc_max))

    # Commit changes to database
    db0.commit()
    conn.close()
    db0.close()


# If we're called as a script, run the function shower_determination()
if __name__ == "__main__":
    # Read command-line arguments
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stop-by', default=None, type=float,
                        dest='stop_by', help='The unix time when we need to exit, even if jobs are unfinished')

    # By default, categorise all meteors recorded since the beginning of time
    parser.add_argument('--utc-min', dest='utc_min', default=0,
                        type=float,
                        help="Only analyse meteors recorded after the specified unix time")
    parser.add_argument('--utc-max', dest='utc_max', default=time.time(),
                        type=float,
                        help="Only analyse meteors recorded before the specified unix time")

    parser.add_argument('--flush', dest='flush', action='store_true')
    parser.add_argument('--no-flush', dest='flush', action='store_false')
    parser.set_defaults(flush=False)
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
    # logger.info(__doc__.strip())

    # If flush option was specified, then delete all existing alignment information
    if args.flush:
        flush_identifications(utc_min=args.utc_min,
                              utc_max=args.utc_max)

    # Estimate the parentage of meteors
    shower_determination(utc_min=args.utc_min,
                         utc_max=args.utc_max)
