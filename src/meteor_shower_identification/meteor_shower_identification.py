#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# meteor_shower_identification.py
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
from math import pi, sin
from operator import itemgetter

import scipy.stats
from pigazing_helpers import connect_db
from pigazing_helpers.dcf_ast import month_name, unix_from_jd, julian_day, date_string, ra_dec_from_j2000
from pigazing_helpers.gnomonic_project import ang_dist
from pigazing_helpers.obsarchive import obsarchive_model as mp, obsarchive_db
from pigazing_helpers.path_projection import PathProjection
from pigazing_helpers.settings_read import settings, installation_info
from pigazing_helpers.sunset_times import alt_az, sun_pos
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
        # logging.info(shower_descriptor)
        output.append(shower_descriptor)

    # Return output
    return output


def shower_determination(utc_min, utc_max):
    """
    Estimate the parent showers of all meteors observed between the unix times <utc_min> and <utc_max>.

    :param utc_min:
        The start of the time period in which we should determine the parent showers of meteors (unix time).
    :type utc_min:
        float
    :param utc_max:
        The end of the time period in which we should determine the parent showers of meteors (unix time).
    :type utc_max:
        float
    :return:
        None
    """

    # Load list of meteor showers
    shower_list = read_shower_list()

    # Open connection to image archive
    db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                           db_host=installation_info['mysqlHost'],
                                           db_user=installation_info['mysqlUser'],
                                           db_password=installation_info['mysqlPassword'],
                                           db_name=installation_info['mysqlDatabase'],
                                           obstory_id=installation_info['observatoryId'])

    logging.info("Starting meteor shower identification.")

    # Count how many images we manage to successfully fit
    outcomes = {
        'successful_fits': 0,
        'error_records': 0,
        'rescued_records': 0,
        'insufficient_information': 0
    }

    # Status update
    logging.info("Searching for meteors within period {} to {}".format(date_string(utc_min), date_string(utc_max)))

    # Open direct connection to database
    conn = db.con

    # Search for meteors within this time period
    conn.execute("""
SELECT ao.obsTime, ao.publicId AS observationId, f.repositoryFname, l.publicId AS observatory
FROM archive_observations ao
LEFT OUTER JOIN archive_files f ON (ao.uid = f.observationId AND
    f.semanticType=(SELECT uid FROM archive_semanticTypes WHERE name="pigazing:movingObject/video"))
INNER JOIN archive_observatories l ON ao.observatory = l.uid
INNER JOIN archive_metadata am2 ON ao.uid = am2.observationId AND
    am2.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="web:category")
WHERE ao.obsType=(SELECT uid FROM archive_semanticTypes WHERE name='pigazing:movingObject/') AND
      ao.obsTime BETWEEN %s AND %s AND
      am2.stringValue = "Meteor"
ORDER BY ao.obsTime;
""", (utc_min, utc_max))
    results = conn.fetchall()

    # Display logging list of the images we are going to work on
    logging.info("Estimating the parent showers of {:d} meteors.".format(len(results)))

    # Count how many meteors we find in each shower
    meteor_count_by_shower = {}

    # Analyse each meteor in turn
    for item_index, item in enumerate(results):
        # Fetch metadata about this object, some of which might be on the file, and some on the observation
        obs_obj = db.get_observation(observation_id=item['observationId'])
        obs_metadata = {item.key: item.value for item in obs_obj.meta}
        if item['repositoryFname']:
            file_obj = db.get_file(repository_fname=item['repositoryFname'])
            file_metadata = {item.key: item.value for item in file_obj.meta}
        else:
            file_metadata = {}
        all_metadata = {**obs_metadata, **file_metadata}

        # Check we have all required metadata
        if 'pigazing:path' not in all_metadata:
            logging.info("Cannot process <{}> due to inadequate metadata.".format(item['observationId']))
            continue

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
            path_json=all_metadata['pigazing:path'],
            path_bezier_json=all_metadata['pigazing:pathBezier'],
            detections=all_metadata['pigazing:detectionCount'],
            duration=all_metadata['pigazing:duration']
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

        # List of candidate showers this meteor might belong to
        candidate_showers = []

        # Test for each candidate meteor shower in turn
        for shower in shower_list:
            # Work out celestial coordinates of shower radiant in RA/Dec in hours/degs of epoch
            radiant_ra_at_epoch, radiant_dec_at_epoch = ra_dec_from_j2000(ra0=shower['RA'],
                                                                          dec0=shower['Decl'],
                                                                          utc_new=item['obsTime'])

            # Work out alt-az of the shower's radiant using known location of camera. Fits returned in degrees.
            alt_az_pos = alt_az(ra=radiant_ra_at_epoch, dec=radiant_dec_at_epoch,
                                utc=item['obsTime'],
                                latitude=projector.obstory_info['latitude'],
                                longitude=projector.obstory_info['longitude'])

            # Work out position of the Sun (J2000)
            sun_ra_j2000, sun_dec_j2000 = sun_pos(utc=item['obsTime'])

            # Work out position of the Sun (RA, Dec of epoch)
            sun_ra_at_epoch, sun_dec_at_epoch = ra_dec_from_j2000(ra0=sun_ra_j2000, dec0=sun_dec_j2000,
                                                                  utc_new=item['obsTime'])

            # Offset from peak of shower
            year = 365.2524
            peak_offset = (sun_ra_at_epoch * 180 / 12. - shower['peak']) * year / 360  # days
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

            # Work out angular distance of meteor from radiant (radians)
            path_radiant_sep = [ang_dist(ra0=pt[0], dec0=pt[1],
                                         ra1=radiant_ra_at_epoch * pi / 12, dec1=radiant_dec_at_epoch * pi / 180)
                                for pt in path_ra_dec_at_epoch]
            change_in_radiant_dist = path_radiant_sep[-1] - path_radiant_sep[0]  # radians

            # Reject meteors that travel *towards* the radiant
            if change_in_radiant_dist < 0:
                continue

            # Convert path to Cartesian coordinates on a unit sphere
            path_cartesian = [Vector.from_ra_dec(ra=ra * 12 / pi, dec=dec * 180 / pi)
                              for ra, dec in path_ra_dec_at_epoch]

            # Work out cross product of first and last point, which is normal to path of meteors
            first = path_cartesian[0]
            last = path_cartesian[-1]
            path_normal = first.cross_product(last)

            # Work out angle of path normal to meteor shower radiant
            radiant_cartesian = Vector.from_ra_dec(ra=radiant_ra_at_epoch, dec=radiant_dec_at_epoch)
            theta = path_normal.angle_with(radiant_cartesian)  # degrees

            if theta > 90:
                theta = 180 - theta

            # What is the angular separation of the meteor's path's closest approach to the shower radiant?
            radiant_angle = 90 - theta

            # Work out likelihood metric that this meteor belongs to this shower
            radiant_angle_std_dev = 2  # Allow 2 degree mismatch in radiant pos
            likelihood = hourly_rate * scipy.stats.norm(loc=0, scale=radiant_angle_std_dev).pdf(radiant_angle)

            # Store information about the likelihood this meteor belongs to this shower
            candidate_showers.append({
                'name': shower['name'],
                'likelihood': likelihood,
                'offset': radiant_angle,
                'change_radiant_dist': change_in_radiant_dist,
                'shower_rate': hourly_rate
            })

        # Add model possibility for sporadic meteor
        hourly_rate = 5
        likelihood = hourly_rate * (1. / 90.)  # Mean value of Gaussian in range 0-90 degs
        candidate_showers.append({
            'name': "Sporadic",
            'likelihood': likelihood,
            'offset': 0,
            'shower_rate': hourly_rate
        })

        # Renormalise likelihoods to sum to unity
        sum_likelihood = sum(shower['likelihood'] for shower in candidate_showers)
        for shower in candidate_showers:
            shower['likelihood'] *= 100 / sum_likelihood

        # Sort candidates by likelihood
        candidate_showers.sort(key=itemgetter('likelihood'), reverse=True)

        # Report possible meteor shower identifications
        logging.info("{date} [{obs}] -- {showers}".format(
            date=date_string(utc=item['obsTime']),
            obs=item['observationId'],
            showers=", ".join([
                "{} {:.1f}% ({:.1f} deg offset)".format(shower['name'], shower['likelihood'], shower['offset'])
                for shower in candidate_showers
            ])
        ))

        # Identify most likely shower
        most_likely_shower = candidate_showers[0]['name']

        # Update tally of meteors
        if most_likely_shower not in meteor_count_by_shower:
            meteor_count_by_shower[most_likely_shower] = 0
        meteor_count_by_shower[most_likely_shower] += 1

        # Store meteor identification
        user = settings['pigazingUser']
        timestamp = time.time()
        db.set_observation_metadata(user_id=user, observation_id=item['observationId'], utc=timestamp,
                                    meta=mp.Meta(key="shower:name", value=most_likely_shower))
        db.set_observation_metadata(user_id=user, observation_id=item['observationId'], utc=timestamp,
                                    meta=mp.Meta(key="shower:radiant_offset", value=candidate_showers[0]['offset']))
        db.set_observation_metadata(user_id=user, observation_id=item['observationId'], utc=timestamp,
                                    meta=mp.Meta(key="shower:path_length",
                                                 value=ang_dist(ra0=path_ra_dec_at_epoch[0][0],
                                                                dec0=path_ra_dec_at_epoch[0][1],
                                                                ra1=path_ra_dec_at_epoch[-1][0],
                                                                dec1=path_ra_dec_at_epoch[-1][1]
                                                                ) * 180 / pi
                                                 ))
        db.set_observation_metadata(user_id=user, observation_id=item['observationId'], utc=timestamp,
                                    meta=mp.Meta(key="shower:path_ra_dec",
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

        # Update database
        db.commit()

    # Report how many fits we achieved
    logging.info("{:d} meteors successfully identified.".format(outcomes['successful_fits']))
    logging.info("{:d} malformed database records.".format(outcomes['error_records']))
    logging.info("{:d} rescued database records.".format(outcomes['rescued_records']))
    logging.info("{:d} meteors with incomplete data.".format(outcomes['insufficient_information']))

    # Report tally of meteors
    logging.info("Tally of meteors by shower:")
    for shower in sorted(meteor_count_by_shower.keys()):
        logging.info("    * {:32s}: {:6d}".format(shower, meteor_count_by_shower[shower]))

    # Clean up and exit
    db.commit()
    db.close_db()
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

    # By default, categorise all meteors recorded since the beginning of time
    parser.add_argument('--utc-min', dest='utc_min', default=0,
                        type=float,
                        help="Only analyse meteors recorded after the specified unix time")
    parser.add_argument('--utc-max', dest='utc_max', default=time.time(),
                        type=float,
                        help="Only analyse meteors recorded before the specified unix time")

    parser.add_argument('--flush', dest='flush', action='store_true')
    parser.add_argument('--no-flush', dest='flush', action='store_false')
    parser.set_defaults(flush=True)
    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(level=logging.INFO,
                        format='[%(asctime)s] %(levelname)s:%(filename)32s:%(message)s',
                        datefmt='%d/%m/%Y %H:%M:%S',
                        handlers=[
                            logging.FileHandler(os.path.join(settings['pythonPath'], "../datadir/pigazing.log")),
                            logging.StreamHandler()
                        ])
    logger = logging.getLogger(__name__)
    # logger.info(__doc__.strip())

    # If flush option was specified, then delete all existing meteor identifications
    if args.flush:
        flush_identifications(utc_min=args.utc_min,
                              utc_max=args.utc_max)

    # Estimate the parentage of meteors
    shower_determination(utc_min=args.utc_min,
                         utc_max=args.utc_max)
