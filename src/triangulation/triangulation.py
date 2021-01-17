#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# triangulation.py
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
Attempt to triangulate the trajectories of moving objects seen at similar times by multiple observatories.
"""

import argparse
import json
import logging
import os
import time
from math import pi

import numpy
import scipy.optimize
from pigazing_helpers import connect_db, hardware_properties
from pigazing_helpers.dcf_ast import date_string
from pigazing_helpers.gnomonic_project import inv_gnom_project, position_angle
from pigazing_helpers.obsarchive import obsarchive_db
from pigazing_helpers.settings_read import settings, installation_info
from pigazing_helpers.sunset_times import get_zenith_position, sidereal_time, ra_dec, alt_az
from pigazing_helpers.vector_algebra import Point, Vector, Line

# The semantic type for observation groups which contain groups of simultaneous object sightings from multiple
# observatories
simultaneous_event_type = "pigazing:simultaneous"

# List of all sight lines to the moving object we are currently fitting
sight_line_list = []


def line_from_parameters(p):
    """
    Construct a Line object based on five free parameters contained in the vector p.

    :param p:
        Vector with at least five components.
    :return:
        Parameterised Line object
    """

    # Starting point for line
    x0 = Point(p[0] * 1000, p[1] * 1000, 0)

    # Direction for line
    d = Vector.from_ra_dec(p[2], p[3])

    # Combining starting point and direction into a single object
    trajectory = Line(x0=x0, direction=d)
    return trajectory


def angular_mismatch_slave(p):
    """
    Objective function that we minimise in order to fit a linear trajectory to all the recorded sight lines to a
    moving object.

    :param p:
        Vector with at least five components.
    :return:
        Mismatch of trial trajectory from recorded sight lines
    """

    global sight_line_list

    # Turn input parameters into a Line object
    trajectory = line_from_parameters(p)

    # Sum the angular offset of each observed position of the object from predicted position
    mismatch = 0
    for sight in sight_line_list:
        # Find point of closest approach between the observed sight line and the trial trajectory for the object
        closest_point = trajectory.find_closest_approach(sight['line'])
        mismatch += closest_point['angular_distance']
    return mismatch


def do_triangulation(utc_min, utc_max, utc_must_stop):
    # We need to share the list of sight lines to each moving object with the objective function that we minimise
    global sight_line_list

    # Open connection to database
    [db0, conn] = connect_db.connect_db()

    db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                           db_host=installation_info['mysqlHost'],
                                           db_user=installation_info['mysqlUser'],
                                           db_password=installation_info['mysqlPassword'],
                                           db_name=installation_info['mysqlDatabase'],
                                           obstory_id=installation_info['observatoryId'])

    # Count how many objects we manage to successfully fit
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

    # Compile search criteria for observation groups
    where = ["g.semanticType = (SELECT uid FROM archive_semanticTypes WHERE name=\"{}\")".
                 format(simultaneous_event_type)
             ]
    args = []

    if utc_min is not None:
        where.append("o.obsTime>=%s")
        args.append(utc_min)
    if utc_max is not None:
        where.append("o.obsTime<=%s")
        args.append(utc_max)

    # Search for observation groups containing groups of simultaneous detections
    conn.execute("""
SELECT g.publicId AS groupId, o.publicId AS observationId, o.obsTime,
       am.stringValue AS objectType, am2.stringValue AS path, am3.stringValue AS pathBezier,
       am4.floatValue AS duration, am5.floatValue AS detections,
       l.publicId AS observatory
FROM archive_obs_groups g
INNER JOIN archive_obs_group_members m on g.uid = m.groupId
INNER JOIN archive_observations o ON m.childObservation = o.uid
INNER JOIN archive_observatories l ON o.observatory = l.uid
INNER JOIN archive_files f on o.uid = f.observationId AND
    f.semanticType=(SELECT uid FROM archive_semanticTypes WHERE name="pigazing:movingObject/video")
INNER JOIN archive_metadata am ON g.uid = am.groupId AND
    am.fieldId = (SELECT uid FROM archive_metadataFields WHERE metaKey="web:category")
INNER JOIN archive_metadata am2 ON f.uid = am2.fileId AND
    am2.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="pigazing:path")
INNER JOIN archive_metadata am3 ON f.uid = am3.fileId AND
    am3.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="pigazing:pathBezier")
INNER JOIN archive_metadata am4 ON f.uid = am4.fileId AND
    am4.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="pigazing:duration")
INNER JOIN archive_metadata am5 ON f.uid = am5.fileId AND
    am5.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="pigazing:detectionCount")
WHERE """ + " AND ".join(where) + """
ORDER BY o.obsTime;
""", args)
    results = conn.fetchall()

    # Compile list of groups
    obs_groups = {}
    obs_group_ids = []
    for item in results:
        key = item['groupId']
        if key not in obs_groups:
            obs_groups[key] = []
            obs_group_ids.append({
                'groupId': key,
                'time': item['obsTime'],
                'type': item['objectType']
            })
        obs_groups[key].append(item)

    # Start triangulation process
    logging.info("Triangulating simultaneous object detections between <{}> and <{}>.".
                 format(date_string(utc_min),
                        date_string(utc_max)))

    # Loop over list of simultaneous event detections
    for group_info in obs_group_ids:
        # If we've run out of time, stop now
        time_now = time.time()
        if time_now > utc_must_stop:
            break

        # Make a list of all our sight-lines to this object
        sight_line_list = []

        # Fetch information about each observation in turn
        for item in obs_groups[group_info['groupId']]:
            # Fetch observatory's database record
            obstory_info = db.get_obstory_from_id(obstory_id=item['observatory'])

            # Fetch observatory status at time of observation
            obstory_status = db.get_obstory_status(obstory_id=item['observatory'], time=item['obsTime'])
            if not obstory_status:
                # We cannot identify meteors if we don't have observatory status
                logging.info("{date} [{obs}/{type:16s}] -- No observatory status available".format(
                    date=date_string(utc=group_info['time']),
                    obs=group_info['groupId'],
                    type=group_info['type']
                ))
                outcomes['insufficient_information'] += 1
                continue

            # Fetch properties of the lens being used at the time of the observation
            lens_name = obstory_status['lens']
            lens_props = hw.lens_data[lens_name]

            # Look up radial distortion model for the lens we are using
            lens_barrel_parameters = obstory_status.get('calibration:lens_barrel_parameters',
                                                        lens_props.barrel_parameters)
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
                logging.info("{date} [{obs}/{type:16s}] -- Orientation of camera unknown".format(
                    date=date_string(utc=group_info['time']),
                    obs=group_info['groupId'],
                    type=group_info['type']
                ))
                outcomes['insufficient_information'] += 1
                continue

            # Look up size of camera sensor
            if 'camera_width' in obstory_status:
                orientation['pixel_width'] = obstory_status['camera_width']
                orientation['pixel_height'] = obstory_status['camera_height']
            else:
                # We cannot identify meteors if we don't know camera field of view
                logging.info(
                    "{date} [{obs}/{type:16s}] -- Pixel dimensions of video stream could not be determined".format(
                        date=date_string(utc=group_info['time']),
                        obs=group_info['groupId'],
                        type=group_info['type']
                    ))
                outcomes['insufficient_information'] += 1
                continue

            # Position of observatory in Cartesian coordinates, relative to centre of the Earth
            # Units: metres; zero longitude along x axis
            observatory_position = Point.from_lat_lng(lat=obstory_info['latitude'],
                                                      lng=obstory_info['longitude'],
                                                      alt=obstory_info['altitude'],
                                                      utc=None)

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
            # degrees, for north pole at epoch
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

                    # logging.info("{date} [{obs}/{type:16s}] -- RESCUE: In: {detections:.0f} / {duration:.1f} sec; "
                    #             "Rescued: {count:d} / {json_span:.1f} sec".format(
                    #    date=date_string(utc=group_info['time']),
                    #    obs=group_info['groupId'],
                    #    type=group_info['type'],
                    #    detections=item['detections'],
                    #    duration=item['duration'],
                    #    count=len(path_x_y),
                    #    json_span=path_x_y[-1][3] - path_x_y[0][3]
                    # ))

                    path_bezier = json.loads(item['pathBezier'])
                    p = path_bezier[1]
                    path_x_y.append([p[0], p[1], 0, p[2]])
                    p = path_bezier[2]
                    path_x_y.append([p[0], p[1], 0, p[2]])
                    outcomes['rescued_records'] += 1

                    # logging.info("{date} [{obs}/{type:16s}] -- Added Bezier points: "
                    #             "In: {detections:.0f} / {duration:.1f} sec; "
                    #             "Rescued: {count:d} / {json_span:.1f} sec".format(
                    #    date=date_string(utc=group_info['time']),
                    #    obs=group_info['groupId'],
                    #    type=group_info['type'],
                    #    detections=item['detections'],
                    #    duration=item['duration'],
                    #    count=len(path_x_y),
                    #    json_span=path_x_y[-1][3] - path_x_y[0][3]
                    # ))
                except json.decoder.JSONDecodeError:
                    logging.info("{date} [{obs}/{type:16s}] -- !!! JSON error".format(
                        date=date_string(utc=group_info['time']),
                        obs=group_info['groupId'],
                        type=group_info['type']
                    ))
                    outcomes['error_records'] += 1
                    continue

            # Convert path of moving objects into RA / Dec (radians, at epoch of observation)
            path_ra_dec_at_epoch = []
            path_alt_az = []
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

                # Calculate RA / Dec of observed position (radians), at observed time
                ra, dec = inv_gnom_project(ra0=instantaneous_central_ra_at_epoch * pi / 12,
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

                path_ra_dec_at_epoch.append([ra, dec])

                # Work out the Greenwich hour angle of the object; radians eastwards of the prime meridian at Greenwich
                instantaneous_sidereal_time = sidereal_time(utc=pt_utc)  # hours
                greenwich_hour_angle = ra - instantaneous_sidereal_time * pi / 12  # radians

                # Work out alt-az of reported (RA,Dec) using known location of camera (degrees)
                alt, az = alt_az(ra=ra * 12 / pi, dec=dec * 180 / pi,
                                 utc=pt_utc,
                                 latitude=obstory_status['latitude'],
                                 longitude=obstory_status['longitude'])

                path_alt_az.append([alt, az])

                # Populate description of this sight line from observatory to the moving object
                direction = Vector.from_ra_dec(ra=greenwich_hour_angle * 12 / pi, dec=dec * 180 / pi)
                sight_line = Line(observatory_position, direction)
                sight_line_descriptor = {
                    'ra': ra,  # radians; at epoch
                    'dec': dec,  # radians; at epoch
                    'alt': alt,  # degrees
                    'az': az,  # degrees
                    'utc': pt_utc,  # unix time
                    'obs_position': observatory_position,  # Point
                    'line': sight_line  # Line
                }
                sight_line_list.append(sight_line_descriptor)

                # Debugging
                logging.info("Observatory <{}> saw object at RA {:.3f} h; Dec {:.3f} deg, with sight line {}.".
                             format(obstory_info['publicId'],
                                    ra * 12 / pi,
                                    dec * 180 / pi,
                                    sight_line))

        # If we have fewer than six sight lines, don't bother trying to triangulate
        if len(sight_line_list) < 6:
            logging.info("Giving up triangulation as we only have {:d} sight lines to object.".
                         format(len(sight_line_list)))
            continue

        # Attempt to fit a linear trajectory through all of the sight lines that we have collected
        parameters_initial = [0, 0, 0, 0]

        # Solve the system of equations
        # See <http://www.scipy-lectures.org/advanced/mathematical_optimization/>
        # for more information about how this works
        parameters_optimised = scipy.optimize.minimize(angular_mismatch_slave, numpy.asarray(parameters_initial),
                                                       options={'disp': False, 'maxiter': 1e8}
                                                       ).x

        # Construct best-fit linear trajectory for best-fitting parameters
        best_triangulation = line_from_parameters(parameters_optimised)
        logging.info("Best fit path of object is <{}>.".format(best_triangulation))

        logging.info("Mismatch of observed sight lines from trajectory are {} deg.".format(
            ["{:.1f}".format(best_triangulation.find_closest_approach(s['line'])['angular_distance'])
             for s in sight_line_list]
        ))

        # Find sight line with the worst match
        maximum_mismatch = max([best_triangulation.find_closest_approach(s['line'])['angular_distance']
                                for s in sight_line_list])

        # Reject trajectory if it deviates by more than 7 degrees from any observation
        if maximum_mismatch > 7:
            logging.info("Mismatch is too great. Trajectory fit is rejected.")
            continue

        # # Add triangulation information to each observation
        # for event in item['triggers']:
        #     if 'sight_line_list' in event:
        #         detected_position_info = []
        #         for detection in event['sight_line_list']:
        #             sight_line = detection['line']
        #             observatory_position = detection['obs_position']
        #             object_position = best_triangulation.find_closest_approach(sight_line)
        #             object_lat_lng = object_position['self_point'].to_lat_lng(detection['utc'])
        #             object_distance = abs(object_position['self_point'].displacement_vector_from(observatory_position))
        #             detection['object_position'] = observatory_position
        #             detected_position_info.append({'ra': detection['ra'],
        #                                            'dec': detection['dec'],
        #                                            'alt': detection['alt'],
        #                                            'az': detection['az'],
        #                                            'utc': detection['utc'],
        #                                            'lat': object_lat_lng['lat'],
        #                                            'lng': object_lat_lng['lng'],
        #                                            'height': object_lat_lng['alt'],
        #                                            'dist': object_distance,
        #                                            'ang_mismatch': object_position['angular_distance']
        #                                            })
        #
        #         # Make descriptor of triangulated information
        #         trigger_0 = event['sight_line_list'][0]
        #         trigger_1 = event['sight_line_list'][-1]
        #         obs_position_0 = trigger_0['obs_position']  # Position of observatory at first sighting
        #         obj_position_0 = trigger_0['object_position']  # Position of object at first sighting
        #         utc_0 = trigger_0['utc']
        #         obs_position_1 = trigger_1['obs_position']  # Position of observatory at last sighting
        #         obj_position_1 = trigger_1['object_position']  # Position of object at last sighting
        #         utc_1 = trigger_1['utc']
        #
        #         # Work out speed of object relative to centre of the Earth
        #         displacement_geocentre_frame = obj_position_1.displacement_vector_from(obj_position_0)
        #         time_span = utc_1 - utc_0
        #         speed_geocentre_frame = abs(displacement_geocentre_frame / time_span)
        #         object_direction_geocentre_frame = best_triangulation.direction.to_ra_dec()
        #
        #         # Work out speed of object relative to observer
        #         point_0_obs_frame = obj_position_0.displacement_vector_from(obs_position_0)
        #         point_1_obs_frame = obj_position_1.displacement_vector_from(obs_position_1)
        #         displacement_obs_frame = point_1_obs_frame - point_0_obs_frame
        #         speed_obs_frame = abs(displacement_obs_frame / time_span)
        #         object_direction_obs_frame = displacement_obs_frame.to_ra_dec()
        #
        #         triangulation_info = {'observer_frame_heading_ra': object_direction_obs_frame['ra'],
        #                               'observer_frame_heading_dec': object_direction_obs_frame['dec'],
        #                               'observer_frame_speed': speed_obs_frame,
        #                               'geocentre_heading_ra': object_direction_geocentre_frame['ra'],
        #                               'geocentre_heading_dec': object_direction_geocentre_frame['dec'],
        #                               'geocentre_speed': speed_geocentre_frame,
        #                               'position_list': detected_position_info}
        #         logging.info("Triangulated details of observation <{}> is {}.".
        #                      format(event['obs'].id, triangulation_info))
        #
        #         # Store triangulated information in database
        #         meta_item = mp.Meta("triangulation", json.dumps(triangulation_info))
        #         db.set_observation_metadata(observation_id=event['obs'].id,
        #                                     meta=meta_item,
        #                                     user_id=settings['pigazingUser'])

        # Report outcome
        logging.info("{date} [{obs}/{type:16s}] -- Success".format(
            date=date_string(utc=group_info['time']),
            obs=group_info['groupId'],
            type=group_info['type']
        ))

        # Triangulation successful
        outcomes['successful_fits'] += 1

    # Report how many fits we achieved
    logging.info("{:d} objects successfully triangulated.".format(outcomes['successful_fits']))
    logging.info("{:d} malformed database records.".format(outcomes['error_records']))
    logging.info("{:d} rescued database records.".format(outcomes['rescued_records']))
    logging.info("{:d} objects with incomplete data.".format(outcomes['insufficient_information']))

    # Commit changes
    db.commit()
    db.close_db()
    db0.commit()
    conn.close()
    db0.close()


def flush_triangulation(utc_min, utc_max):
    """
    Remove all pre-existing triangulation metadata.

    :param utc_min:
        The earliest time for which we are to flush observation groups.
    :param utc_max:
        The latest time for which we are to flush observation groups.
    :return:
        None
    """
    # Open connection to database
    [db0, conn] = connect_db.connect_db()

    # Delete observation metadata fields that start 'orientation:*'
    conn.execute("""
DELETE m
FROM archive_metadata m
INNER JOIN archive_obs_groups o ON m.observationId = o.uid
WHERE
    fieldId IN (SELECT uid FROM archive_metadataFields WHERE metaKey LIKE 'triangulation:%%') AND
    o.obsTime BETWEEN %s AND %s;
""", (utc_min, utc_max))

    # Commit changes to database
    db0.commit()
    conn.close()
    db0.close()


# If we're called as a script, run the method orientationCalc()
if __name__ == "__main__":
    # Read command-line arguments
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stop-by', default=None, type=float,
                        dest='stop_by', help='The unix time when we need to exit, even if jobs are unfinished')

    # By default, study images taken over past 24 hours
    parser.add_argument('--utc-min', dest='utc_min', default=0,
                        type=float,
                        help="Only search for detections from after the specified unix time")
    parser.add_argument('--utc-max', dest='utc_max', default=time.time(),
                        type=float,
                        help="Only search for detections from before the specified unix time")

    # Flush previous simultaneous detections?
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
    logger.info(__doc__.strip())

    # If flush option was specified, then delete all existing alignment information
    if args.flush:
        flush_triangulation(utc_min=args.utc_min,
                            utc_max=args.utc_max)

    # Calculate the orientation of images
    do_triangulation(utc_min=args.utc_min,
                     utc_max=args.utc_max,
                     utc_must_stop=args.stop_by)
