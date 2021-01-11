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
import json
import logging
import os
import time
from math import pi, sin

from pigazing_helpers import connect_db, hardware_properties
from pigazing_helpers.dcf_ast import month_name, unix_from_jd, julian_day, date_string
from pigazing_helpers.gnomonic_project import inv_gnom_project, position_angle, ang_dist
from pigazing_helpers.obsarchive import obsarchive_db
from pigazing_helpers.settings_read import settings, installation_info
from pigazing_helpers.sunset_times import alt_az, get_zenith_position, sun_pos, ra_dec
from pigazing_helpers.vector_algebra import Vector
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
        # Fetch observatory's database record
        obstory_info = db.get_obstory_from_id(obstory_id=item['observatory'])

        # Fetch observatory status at time of observation
        obstory_status = db.get_obstory_status(obstory_id=item['observatory'], time=item['obsTime'])
        if not obstory_status:
            logging.info("Aborting -- no observatory status available.")
            continue

        # Fetch properties of the lens being used at the time of the observation
        lens_name = obstory_status['lens']
        lens_props = hw.lens_data[lens_name]

        # Look up radial distortion model for the lens we are using
        lens_barrel_parameters = obstory_status.get('calibration:lens_barrel_parameters', lens_props.barrel_parameters)
        if isinstance(lens_barrel_parameters, str):
            lens_barrel_parameters = json.loads(lens_barrel_parameters)

        # Look up orientation of the camera
        if 'orientation:altitude' in obstory_status:
            orientation = {
                'altitude': obstory_status['orientation:altitude'],
                'azimuth': obstory_status['orientation:azimuth'],
                'pa': obstory_status['orientation:pa'],
                'tilt': obstory_status['orientation:tilt'],
                'ang_width': obstory_status['orientation:width_x_field'],
                'ang_height': obstory_status['orientation:width_y_field'],
                'orientation_uncertainty': obstory_status['orientation:uncertainty'],
                'pixel_width': None,
                'pixel_height': None
            }
        else:
            # We cannot identify meteors if we don't know which direction camera is pointing
            logging.info("Orientation of camera unknown")
            continue

        # Look up size of camera sensor
        if 'camera_width' in obstory_status:
            orientation['pixel_width'] = obstory_status['camera_width']
            orientation['pixel_height'] = obstory_status['camera_height']
        else:
            # We cannot identify meteors if we don't know camera field of view
            logging.info("Pixel dimensions of video stream could not be determined")
            continue

        # Get celestial coordinates of the local zenith
        ra_dec_zenith = get_zenith_position(latitude=obstory_info['latitude'],
                                            longitude=obstory_info['longitude'],
                                            utc=item['obsTime'])
        ra_zenith = ra_dec_zenith['ra']
        dec_zenith = ra_dec_zenith['dec']

        # Calculate celestial coordinates of the centre of the field of view
        central_ra, central_dec = ra_dec(alt=orientation['altitude'],
                                         az=orientation['azimuth'],
                                         utc=item['obsTime'],
                                         latitude=obstory_info['latitude'],
                                         longitude=obstory_info['longitude']
                                         )

        # Work out the position angle of the zenith, counterclockwise from north, as measured at centre of frame
        zenith_pa = position_angle(ra1=central_ra, dec1=central_dec, ra2=ra_zenith, dec2=dec_zenith)

        # Calculate the position angle of the north pole, clockwise from vertical, at the centre of the frame
        celestial_pa = zenith_pa - orientation['tilt']
        while celestial_pa < -180:
            celestial_pa += 360
        while celestial_pa > 180:
            celestial_pa -= 360

        # List of candidate showers this meteor might belong to
        candidate_showers = []

        # Test for each candidate meteor shower in turn
        for shower in shower_list:
            # Work out alt-az of the shower's radiant using known location of camera. Fits returned in degrees.
            alt_az_pos = alt_az(ra=shower['RA'], dec=shower['Decl'],
                                utc=item['obsTime'],
                                latitude=obstory_info['latitude'], longitude=obstory_info['longitude'])

            # Work out position of the Sun
            sun_ra, sun_dec = sun_pos(utc=item['obsTime'])

            # Offset from peak of shower
            year = 365.2524
            peak_offset = (sun_ra * 180 / 12. - shower['peak']) * year / 360  # days
            while peak_offset < -year / 2:
                peak_offset += year
            while peak_offset > year / 2:
                peak_offset -= year

            start_offset = peak_offset + shower['start'] - 4
            end_offset = peak_offset + shower['end'] + 4

            # Estimate ZHR of shower at the time the meteor was observed
            zhr = 0
            if abs(peak_offset) < 2:
                zhr = shower['zhr']  # Shower is within 2 days of maximum; use quoted peak ZHR value
            if start_offset < 0 < end_offset:
                zhr = max(zhr, 5)  # Shower is not at peak, but is active; assume ZHR=5

            # Correct hourly rate for the altitude of the shower radiant
            hourly_rate = zhr * sin(alt_az_pos[0] * pi / 180)

            # If hourly rate is zero, this shower is not active
            if hourly_rate <= 0:
                # logging.info("Meteor shower <{}> has zero rate".format(shower['name']))
                continue

            # Work out path of meteor in RA, Dec (radians)
            path_x_y = json.loads(item['path'])
            path_ra_dec = [inv_gnom_project(ra0=central_ra * pi / 12, dec0=central_dec * pi / 180,
                                            size_x=orientation['pixel_width'],
                                            size_y=orientation['pixel_height'],
                                            scale_x=orientation['ang_width'] * pi / 180,
                                            scale_y=orientation['ang_height'] * pi / 180,
                                            x=pt[0], y=pt[1],
                                            pos_ang=celestial_pa * pi / 180,
                                            barrel_k1=lens_barrel_parameters[2],
                                            barrel_k2=lens_barrel_parameters[3],
                                            barrel_k3=lens_barrel_parameters[4]
                                            )
                           for pt in path_x_y]

            # Work out angular distance of meteor from radiant (radians)
            path_radiant_sep = [ang_dist(ra0=pt[0], dec0=pt[1],
                                         ra1=shower['RA'] * pi / 12, dec1=shower['Decl'] * pi / 180)
                                for pt in path_ra_dec]
            change_in_radiant_dist = path_radiant_sep[-1] - path_radiant_sep[0]  # radians

            # Convert path to Cartesian coordinates on a unit sphere
            path_cartesian = [Vector.from_ra_dec(ra=ra * 12 / pi, dec=dec * 180 / pi) for ra, dec in path_ra_dec]

            # Work out cross product of first and last point, which is normal to path of meteors
            first = path_cartesian[0]
            last = path_cartesian[-1]
            path_normal = first.cross_product(last)

            # Work out angle of path normal to meteor shower radiant
            radiant_cartesian = Vector.from_ra_dec(ra=shower['RA'], dec=shower['Decl'])
            theta = path_normal.angle_with(radiant_cartesian)  # degrees

            if theta > 90:
                theta = 180 - theta

            # What is the angular separation of the meteor's path's closest approach to the shower radiant?
            radiant_angle = 90 - theta

            # Store information about the likelihood this meteor belongs to this shower
            candidate_showers.append({
                'name': shower['name'],
                'radiant_angle': radiant_angle,
                'change_radiant_dist': change_in_radiant_dist,
                'shower_rate': hourly_rate
            })

        # Report possibility meteor shower identifications
        logging.info("{date} -- {showers}".format(
            date=date_string(utc=item['obsTime']),
            showers=json.dumps(candidate_showers)
        ))

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
