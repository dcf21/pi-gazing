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

from pigazing_helpers import connect_db, hardware_properties
from pigazing_helpers.dcf_ast import date_string
from pigazing_helpers.gnomonic_project import inv_gnom_project, position_angle
from pigazing_helpers.obsarchive import obsarchive_db
from pigazing_helpers.settings_read import settings, installation_info
from pigazing_helpers.sunset_times import get_zenith_position, ra_dec

simultaneous_event_type = "pigazing:simultaneous"


def do_triangulation(utc_min, utc_max, utc_must_stop):
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

            # Work out path of meteor in RA, Dec (radians)
            try:
                path_x_y = json.loads(item['path'])
            except json.decoder.JSONDecodeError:
                # Attempt JSON repair
                original_json = item['path']
                fixed_json = "],[".join(original_json.split("],[")[:-1]) + "]]"
                try:
                    path_x_y = json.loads(fixed_json)

                    #logging.info("{date} [{obs}/{type:16s}] -- RESCUE: In: {detections:.0f} / {duration:.1f} sec; "
                    #             "Rescued: {count:d} / {json_span:.1f} sec".format(
                    #    date=date_string(utc=group_info['time']),
                    #    obs=group_info['groupId'],
                    #    type=group_info['type'],
                    #    detections=item['detections'],
                    #    duration=item['duration'],
                    #    count=len(path_x_y),
                    #    json_span=path_x_y[-1][3] - path_x_y[0][3]
                    #))

                    path_bezier = json.loads(item['pathBezier'])
                    p = path_bezier[1]
                    path_x_y.append([p[0], p[1], 0, p[2]])
                    p = path_bezier[2]
                    path_x_y.append([p[0], p[1], 0, p[2]])
                    outcomes['rescued_records'] += 1

                    #logging.info("{date} [{obs}/{type:16s}] -- Added Bezier points: "
                    #             "In: {detections:.0f} / {duration:.1f} sec; "
                    #             "Rescued: {count:d} / {json_span:.1f} sec".format(
                    #    date=date_string(utc=group_info['time']),
                    #    obs=group_info['groupId'],
                    #    type=group_info['type'],
                    #    detections=item['detections'],
                    #    duration=item['duration'],
                    #    count=len(path_x_y),
                    #    json_span=path_x_y[-1][3] - path_x_y[0][3]
                    #))
                except json.decoder.JSONDecodeError:
                    logging.info("{date} [{obs}/{type:16s}] -- !!! JSON error".format(
                        date=date_string(utc=group_info['time']),
                        obs=group_info['groupId'],
                        type=group_info['type']
                    ))
                    outcomes['error_records'] += 1
                    continue

            path_len = len(path_x_y)
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

        # # We do all positional astronomy in the frame of the Earth geocentre.
        # # This means that all speeds are measured in the non-rotating frame of the centre of the Earth.
        # group_time = item['time']
        #
        # # Attempt to triangulate object
        # all_sight_lines = []
        #
        # # Work out position of each observatory, and centre of field of view of each observatory
        # for event in item['triggers']:
        #
        #     # Look up information about observatory
        #     obs = event['obs']
        #     obstory_id = obs.obstory_id
        #     obstory_status = db.get_obstory_status(time=group_time, obstory_id=obstory_id)
        #     path_json = db.get_observation_metadata(obs.id, "pigazing:pathBezier")
        #     if ((path_json is None) or
        #             ('lens_barrel_a' not in obstory_status) or
        #             ('latitude' not in obstory_status) or
        #             ('orientation_altitude' not in obstory_status)):
        #         logging.info("Cannot use observation <{}> from <{}> because orientation unknown.".format(obs.id,
        #                                                                                                  obstory_id))
        #         continue
        #     bca = obstory_status['lens_barrel_a']
        #     bcb = obstory_status['lens_barrel_b']
        #     bcc = obstory_status['lens_barrel_c']
        #     path = json.loads(path_json)
        #
        #     # Look up size of image frame
        #     size_x = obstory_status['camera_width']
        #     size_y = obstory_status['camera_height']
        #     scale_x = obstory_status['orientation_width_x_field'] * pi / 180
        #     scale_y = obstory_status['orientation_width_y_field'] * pi / 180
        #     # scale_y = 2 * atan(tan(scale_x / 2) * size_y / size_x)
        #
        #     # For each positional fix on object, convert pixel coordinates into celestial coordinates
        #     sight_line_list = []
        #     for point in path:
        #         utc = point[2]
        #
        #         # Look up the physical position of the observatory
        #         if 'altitude' in obstory_status:
        #             altitude = obstory_status['altitude']
        #         else:
        #             altitude = 0
        #         observatory_position = Point.from_lat_lng(lat=obstory_status['latitude'],
        #                                                   lng=obstory_status['longitude'],
        #                                                   alt=altitude,
        #                                                   utc=utc)
        #
        #         # Calculate the celestial coordinates of the centre of the frame
        #         [ra0, dec0] = sunset_times.ra_dec(alt=obstory_status['orientation_altitude'],
        #                                           az=obstory_status['orientation_azimuth'],
        #                                           utc=utc,
        #                                           latitude=obstory_status['latitude'],
        #                                           longitude=obstory_status['longitude'])
        #         ra0_rad = ra0 * pi / 12  # Convert hours into radians
        #         dec0_rad = dec0 * pi / 180  # Convert degrees into radians
        #
        #         # Convert orientation_pa into position angle of the centre of the field of view
        #         # This is the position angle of the zenith, clockwise from vertical, at the centre of the frame
        #         # If the camera is roughly upright, this ought to be close to zero!
        #         camera_tilt = obstory_status['orientation_pa']
        #
        #         # Get celestial coordinates of the local zenith
        #         ra_dec_zenith = sunset_times.get_zenith_position(lat=obstory_status['latitude'],
        #                                                          lng=obstory_status['longitude'],
        #                                                          utc=utc)
        #         ra_zenith = ra_dec_zenith['ra']
        #         dec_zenith = ra_dec_zenith['dec']
        #
        #         # Work out the position angle of the zenith, counterclockwise from north, as measured at centre of frame
        #         zenith_pa = gnomonic_project.position_angle(ra0, dec0, ra_zenith, dec_zenith)
        #
        #         # Work out the position angle of the upward vector in the centre of the image, counterclockwise
        #         # from celestial north.
        #         celestial_pa = zenith_pa - camera_tilt
        #
        #         # Work out the RA and Dec of the point where the object was spotted
        #         [ra, dec] = gnomonic_project.inv_gnom_project(ra0=ra0_rad, dec0=dec0_rad,
        #                                                       x=point[0], y=point[1],
        #                                                       size_x=size_x, size_y=size_y,
        #                                                       scale_x=scale_x, scale_y=scale_y,
        #                                                       pos_ang=celestial_pa * pi / 180,
        #                                                       bca=bca, bcb=bcb, bcc=bcc)
        #         ra *= 12 / pi  # Convert RA into hours
        #         dec *= 180 / pi  # Convert Dec into degrees
        #
        #         # Work out alt-az of reported (RA,Dec) using known location of camera. Fits returned in degrees.
        #         alt_az = sunset_times.alt_az(ra=ra, dec=dec, utc=point[2],
        #                                      latitude=obstory_status['latitude'], longitude=obstory_status['longitude'])
        #
        #         direction = Vector.from_ra_dec(ra, dec)
        #         sight_line = Line(observatory_position, direction)
        #         sight_line_descriptor = {
        #             'ra': ra,
        #             'dec': dec,
        #             'alt': alt_az[0],
        #             'az': alt_az[1],
        #             'utc': point[2],
        #             'obs_position': observatory_position,
        #             'line': sight_line
        #         }
        #         sight_line_list.append(sight_line_descriptor)
        #         all_sight_lines.append(sight_line_descriptor)
        #
        #         logging.info("Observatory <{}> is pointing at (alt {:.2f}; az {:.2f}; tilt {:.2f}; PA {:.2f}) "
        #                      "and (RA {:.3f} h; Dec {:.2f} deg). "
        #                      "ScaleX = {:.1f} deg. ScaleY = {:.1f} deg.".
        #                      format(obstory_id,
        #                             obstory_status['orientation_altitude'], obstory_status['orientation_azimuth'],
        #                             celestial_pa, obstory_status['orientation_pa'],
        #                             ra0, dec0,
        #                             scale_x * 180 / pi, scale_y * 180 / pi))
        #         logging.info("Observatory <{}> saw object at RA {:.3f} h; Dec {:.3f} deg, with sight line {}.".
        #                      format(obstory_id, ra, dec, sight_line))
        #
        #     # Store calculated information about observation
        #     event['sight_line_list'] = sight_line_list
        #
        # # If we don't have fewer than six sight lines, don't bother trying to triangulate
        # if len(all_sight_lines) < 6:
        #     logging.info("Giving up triangulation as we only have {:d} sight lines to object.".
        #                  format(len(all_sight_lines)))
        #     continue
        #
        # # Work out the sum of square angular mismatches of sight lines to a test trajectory
        # def line_from_parameters(p):
        #     x0 = Point(p[0] * 1000, p[1] * 1000, 0)
        #     d = Vector.from_ra_dec(p[2], p[3])
        #     trajectory = Line(x0=x0, direction=d)
        #     return trajectory
        #
        # def angular_mismatch_slave(p):
        #     trajectory = line_from_parameters(p)
        #     mismatch = 0
        #     for sight in all_sight_lines:
        #         closest_point = trajectory.find_closest_approach(sight['line'])
        #         mismatch += closest_point['angular_distance']
        #     return mismatch
        #
        # params_initial = [0, 0, 0, 0]
        # params_optimised = scipy.optimize.minimize(angular_mismatch_slave, params_initial, method='nelder-mead',
        #                                            options={'xtol': 1e-7, 'disp': False, 'maxiter': 1e6, 'maxfev': 1e6}
        #                                            ).x
        # best_triangulation = line_from_parameters(params_optimised)
        # logging.info("Best fit path of object through space is %s." % best_triangulation)
        #
        # logging.info("Mismatch of observed sight lines from trajectory are %s deg." %
        #              (["%.1f" % best_triangulation.find_closest_approach(s['line'])['angular_distance']
        #                for s in all_sight_lines]))
        #
        # maximum_mismatch = max([best_triangulation.find_closest_approach(s['line'])['angular_distance']
        #                         for s in all_sight_lines])
        #
        # # Reject trajectory if it deviates by more than 3 degrees from any observation
        # if maximum_mismatch > 7:
        #     logging.info("Mismatch is too great. Trajectory fit is rejected.")
        #     continue
        #
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
    logger.info(__doc__.strip())

    # If flush option was specified, then delete all existing alignment information
    if args.flush:
        flush_triangulation(utc_min=args.utc_min,
                            utc_max=args.utc_max)

    # Calculate the orientation of images
    do_triangulation(utc_min=args.utc_min,
                     utc_max=args.utc_max,
                     utc_must_stop=args.stop_by)
