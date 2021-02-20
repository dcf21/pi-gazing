#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# satellite_identification.py
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
This script searches through all the moving objects detected within a given time span, and makes single-station
estimates of identity of each spacecraft observed.
"""

import argparse
import json
import logging
import os
import MySQLdb
import time
from math import pi
from operator import itemgetter

from pigazing_helpers import connect_db, hardware_properties
from pigazing_helpers.dcf_ast import date_string
from pigazing_helpers.gnomonic_project import inv_gnom_project, position_angle, ang_dist
from pigazing_helpers.obsarchive import obsarchive_model as mp, obsarchive_db
from pigazing_helpers.settings_read import settings, installation_info
from pigazing_helpers.sunset_times import get_zenith_position, ra_dec

def fetch_satellites(utc):
    """
    Fetch list of satellite orbital elements from InTheSky database, at specified time.

    :param utc:
        Time for which to return orbital elements (unix time).
    :type utc:
        float
    :return:
        List of dictionaries containing orbital elements
    """

    output = []

    # Open connection to database
    db = MySQLdb.connect(host=connect_db.db_host, user=connect_db.db_user, passwd=connect_db.db_passwd,
                         db="inthesky")
    c = db.cursor(cursorclass=MySQLdb.cursors.DictCursor)

    db.set_character_set('utf8mb4')
    c.execute('SET NAMES utf8mb4;')
    c.execute('SET CHARACTER SET utf8mb4;')
    c.execute('SET character_set_connection=utf8mb4;')

    # Close connection to database
    c.close()
    db.close()

    # Return results
    return output



def satellite_determination(utc_min, utc_max):
    """
    Estimate the identity of spacecraft observed between the unix times <utc_min> and <utc_max>.

    :param utc_min:
        The start of the time period in which we should determine the identity of spacecraft (unix time).
    :type utc_min:
        float
    :param utc_max:
        The end of the time period in which we should determine the identity of spacecraft (unix time).
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

    logging.info("Starting satellite identification.")

    # Count how many images we manage to successfully fit
    outcomes = {
        'successful_fits': 0,
        'error_records': 0,
        'rescued_records': 0,
        'insufficient_information': 0
    }

    # Read properties of known lenses, which give us the default radial distortion models to assume for them
    hw = hardware_properties.HardwareProps(
        path=os.path.join(settings['pythonPath'], "..", "configuration_global", "camera_properties")
    )

    # Status update
    logging.info("Searching for satellites within period {} to {}".format(date_string(utc_min), date_string(utc_max)))

    # Search for satellites within this time period
    conn.execute("""
SELECT ao.obsTime, ao.publicId AS observationId, f.repositoryFname, am.stringValue AS path, l.publicId AS observatory,
       am3.stringValue AS pathBezier, am4.floatValue AS duration, am5.floatValue AS detections
FROM archive_files f
INNER JOIN archive_observations ao ON f.observationId = ao.uid
INNER JOIN archive_observatories l ON ao.observatory = l.uid
INNER JOIN archive_metadata am ON f.uid = am.fileId AND
    am.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="pigazing:path")
INNER JOIN archive_metadata am2 ON ao.uid = am2.observationId AND
    am2.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="web:category")
INNER JOIN archive_metadata am3 ON f.uid = am3.fileId AND
    am3.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="pigazing:pathBezier")
INNER JOIN archive_metadata am4 ON f.uid = am4.fileId AND
    am4.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="pigazing:duration")
INNER JOIN archive_metadata am5 ON f.uid = am5.fileId AND
    am5.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="pigazing:detectionCount")
WHERE ao.obsTime BETWEEN %s AND %s
    AND f.semanticType=(SELECT uid FROM archive_semanticTypes WHERE name="pigazing:movingObject/video")
    AND am2.stringValue = "Satellite"
ORDER BY ao.obsTime
""", (utc_min, utc_max))
    results = conn.fetchall()

    # Display logging list of the images we are going to work on
    logging.info("Estimating the identity of {:d} spacecraft.".format(len(results)))

    # Analyse each spacecraft in turn
    for item_index, item in enumerate(results):
        # Fetch observatory's database record
        obstory_info = db.get_obstory_from_id(obstory_id=item['observatory'])

        # Fetch observatory status at time of observation
        obstory_status = db.get_obstory_status(obstory_id=item['observatory'], time=item['obsTime'])
        if not obstory_status:
            # We cannot identify spacecraft if we don't have observatory status
            logging.info("{date} [{obs}] -- No observatory status available".format(
                date=date_string(utc=item['obsTime']),
                obs=item['observationId']
            ))
            outcomes['insufficient_information'] += 1
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
            logging.info("{date} [{obs}] -- Orientation of camera unknown".format(
                date=date_string(utc=item['obsTime']),
                obs=item['observationId']
            ))
            outcomes['insufficient_information'] += 1
            continue

        # Look up size of camera sensor
        if 'camera_width' in obstory_status:
            orientation['pixel_width'] = obstory_status['camera_width']
            orientation['pixel_height'] = obstory_status['camera_height']
        else:
            # We cannot identify meteors if we don't know camera field of view
            logging.info("{date} [{obs}] -- Pixel dimensions of video stream could not be determined".format(
                date=date_string(utc=item['obsTime']),
                obs=item['observationId']
            ))
            outcomes['insufficient_information'] += 1
            continue

        # Get celestial coordinates of the local zenith
        ra_dec_zenith_at_epoch = get_zenith_position(latitude=obstory_info['latitude'],
                                                     longitude=obstory_info['longitude'],
                                                     utc=item['obsTime'])
        ra_zenith_at_epoch = ra_dec_zenith_at_epoch['ra']  # hours, epoch of observation
        dec_zenith_at_epoch = ra_dec_zenith_at_epoch['dec']  # degrees, epoch of observation

        # Calculate celestial coordinates of the centre of the field of view
        # hours / degrees, epoch of observation
        central_ra_at_epoch, central_dec_at_epoch = ra_dec(alt=orientation['altitude'],
                                                           az=orientation['azimuth'],
                                                           utc=item['obsTime'],
                                                           latitude=obstory_info['latitude'],
                                                           longitude=obstory_info['longitude']
                                                           )

        # Work out the position angle of the zenith, counterclockwise from north, as measured at centre of frame
        # degrees for north pole at epoch
        zenith_pa_at_epoch = position_angle(ra1=central_ra_at_epoch, dec1=central_dec_at_epoch,
                                            ra2=ra_zenith_at_epoch, dec2=dec_zenith_at_epoch)

        # Calculate the position angle of the north pole, clockwise from vertical, at the centre of the frame
        celestial_pa_at_epoch = zenith_pa_at_epoch - orientation['tilt']
        while celestial_pa_at_epoch < -180:
            celestial_pa_at_epoch += 360
        while celestial_pa_at_epoch > 180:
            celestial_pa_at_epoch -= 360

        # Read path of the moving object in pixel coordinates
        try:
            path_x_y = json.loads(item['path'])
        except json.decoder.JSONDecodeError:
            # Attempt JSON repair; sometimes JSON content gets truncated
            original_json = item['path']
            fixed_json = "],[".join(original_json.split("],[")[:-1]) + "]]"
            try:
                path_x_y = json.loads(fixed_json)

                logging.info("{date} [{obs}] -- RESCUE: In: {detections:.0f} / {duration:.1f} sec; "
                            "Rescued: {count:d} / {json_span:.1f} sec".format(
                   date=date_string(utc=item['obsTime']),
                   obs=item['observationId'],
                   detections=item['detections'],
                   duration=item['duration'],
                   count=len(path_x_y),
                   json_span=path_x_y[-1][3] - path_x_y[0][3]
                ))

                path_bezier = json.loads(item['pathBezier'])
                p = path_bezier[1]
                path_x_y.append([p[0], p[1], 0, p[2]])
                p = path_bezier[2]
                path_x_y.append([p[0], p[1], 0, p[2]])
                outcomes['rescued_records'] += 1

                logging.info("{date} [{obs}] -- Added Bezier points: "
                            "In: {detections:.0f} / {duration:.1f} sec; "
                            "Rescued: {count:d} / {json_span:.1f} sec".format(
                   date=date_string(utc=item['obsTime']),
                   obs=item['observationId'],
                   detections=item['detections'],
                   duration=item['duration'],
                   count=len(path_x_y),
                   json_span=path_x_y[-1][3] - path_x_y[0][3]
                ))
            except json.decoder.JSONDecodeError:
                logging.info("{date} [{obs}] -- !!! JSON error".format(
                    date=date_string(utc=item['obsTime']),
                    obs=item['observationId']
                ))
            outcomes['error_records'] += 1
            continue

        # Convert path of moving objects into RA / Dec (radians, at epoch of observation)
        path_len = len(path_x_y)
        path_ra_dec_at_epoch = []
        for pt_x, pt_y, pt_intensity, pt_utc in path_x_y:
            # Calculate celestial coordinates of the centre of the field of view
            # hours / degrees, epoch of observation
            instantaneous_central_ra_at_epoch, instantaneous_central_dec_at_epoch = ra_dec(
                alt=orientation['altitude'],
                az=orientation['azimuth'],
                utc=pt_utc,
                latitude=obstory_info['latitude'],
                longitude=obstory_info['longitude']
            )

            # Calculate RA / Dec of observed position, at observed time
            path_ra_dec_at_epoch.append(
                inv_gnom_project(ra0=instantaneous_central_ra_at_epoch * pi / 12,
                                 dec0=instantaneous_central_dec_at_epoch * pi / 180,
                                 size_x=orientation['pixel_width'],
                                 size_y=orientation['pixel_height'],
                                 scale_x=orientation['ang_width'] * pi / 180,
                                 scale_y=orientation['ang_height'] * pi / 180,
                                 x=pt_x, y=pt_y,
                                 pos_ang=celestial_pa_at_epoch * pi / 180,
                                 barrel_k1=lens_barrel_parameters[2],
                                 barrel_k2=lens_barrel_parameters[3],
                                 barrel_k3=lens_barrel_parameters[4]
                                 )
            )

        # Look up list of satellite orbital elements at the time of this sighting
        spacecraft_list = []

        # List of candidate showers this meteor might belong to
        candidate_satellites = fetch_satellites(utc=item['obsTime'])

        # Test for each candidate meteor shower in turn
        for spacecraft in spacecraft_list:
            pass

        # Add model possibility for null
        hourly_rate = 5
        likelihood = hourly_rate * (1. / 90.)  # Mean value of Gaussian in range 0-90 degs
        candidate_satellites.append({
            'name': "Unidentified",
            'likelihood': 1e-8,
            'offset': 0
        })

        # Renormalise likelihoods to sum to unity
        sum_likelihood = sum(shower['likelihood'] for shower in candidate_satellites)
        for shower in candidate_satellites:
            shower['likelihood'] *= 100 / sum_likelihood

        # Sort candidates by likelihood
        candidate_satellites.sort(key=itemgetter('likelihood'), reverse=True)

        # Report possibility meteor shower identifications
        logging.info("{date} [{obs}] -- {satellites}".format(
            date=date_string(utc=item['obsTime']),
            obs=item['observationId'],
            satellites=", ".join([
                "{} {:.1f}% ({:.1f} deg offset)".format(shower['name'], shower['likelihood'], shower['offset'])
                for shower in candidate_satellites
            ])
        ))

        # Identify most likely satellite
        most_likely_satellite = candidate_satellites[0]['name']

        # Store satellite identification
        user = settings['pigazingUser']
        timestamp = time.time()
        db.set_observation_metadata(user_id=user, observation_id=item['observationId'], utc=timestamp,
                                    meta=mp.Meta(key="satellite:name", value=most_likely_satellite))
        db.set_observation_metadata(user_id=user, observation_id=item['observationId'], utc=timestamp,
                                    meta=mp.Meta(key="satellite:offset", value=candidate_satellites[0]['offset']))
        db.set_observation_metadata(user_id=user, observation_id=item['observationId'], utc=timestamp,
                                    meta=mp.Meta(key="satellite:path_length",
                                                 value=ang_dist(ra0=path_ra_dec_at_epoch[0][0],
                                                                dec0=path_ra_dec_at_epoch[0][1],
                                                                ra1=path_ra_dec_at_epoch[-1][0],
                                                                dec1=path_ra_dec_at_epoch[-1][0]
                                                                ) * 180 / pi
                                                 ))
        db.set_observation_metadata(user_id=user, observation_id=item['observationId'], utc=timestamp,
                                    meta=mp.Meta(key="satellite:path_ra_dec",
                                                 value="[[{:.3f},{:.3f}],[{:.3f},{:.3f}],[{:.3f},{:.3f}]]".format(
                                                     path_ra_dec_at_epoch[0][0] * 12 / pi,
                                                     path_ra_dec_at_epoch[0][1] * 180 / pi,
                                                     path_ra_dec_at_epoch[int(path_len / 2)][0] * 12 / pi,
                                                     path_ra_dec_at_epoch[int(path_len / 2)][1] * 180 / pi,
                                                     path_ra_dec_at_epoch[-1][0] * 12 / pi,
                                                     path_ra_dec_at_epoch[-1][1] * 180 / pi,
                                                 )
                                                 ))

        # Meteor successfully identified
        outcomes['successful_fits'] += 1

    # Report how many fits we achieved
    logging.info("{:d} satellites successfully identified.".format(outcomes['successful_fits']))
    logging.info("{:d} malformed database records.".format(outcomes['error_records']))
    logging.info("{:d} rescued database records.".format(outcomes['rescued_records']))
    logging.info("{:d} satellites with incomplete data.".format(outcomes['insufficient_information']))

    # Clean up and exit
    db.commit()
    db.close_db()
    db0.commit()
    conn.close()
    db0.close()
    return


def flush_identifications(utc_min, utc_max):
    """
    Remove all satellite identifications within a specified time period.

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
    fieldId IN (SELECT uid FROM archive_metadataFields WHERE metaKey LIKE 'satellite:%%') AND
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

    # By default, categorise all meteors recorded since the beginning of time
    parser.add_argument('--utc-min', dest='utc_min', default=0,
                        type=float,
                        help="Only analyse satellites recorded after the specified unix time")
    parser.add_argument('--utc-max', dest='utc_max', default=time.time(),
                        type=float,
                        help="Only analyse satellites recorded before the specified unix time")

    parser.add_argument('--flush', dest='flush', action='store_true')
    parser.add_argument('--no-flush', dest='flush', action='store_false')
    parser.set_defaults(flush=True)
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
    satellite_determination(utc_min=args.utc_min,
                            utc_max=args.utc_max)
