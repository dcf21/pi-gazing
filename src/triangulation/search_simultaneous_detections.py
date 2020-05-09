#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# search_simultaneous_detections.py
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
Search the database for moving objects seen at similar times by multiple observatories. Create observation group
objects to describe the simultaneous detections.
"""

import argparse
import logging
import os
import time

from pigazing_helpers import dcf_ast
from pigazing_helpers.obsarchive import obsarchive_db
from pigazing_helpers.obsarchive import obsarchive_model as mp
from pigazing_helpers.settings_read import settings, installation_info
from pigazing_helpers.vector_algebra import Point

simultaneous_event_type = "pigazing:simultaneous"


def search_simultaneous_detections(utc_min, utc_max, utc_must_stop):
    db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                           db_host=installation_info['mysqlHost'],
                                           db_user=installation_info['mysqlUser'],
                                           db_password=installation_info['mysqlPassword'],
                                           db_name=installation_info['mysqlDatabase'],
                                           obstory_id=installation_info['observatoryId'])

    # Search for moving objects within time span
    search = mp.ObservationSearch(observation_type="pigazing:movingObject/",
                                  time_min=utc_min,
                                  time_max=utc_max,
                                  limit=1000000)
    events_raw = db.search_observations(search)

    # Use only event descriptors, not other returned fields
    events = events_raw['obs']

    # Make a list of which events are already members of groups
    events_used = [False] * len(events)

    # Look up the categorisation of each event
    for event in events:
        event.category = db.get_observation_metadata(event.id, "web:category")

    # Throw out junk events and unclassified events
    events = [x for x in events if x.category is not None and x.category not in ('Junk', 'Bin')]

    # Look up which pre-existing observation groups each event is in
    for index, event in enumerate(events):
        db.con.execute("""
SELECT COUNT(*)
FROM archive_obs_groups grp
WHERE grp.semanticType = (SELECT y.uid FROM archive_semanticTypes y WHERE y.name=%s) AND
      EXISTS (SELECT 1 FROM archive_obs_group_members x
              WHERE x.groupId=grp.uid AND
                    x.childObservation=(SELECT z.uid FROM archive_observations z WHERE z.publicId=%s));
""", (simultaneous_event_type, event.id))

        if db.con.fetchone()['COUNT(*)'] > 0:
            events_used[index] = True

    # Sort event descriptors into chronological order
    events.sort(key=lambda x: x.obs_time)

    # Look up the duration of each event, and calculate its end time
    for event in events:
        duration = 0
        for meta in event.meta:
            if meta.key == "pigazing:duration":
                duration = meta.value
        event.duration = duration
        event.obs_time_end = event.obs_time + duration

    # Compile list of simultaneous object detections
    groups = []

    # Search for simultaneous object detections
    for index in range(len(events)):
        # If we have already put this event in another simultaneous detection, don't add it to others
        if events_used[index]:
            continue

        # Look up time span of event
        event = events[index]
        obstory_id_list = [event.obstory_id]  # List of all observatories which saw this event
        utc_min = event.obs_time  # Earliest start time of any of the events in this group
        utc_max = event.obs_time_end  # Latest end time of any of the events in this group
        events_used[index] = True
        prev_group_size = -1
        group_members = [index]

        search_margin = 60
        match_margin = 1

        # Search for other events which fall within the same time span
        # Do this iteratively, as a preceding event can expand the end time of the group, and vice versa
        while len(group_members) > prev_group_size:
            prev_group_size = len(group_members)
            # Search for events at earlier times, and then at later times
            for search_direction in (-1, 1):
                # Start from the reference event
                candidate_index = index

                # Step through other events, providing they're within range
                while ((candidate_index >= 0) and
                       (candidate_index < len(events))):
                    # Fetch event record
                    candidate = events[candidate_index]

                    # Stop search if we've gone out of time range
                    if ((candidate.obs_time_end < utc_min - search_margin) or
                            (candidate.obs_time > utc_max + search_margin)):
                        break

                    # Check whether this is a simultaneous detection, with same categorisation
                    if ((not events_used[candidate_index]) and
                            (candidate.category == event.category) and
                            (candidate.obs_time < utc_max + match_margin) and
                            (candidate.obs_time_end > utc_min - match_margin)):
                        # Add this event to the group, and update time span of event
                        group_members.append(candidate_index)
                        utc_min = min(utc_min, candidate.obs_time)
                        utc_max = max(utc_max, candidate.obs_time_end)

                        # Compile a list of all the observatories which saw this event
                        if candidate.obstory_id not in obstory_id_list:
                            obstory_id_list.append(candidate.obstory_id)

                        # Record that we have added this event to a group
                        events_used[candidate_index] = True

                    # Step on to the next candidate event to add into group
                    candidate_index += search_direction

        # We have found a coincident detection only if multiple observatories saw an event at the same time
        if len(obstory_id_list) < 2:
            continue

        maximum_obstory_spacing = 0

        # Work out locations of all observatories which saw this event
        obstory_locs = []
        for obstory_id in obstory_id_list:
            obstory_info = db.get_obstory_from_id(obstory_id)
            obstory_loc = Point.from_lat_lng(lat=obstory_info['latitude'],
                                             lng=obstory_info['longitude'],
                                             alt=0,
                                             utc=(utc_min + utc_max) / 2
                                             )
            obstory_locs.append(obstory_loc)

        # Check the distances between all pairs of observatories
        pairs = [[obstory_locs[i], obstory_locs[j]]
                 for i in range(len(obstory_id_list))
                 for j in range(i + 1, len(obstory_id_list))
                 ]

        for pair in pairs:
            maximum_obstory_spacing = max(maximum_obstory_spacing,
                                          abs(pair[0].displacement_vector_from(pair[1])))

        # Create information about this simultaneous detection
        groups.append({'time': (utc_min + utc_max) / 2,
                       'obstory_list': obstory_id_list,
                       'time_spread': utc_max - utc_min,
                       'geographic_spacing': maximum_obstory_spacing,
                       'category': event.category,
                       'observations': [{'obs': events[x]} for x in group_members],
                       'ids': [events[x].id for x in group_members]})

    logging.info("{:6d} moving objects seen within this time period".
                 format(len(events_raw['obs'])))
    logging.info("{:6d} moving objects rejected because they were unclassified".
                 format(len(events_raw['obs']) - len(events)))
    logging.info("{:6d} simultaneous detections found.".
                 format(len(groups)))

    for item in groups:
        logging.info("""
{time} -- {count:3d} stations; max baseline {baseline:5.0f} m; time spread {spread:4.1f} sec; type <{category}>
""".format(time=dcf_ast.date_string(item['time']),
           count=len(item['obstory_list']),
           baseline=item['geographic_spacing'],
           spread=item['time_spread'],
           category=item['category']).strip())

    # Start triangulation process
    logging.info("Triangulating simultaneous object detections between <{}> and <{}>.".
                 format(dcf_ast.date_string(utc_min),
                        dcf_ast.date_string(utc_max)))

    # Loop over list of simultaneous event detections
    for item in groups:
        # Create new observation group
        group = db.register_obsgroup(title="Multi-station detection", user_id="system",
                                     semantic_type=simultaneous_event_type,
                                     obs_time=item['time'], set_time=time.time(),
                                     obs=item['ids'])
        logging.info("Simultaneous detection at {time} by {count:3d} stations (time spread {spread:.1f} sec)".
                     format(time=dcf_ast.date_string(item['time']),
                            count=len(item['obstory_list']),
                            spread=item['time_spread']))
        logging.info("Observation IDs: %s" % item['ids'])

        # Register group metadata
        timestamp = time.time()
        db.set_obsgroup_metadata(user_id="system", group_id=group.id, utc=timestamp,
                                 meta=mp.Meta(key="web:category", value=item['category']))
        db.set_obsgroup_metadata(user_id="system", group_id=group.id, utc=timestamp,
                                 meta=mp.Meta(key="simultaneous:time_spread", value=item['time_spread']))
        db.set_obsgroup_metadata(user_id="system", group_id=group.id, utc=timestamp,
                                 meta=mp.Meta(key="simulataneous:geographic_spread", value=item['geographic_spacing']))

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

    # Commit changes
    db.commit()


def flush_simultaneous_detections(utc_min, utc_max):
    """
    Remove all pre-existing observation groups from within a specified time period.

    :param utc_min:
        The earliest time for which we are to flush observation groups.
    :param utc_max:
        The latest time for which we are to flush observation groups.
    :return:
        None
    """
    db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                           db_host=installation_info['mysqlHost'],
                                           db_user=installation_info['mysqlUser'],
                                           db_password=installation_info['mysqlPassword'],
                                           db_name=installation_info['mysqlDatabase'],
                                           obstory_id=installation_info['observatoryId'])

    # Search for existing observation groups representing simultaneous events
    search = mp.ObservationGroupSearch(semantic_type=simultaneous_event_type,
                                       time_min=utc_min, time_max=utc_max, limit=1000000)
    existing_groups = db.search_obsgroups(search)
    existing_groups = existing_groups['obsgroups']

    logging.info("{:6d} existing observation groups within this time period (will be deleted).".
                 format(len(existing_groups)))

    # Delete existing observation groups
    for item in existing_groups:
        db.delete_obsgroup(item.id)

    # Delete existing triangulation metadata
    db.con.execute("""
DELETE m
FROM archive_metadata m
INNER JOIN archive_observations o ON m.observationId = o.uid
WHERE fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey LIKE 'triangulation:%%') AND
      o.obsTime BETWEEN %s AND %s;
""", (utc_min, utc_max))

    # Commit to database
    db.commit()


# If we're called as a script, run the method orientationCalc()
if __name__ == "__main__":
    # Read command-line arguments
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stop-by', default=None, type=float,
                        dest='stop_by', help='The unix time when we need to exit, even if jobs are unfinished')

    # By default, study images taken over past 24 hours
    parser.add_argument('--utc-min', dest='utc_min', default=time.time() - 3600 * 24,
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
        flush_simultaneous_detections(utc_min=args.utc_min,
                                      utc_max=args.utc_max)

    # Calculate the orientation of images
    search_simultaneous_detections(utc_min=args.utc_min,
                                   utc_max=args.utc_max,
                                   utc_must_stop=args.stop_by)
