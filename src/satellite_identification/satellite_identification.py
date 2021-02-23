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
import logging
import os
import time
from math import pi
from operator import itemgetter

import MySQLdb
from pigazing_helpers import connect_db, hardware_properties
from pigazing_helpers.dcf_ast import date_string, jd_from_unix
from pigazing_helpers.gnomonic_project import ang_dist
from pigazing_helpers.obsarchive import obsarchive_model as mp, obsarchive_db
from pigazing_helpers.path_projection import PathProjection
from pigazing_helpers.settings_read import settings, installation_info
from sgp4.api import Satrec, WGS72


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

    # Open connection to database
    db = MySQLdb.connect(host=connect_db.db_host, user=connect_db.db_user, passwd=connect_db.db_passwd,
                         db="inthesky")
    c = db.cursor(cursorclass=MySQLdb.cursors.DictCursor)

    db.set_character_set('utf8mb4')
    c.execute('SET NAMES utf8mb4;')
    c.execute('SET CHARACTER SET utf8mb4;')
    c.execute('SET character_set_connection=utf8mb4;')

    # Look up the closest epoch which exists in the database
    c.execute("""
SELECT uid, epoch
FROM inthesky_spacecraft_epochs WHERE epoch BETWEEN %s AND %s
ORDER BY ABS(epoch-%s) LIMIT 1;
""", (utc - 86400 * 7, utc + 86400 * 7, utc))
    epoch_info = c.fetchall()

    # Check that we found an epoch
    if len(epoch_info) == 0:
        return None

    # Fetch list of satellites
    c.execute("""
SELECT o.noradId,epoch,incl,ecc,RAasc,argPeri,meanAnom,meanMotion,mag,bStar,meanMotionDot,meanMotionDotDot
FROM inthesky_spacecraft s
INNER JOIN inthesky_spacecraft_orbit_epochs oe ON oe.noradId = s.noradId AND oe.epochId=%s
INNER JOIN inthesky_spacecraft_orbits o ON oe.orbitId = o.uid
INNER JOIN inthesky_spacecraft_names n ON s.noradId = n.noradId AND primaryName
WHERE ((s.decayDate IS NULL) OR (s.decayDate>%s)) AND NOT s.isDebris;
""", (epoch_info[0]['uid'], utc))
    output = c.fetchall()

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
        'unsuccessful_fits': 0,
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

        path_x_y, path_ra_dec_at_epoch, path_alt_az, sight_line_list_this = projector.ra_dec_from_x_y(
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

        # Look up list of satellite orbital elements at the time of this sighting
        spacecraft_list = fetch_satellites(utc=item['obsTime'])

        # List of candidate showers this meteor might belong to
        candidate_satellites = []

        # Check that we found a list of spacecraft
        if spacecraft_list is None:
            logging.info("{date} [{obs}] -- No spacecraft records found.".format(
                date=date_string(utc=item['obsTime']),
                obs=item['observationId']
            ))
            outcomes['insufficient_information'] += 1
            continue

        # Logging message about how many spacecraft we're testing
        logging.info("{date} [{obs}] -- Matching against {count:7d} spacecraft.".format(
            date=date_string(utc=item['obsTime']),
            obs=item['observationId'],
            count=len(spacecraft_list)
        ))

        # Test for each candidate meteor shower in turn
        for spacecraft in spacecraft_list:
            # Unit scaling
            deg2rad = pi / 180.0  # 0.0174532925199433
            xpdotp = 1440.0 / (2.0 * pi)  # 229.1831180523293

            # Model the path of this spacecraft
            model = Satrec()
            model.sgp4init(
                # whichconst: gravity model
                WGS72,

                # opsmode: 'a' = old AFSPC mode, 'i' = improved mode
                'i',

                # satnum: Satellite number
                spacecraft['noradId'],

                # epoch: days since 1949 December 31 00:00 UT
                jd_from_unix(spacecraft['epoch']) - 2433281.5,

                # bstar: drag coefficient (/earth radii)
                spacecraft['bStar'],

                # ndot (NOT USED): ballistic coefficient (revs/day)
                spacecraft['meanMotionDot'] / (xpdotp * 1440.0),

                # nddot (NOT USED): mean motion 2nd derivative (revs/day^3)
                spacecraft['meanMotionDotDot'] / (xpdotp * 1440.0 * 1440),

                # ecco: eccentricity
                spacecraft['ecc'],

                # argpo: argument of perigee (radians)
                spacecraft['argPeri'] * deg2rad,

                # inclo: inclination (radians)
                spacecraft['incl'] * deg2rad,

                # mo: mean anomaly (radians)
                spacecraft['meanAnom'] * deg2rad,

                # no_kozai: mean motion (radians/minute)
                spacecraft['meanMotion'] / xpdotp,

                # nodeo: right ascension of ascending node (radians)
                spacecraft['RAasc'] * deg2rad
            )

            # Fetch spacecraft position
            e, r, v = model.sgp4(jd_from_unix(utc=item['obsTime']), 0)

            # Convert to celestial coordinate in observer's sky
            logging.info("{} {} {}".format(str(e), str(r), str(v)))

        # Add model possibility for null
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

        # Report possible satellite identifications
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
        if most_likely_satellite == "Unidentified":
            outcomes['unsuccessful_fits'] += 1
        else:
            outcomes['successful_fits'] += 1

    # Report how many fits we achieved
    logging.info("{:d} satellites successfully identified.".format(outcomes['successful_fits']))
    logging.info("{:d} satellites not identified.".format(outcomes['unsuccessful_fits']))
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
                        format='[%(asctime)s] %(levelname)s:%(filename)20s:%(message)s',
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
