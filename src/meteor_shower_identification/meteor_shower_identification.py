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
from operator import itemgetter

import scipy.stats
from pigazing_helpers import connect_db, hardware_properties
from pigazing_helpers.dcf_ast import month_name, unix_from_jd, julian_day, date_string, ra_dec_from_j2000
from pigazing_helpers.gnomonic_project import inv_gnom_project, position_angle, ang_dist
from pigazing_helpers.obsarchive import obsarchive_model as mp, obsarchive_db
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
        # logging.info(shower_descriptor)
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
    outcomes = {
        'successful_fits': 0,
        'error_records': 0,
        'insufficient_information': 0
    }

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

    # Count how many meteors we find in each shower
    meteor_count_by_shower = {}

    # Analyse each meteor in turn
    for item_index, item in enumerate(results):
        # Fetch observatory's database record
        obstory_info = db.get_obstory_from_id(obstory_id=item['observatory'])

        # Fetch observatory status at time of observation
        obstory_status = db.get_obstory_status(obstory_id=item['observatory'], time=item['obsTime'])
        if not obstory_status:
            # We cannot identify meteors if we don't have observatory status
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
                                latitude=obstory_info['latitude'], longitude=obstory_info['longitude'])

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

        # Report possibility meteor shower identifications
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
                                                                dec1=path_ra_dec_at_epoch[-1][0]
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

    # Report how many fits we achieved
    logging.info("{:d} meteors successfully identified.".format(outcomes['successful_fits']))
    logging.info("{:d} malformed database records.".format(outcomes['error_records']))
    logging.info("{:d} meteors with incomplete data.".format(outcomes['insufficient_information']))

    # Report tally of meteors
    logging.info("Tally of meteors by shower:")
    for shower in sorted(meteor_count_by_shower.keys()):
        logging.info("    * {:32s}: {:6d}".format(shower, meteor_count_by_shower[shower]))

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
    shower_determination(utc_min=args.utc_min,
                         utc_max=args.utc_max)
