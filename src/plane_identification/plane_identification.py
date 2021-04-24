#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# plane_identification.py
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
estimates of identity of each plane observed.
"""

import argparse
import logging
import os
import time
import json
from math import pi, exp, hypot
from operator import itemgetter

import MySQLdb
import numpy as np
import scipy.optimize
from pigazing_helpers import connect_db
from pigazing_helpers.dcf_ast import date_string
from pigazing_helpers.gnomonic_project import ang_dist
from pigazing_helpers.obsarchive import obsarchive_model as mp, obsarchive_db
from pigazing_helpers.path_projection import PathProjection
from pigazing_helpers.settings_read import settings, installation_info
from pigazing_helpers.vector_algebra import Point
from scipy.interpolate import interp1d

# Constants
feet = 0.3048  # Aircraft altitudes are given in feet

# Global search settings
global_settings = {
    'max_angular_mismatch': 15,  # Maximum offset of a plane from observed position, deg
    'max_mean_angular_mismatch': 10,  # Maximum mean offset of a plane from observed position, deg
    'max_clock_offset': 20,  # Maximum time offset of plane trajectory
}


def fetch_aircraft_data(hex_ident):
    """
    Fetch data about a plane, based on its hex ident.

    :param hex_ident:
        Plane identifier
    :return:
        Dictionary of information about plane
    """

    # Open connection to database
    db = MySQLdb.connect(host=connect_db.db_host, user=connect_db.db_user, passwd=connect_db.db_passwd,
                         db="adsb")
    c = db.cursor(cursorclass=MySQLdb.cursors.DictCursor)

    db.set_character_set('utf8mb4')
    c.execute('SET NAMES utf8mb4;')
    c.execute('SET CHARACTER SET utf8mb4;')
    c.execute('SET character_set_connection=utf8mb4;')

    # Look up aircraft
    c.execute("""
SELECT * FROM aircraft_hex_codes WHERE hex_ident=%s;
""", (hex_ident,))
    aircraft = c.fetchall()

    # If we got no matches, return an empty dictionary
    if len(aircraft) > 0:
        result = dict(aircraft[0])
    else:
        result = {}

    return result


def fetch_planes_from_adsb(utc):
    """
    Fetch list of planes from ADS-B database, at specified time.

    :param utc:
        Time for which to return aircraft (unix time).
    :type utc:
        float
    :return:
        List of dictionaries containing aircraft tracks
    """

    # Open connection to database
    db = MySQLdb.connect(host=connect_db.db_host, user=connect_db.db_user, passwd=connect_db.db_passwd,
                         db="adsb")
    c = db.cursor(cursorclass=MySQLdb.cursors.DictCursor)

    db.set_character_set('utf8mb4')
    c.execute('SET NAMES utf8mb4;')
    c.execute('SET CHARACTER SET utf8mb4;')
    c.execute('SET character_set_connection=utf8mb4;')

    # Look up aircraft seen around queried time
    search_window = 300
    c.execute("""
SELECT call_sign, hex_ident
FROM adsb_squitters s
WHERE s.generated_timestamp BETWEEN %s AND %s
GROUP BY call_sign, hex_ident;
""", (utc - search_window, utc + search_window))
    aircraft_list = c.fetchall()

    # Fetch track for each aircraft
    output = []
    for aircraft in aircraft_list:
        c.execute("""
SELECT generated_timestamp, lat, lon, altitude, ground_speed
FROM adsb_squitters s
WHERE s.call_sign=%s AND s.hex_ident=%s AND s.lat IS NOT NULL AND s.generated_timestamp BETWEEN %s AND %s
ORDER BY s.generated_timestamp;
""", (aircraft['call_sign'], aircraft['hex_ident'], utc - search_window, utc + search_window))
        track_list = c.fetchall()

        track = [{
            'utc': point['generated_timestamp'],
            'lat': point['lat'],
            'lon': point['lon'],
            'altitude': point['altitude'],
            'ground_speed': point['ground_speed']
        }
            for point in track_list
        ]

        # Linearly interpolate track
        interpolate_lat = interp1d(x=np.asarray([i['utc'] for i in track]),
                                   y=np.asarray([i['lat'] for i in track]),
                                   kind='linear')
        interpolate_lon = interp1d(x=np.asarray([i['utc'] for i in track]),
                                   y=np.asarray([i['lon'] for i in track]),
                                   kind='linear')
        interpolate_alt = interp1d(x=np.asarray([i['utc'] for i in track]),
                                   y=np.asarray([i['altitude'] for i in track]),
                                   kind='linear')
        interpolate_spd = interp1d(x=np.asarray([i['utc'] for i in track]),
                                   y=np.asarray([i['ground_speed'] for i in track]),
                                   kind='linear')

        output.append({
            'call_sign': aircraft['call_sign'],
            'hex_ident': aircraft['hex_ident'],
            'track': track,
            'interpolate_lat': interpolate_lat,
            'interpolate_lon': interpolate_lon,
            'interpolate_alt': interpolate_alt,
            'interpolate_spd': interpolate_spd
        })

    # Close connection to database
    c.close()
    db.close()

    # Return results
    return output


def path_interpolate(aircraft: dict, utc: float):
    """
    Interpolate the position of a plane at a particular time.

    :param aircraft:
        A dictionary of database data about an aircraft.
    :type aircraft:
        dict
    :param utc:
        The time at which to interpolate the aircraft's position.
    :type utc:
        float
    :return:
        Position at the interpolated timestamp.
    """

    track = aircraft['track']
    track_length = len(track)

    # Is time point outside time span of the track?
    if (utc < track[0]['utc']) or (utc > track[-1]['utc']):
        return None

    # Linearly interpolate trajectory
    output = {
        'utc': utc,
        'lat': aircraft['interpolate_lat'](utc),
        'lon': aircraft['interpolate_lon'](utc),
        'altitude': aircraft['interpolate_alt'](utc),
        'ground_speed': aircraft['interpolate_spd'](utc),
    }

    # Return interpolated track point
    return output


def plane_determination(utc_min, utc_max, source):
    """
    Estimate the identity of aircraft observed between the unix times <utc_min> and <utc_max>.

    :param utc_min:
        The start of the time period in which we should determine the identity of aircraft (unix time).
    :type utc_min:
        float
    :param utc_max:
        The end of the time period in which we should determine the identity of aircraft (unix time).
    :type utc_max:
        float
    :param source:
        The source we should use for plane trajectories. Either 'adsb' or 'fr24'.
    :type source:
        str
    :return:
        None
    """

    # Open connection to image archive
    db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                           db_host=installation_info['mysqlHost'],
                                           db_user=installation_info['mysqlUser'],
                                           db_password=installation_info['mysqlPassword'],
                                           db_name=installation_info['mysqlDatabase'],
                                           obstory_id=installation_info['observatoryId'])

    logging.info("Starting aircraft identification.")

    # Count how many images we manage to successfully fit
    outcomes = {
        'successful_fits': 0,
        'unsuccessful_fits': 0,
        'error_records': 0,
        'rescued_records': 0,
        'insufficient_information': 0
    }

    # Status update
    logging.info("Searching for aircraft within period {} to {}".format(date_string(utc_min), date_string(utc_max)))

    # Open connection to database
    [db0, conn] = connect_db.connect_db()

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
    AND am2.stringValue = "Plane"
ORDER BY ao.obsTime
""", (utc_min, utc_max))
    results = conn.fetchall()

    # Close connection to database
    conn.close()
    db0.close()

    # Display logging list of the images we are going to work on
    logging.info("Estimating the identity of {:d} aircraft.".format(len(results)))

    # Analyse each aircraft in turn
    for item_index, item in enumerate(results):
        # Make ID string to prefix to all logging messages about this event
        logging_prefix = "{date} [{obs}]".format(
            date=date_string(utc=item['obsTime']),
            obs=item['observationId']
        )

        # Project path from (x,y) coordinates into (RA, Dec)
        projector = PathProjection(
            db=db,
            obstory_id=item['observatory'],
            time=item['obsTime'],
            logging_prefix=logging_prefix
        )

        path_x_y, path_ra_dec_at_epoch, path_alt_az, sight_line_list = projector.ra_dec_from_x_y(
            path_json=item['path'],
            path_bezier_json=item['pathBezier'],
            detections=item['detections'],
            duration=item['duration']
        )

        # Check for error
        if projector.error is not None:
            if projector.error in outcomes:
                outcomes[projector.error] += 1
            continue

        # Check for notifications
        for notification in projector.notifications:
            if notification in outcomes:
                outcomes[notification] += 1

        # Check number of points in path
        path_len = len(path_x_y)

        # Look up list of aircraft tracks at the time of this sighting
        if source == 'adsb':
            aircraft_list = fetch_planes_from_adsb(utc=item['obsTime'])
        else:
            raise ValueError("Unknown source <{}>".format(source))

        # List of aircraft this moving object might be
        candidate_aircraft = []

        # Check that we found a list of aircraft
        if aircraft_list is None:
            logging.info("{date} [{obs}] -- No aircraft records found.".format(
                date=date_string(utc=item['obsTime']),
                obs=item['observationId']
            ))
            outcomes['insufficient_information'] += 1
            continue

        # Logging message about how many aircraft we're testing
        # logging.info("{date} [{obs}] -- Matching against {count:7d} aircraft.".format(
        #     date=date_string(utc=item['obsTime']),
        #     obs=item['observationId'],
        #     count=len(aircraft_list)
        # ))

        # Test for each candidate aircraft in turn
        for aircraft in aircraft_list:
            # Fetch aircraft position at each time point along trajectory
            ang_mismatch_list = []
            distance_list = []
            altitude_list = []

            def aircraft_angular_offset(index, clock_offset):
                # Fetch observed position of object at this time point
                pt_utc = sight_line_list[index]['utc']
                observatory_position = sight_line_list[index]['obs_position']
                observed_sight_line = sight_line_list[index]['line'].direction

                # Project position of this aircraft in space at this time point
                aircraft_position = path_interpolate(aircraft=aircraft,
                                                     utc=pt_utc + clock_offset)
                if aircraft_position is None:
                    return np.nan, np.nan

                # Convert position to Cartesian coordinates
                aircraft_point = Point.from_lat_lng(lat=aircraft_position['lat'],
                                                    lng=aircraft_position['lon'],
                                                    alt=aircraft_position['altitude'] * feet,
                                                    utc=None)

                # Work out offset of plane's position from observed moving object
                aircraft_sight_line = aircraft_point.to_vector() - observatory_position.to_vector()
                angular_offset = aircraft_sight_line.angle_with(other=observed_sight_line)  # degrees
                distance = abs(aircraft_sight_line)
                altitude = aircraft_position['altitude'] * feet

                return angular_offset, distance, altitude

            def time_offset_objective(p):
                """
                Objective function that we minimise in order to find the best fit clock offset between the observed
                and model paths.

                :param p:
                    Vector with a single component: the clock offset
                :return:
                    Metric to minimise
                """

                # Turn input parameters into a time offset
                clock_offset = p[0]

                # Look up angular offset
                ang_mismatch, distance, altitude = aircraft_angular_offset(index=0, clock_offset=clock_offset)

                # Return metric to minimise
                return ang_mismatch * exp(clock_offset / 8)

            # Work out the optimum time offset between the plane's path and the observed path
            # See <http://www.scipy-lectures.org/advanced/mathematical_optimization/>
            # for more information about how this works
            parameters_initial = [0]
            parameters_optimised = scipy.optimize.minimize(time_offset_objective,
                                                           np.asarray(parameters_initial),
                                                           options={'disp': False, 'maxiter': 100}
                                                           ).x

            # Construct best-fit linear trajectory for best-fitting parameters
            clock_offset = float(parameters_optimised[0])

            # Check clock offset is reasonable
            if abs(clock_offset) > global_settings['max_clock_offset']:
                continue

            # Measure the offset between the plane's position and the observed position at each time point
            for index in range(path_len):
                # Look up angular mismatch at this time point
                ang_mismatch, distance, altitude = aircraft_angular_offset(index=index, clock_offset=clock_offset)

                # Keep list of the offsets at each recorded time point along the trajectory
                ang_mismatch_list.append(ang_mismatch)
                distance_list.append(distance)
                altitude_list.append(altitude)

            # Consider adding this plane to list of candidates
            mean_ang_mismatch = np.mean(np.asarray(ang_mismatch_list))  # degrees
            distance_mean = np.mean(np.asarray(distance_list))  # metres
            altitude_mean = np.mean(np.asarray(altitude_list))  # metres

            if mean_ang_mismatch < global_settings['max_mean_angular_mismatch']:
                start_time = sight_line_list[0]['utc']
                end_time = sight_line_list[-1]['utc']
                start_point = path_interpolate(aircraft=aircraft,
                                                     utc=start_time + clock_offset)
                end_point = path_interpolate(aircraft=aircraft,
                                               utc=end_time + clock_offset)
                candidate_aircraft.append({
                    'call_sign': aircraft['call_sign'],  # string
                    'hex_ident': aircraft['hex_ident'],  # string
                    'distance': distance_mean / 1e3,  # km
                    'altitude': altitude_mean / 1e3,  # km
                    'clock_offset': clock_offset,  # seconds
                    'offset': mean_ang_mismatch,  # degrees
                    'start_point': start_point,
                    'end_point': end_point
                })

        # Add model possibility for null aircraft
        if len(candidate_aircraft) == 0:
            candidate_aircraft.append({
                'call_sign': "Unidentified",
                'hex_ident': "Unidentified",
                'distance': 0,
                'altitude': 0,
                'clock_offset': 0,
                'offset': 0,
                'start_point': None,
                'end_point': None
            })

        # Sort candidates by score
        for candidate in candidate_aircraft:
            candidate['score'] = hypot(
                candidate['offset'],
                candidate['clock_offset'],
            )
        candidate_aircraft.sort(key=itemgetter('score'))

        # Report possible satellite identifications
        logging.info("{prefix} -- {aircraft}".format(
            prefix=logging_prefix,
            aircraft=", ".join([
                "{} ({:.1f} deg offset; clock offset {:.1f} sec; distance {:.1f} km)".format(aircraft['call_sign'],
                                                                                             aircraft['offset'],
                                                                                             aircraft['clock_offset'],
                                                                                             aircraft['distance'])
                for aircraft in candidate_aircraft
            ])
        ))

        # Identify most likely aircraft
        most_likely_aircraft = candidate_aircraft[0]

        # Fetch extra information about plane
        plane_info = fetch_aircraft_data(hex_ident=most_likely_aircraft['hex_ident'])

        # Store aircraft identification
        user = settings['pigazingUser']
        timestamp = time.time()
        db.set_observation_metadata(user_id=user, observation_id=item['observationId'], utc=timestamp,
                                    meta=mp.Meta(key="plane:call_sign", value=most_likely_aircraft['call_sign']))
        db.set_observation_metadata(user_id=user, observation_id=item['observationId'], utc=timestamp,
                                    meta=mp.Meta(key="plane:hex_ident", value=most_likely_aircraft['hex_ident']))
        db.set_observation_metadata(user_id=user, observation_id=item['observationId'], utc=timestamp,
                                    meta=mp.Meta(key="plane:clock_offset",
                                                 value=most_likely_aircraft['clock_offset']))
        db.set_observation_metadata(user_id=user, observation_id=item['observationId'], utc=timestamp,
                                    meta=mp.Meta(key="plane:angular_offset", value=most_likely_aircraft['offset']))
        db.set_observation_metadata(user_id=user, observation_id=item['observationId'], utc=timestamp,
                                    meta=mp.Meta(key="plane:distance", value=most_likely_aircraft['distance']))
        db.set_observation_metadata(user_id=user, observation_id=item['observationId'], utc=timestamp,
                                    meta=mp.Meta(key="plane:mean_altitude", value=most_likely_aircraft['altitude']))
        db.set_observation_metadata(user_id=user, observation_id=item['observationId'], utc=timestamp,
                                    meta=mp.Meta(key="plane:path",
                                                 value=json.dumps([most_likely_aircraft['start_point'],
                                                                   most_likely_aircraft['end_point']])))
        db.set_observation_metadata(user_id=user, observation_id=item['observationId'], utc=timestamp,
                                    meta=mp.Meta(key="plane:path_length",
                                                 value=ang_dist(ra0=path_ra_dec_at_epoch[0][0],
                                                                dec0=path_ra_dec_at_epoch[0][1],
                                                                ra1=path_ra_dec_at_epoch[-1][0],
                                                                dec1=path_ra_dec_at_epoch[-1][1]
                                                                ) * 180 / pi
                                                 ))

        aircraft_operator = ""
        if 'operator' in plane_info and plane_info['operator']:
            aircraft_operator = plane_info['operator']
        elif 'owner' in plane_info and plane_info['owner']:
            aircraft_operator = plane_info['owner']

        db.set_observation_metadata(user_id=user, observation_id=item['observationId'], utc=timestamp,
                                    meta=mp.Meta(key="plane:operator", value=aircraft_operator))
        db.set_observation_metadata(user_id=user, observation_id=item['observationId'], utc=timestamp,
                                    meta=mp.Meta(key="plane:model", value=plane_info.get('model', '')))
        db.set_observation_metadata(user_id=user, observation_id=item['observationId'], utc=timestamp,
                                    meta=mp.Meta(key="plane:manufacturer",
                                                 value=plane_info.get('manufacturername', '')))

        # Aircraft successfully identified
        if most_likely_aircraft['call_sign'] == "Unidentified":
            outcomes['unsuccessful_fits'] += 1
        else:
            outcomes['successful_fits'] += 1

        # Update database
        db.commit()

    # Report how many fits we achieved
    logging.info("{:d} aircraft successfully identified.".format(outcomes['successful_fits']))
    logging.info("{:d} aircraft not identified.".format(outcomes['unsuccessful_fits']))
    logging.info("{:d} malformed database records.".format(outcomes['error_records']))
    logging.info("{:d} rescued database records.".format(outcomes['rescued_records']))
    logging.info("{:d} aircraft with incomplete data.".format(outcomes['insufficient_information']))

    # Clean up and exit
    db.commit()
    db.close_db()
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

    # Delete observation metadata fields that start 'plane:*'
    conn.execute("""
DELETE m
FROM archive_metadata m
INNER JOIN archive_observations o ON m.observationId = o.uid
WHERE
    fieldId IN (SELECT uid FROM archive_metadataFields WHERE metaKey LIKE 'plane:%%') AND
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

    # By default, categorise all aircraft recorded since the beginning of time
    parser.add_argument('--utc-min', dest='utc_min', default=0,
                        type=float,
                        help="Only analyse aircraft recorded after the specified unix time")
    parser.add_argument('--utc-max', dest='utc_max', default=time.time(),
                        type=float,
                        help="Only analyse aircraft recorded before the specified unix time")
    parser.add_argument('--source', dest='source', default='adsb',
                        type=str,
                        help="Source to use for plane paths ('adsb' or 'fr24')")

    parser.add_argument('--flush', dest='flush', action='store_true')
    parser.add_argument('--no-flush', dest='flush', action='store_false')
    parser.set_defaults(flush=True)
    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(level=logging.INFO,
                        format='[%(asctime)s] %(levelname)s:%(filename)28s:%(message)s',
                        datefmt='%d/%m/%Y %H:%M:%S',
                        handlers=[
                            logging.FileHandler(os.path.join(settings['pythonPath'], "../datadir/pigazing.log")),
                            logging.StreamHandler()
                        ])
    logger = logging.getLogger(__name__)
    # logger.info(__doc__.strip())

    # If flush option was specified, then delete all existing satellite identifications
    if args.flush:
        flush_identifications(utc_min=args.utc_min,
                              utc_max=args.utc_max)

    # Estimate the identity of aircraft
    plane_determination(utc_min=args.utc_min,
                        utc_max=args.utc_max,
                        source=args.source)
