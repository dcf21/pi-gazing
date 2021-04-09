#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# triangulation.py
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
Attempt to triangulate the trajectories of moving objects seen at similar times by multiple observatories.
"""

import argparse
import json
import logging
import os
import time
from math import hypot, log10

import numpy
import scipy.optimize
from pigazing_helpers import connect_db
from pigazing_helpers.dcf_ast import date_string
from pigazing_helpers.obsarchive import obsarchive_model as mp, obsarchive_db
from pigazing_helpers.path_projection import PathProjection
from pigazing_helpers.settings_read import settings, installation_info
from pigazing_helpers.sunset_times import sidereal_time
from pigazing_helpers.vector_algebra import Point, Vector, Line

# The semantic type for observation groups which contain groups of simultaneous object sightings from multiple
# observatories
simultaneous_event_type = "pigazing:simultaneous"

# List of all sight lines to the moving object we are currently fitting
sight_line_list = []

# Initial guess for position of moving object
seed_position = Point(0, 0, 0)

# Time span of sightings of moving object
time_span = [0, 0]


def line_from_parameters(p):
    """
    Construct a Line object based on five free parameters contained in the vector p.

    :param p:
        Vector with at least six components.
    :return:
        Parameterised Line object
    """
    global seed_position

    # Starting point for line (at utc_min)
    x0 = seed_position.add_vector(Vector(p[0] * 1000, p[1] * 1000, p[2] * 1000))

    # Direction for line
    d = Vector(p[3] * 100, p[4] * 100, p[5] * 100)

    # Combining starting point and direction into a single object
    trajectory = Line(x0=x0, direction=d)
    return trajectory


def sight_line_mismatch_list(trajectory):
    """
    Compute the angular offset (degrees) of a list of timed lines of sight to a moving object from a trial
    trajectory for that object.

    :param trajectory:
        Trial trajectory for a moving object.
    :type trajectory:
        Line
    :return:
        List of mismatches of trial trajectory from recorded sight lines
    """

    global sight_line_list, time_span

    # Sum the angular offset of each observed position of the object from predicted position
    mismatch_list = []
    for sight in sight_line_list:
        # Map duration of moving object onto line segment time span 0-1
        time_point = (sight['utc'] - time_span[0]) / (time_span[1] - time_span[0])

        # Fetch trajectory position at time of sighting
        trajectory_pos = trajectory.point(i=time_point)

        model_sightline = trajectory_pos.to_vector() - sight['obs_position'].to_vector()
        observed_sightline = sight['line'].direction
        angular_offset = model_sightline.angle_with(other=observed_sightline)  # degrees

        # Find point of closest approach between the observed sight line and the trial trajectory for the object
        mismatch_list.append(angular_offset)
    return mismatch_list


def angular_mismatch_objective(p):
    """
    Objective function that we minimise in order to fit a linear trajectory to all the recorded sight lines to a
    moving object.

    :param p:
        Vector with at least six components.
    :return:
        Sum of square mismatches of trial trajectory from recorded sight lines
    """

    global time_span

    # Turn input parameters into a Line object
    trajectory = line_from_parameters(p)

    # Fetch list of angular offsets (degrees) of trial trajectory from observed sight lines
    mismatch_list = sight_line_mismatch_list(trajectory=trajectory)

    # Calculate sum of squares of mismatches
    angular_mismatches = hypot(*mismatch_list)
    speed = abs(trajectory.direction) / (time_span[1] - time_span[0])  # m/s

    # Heuristic to penalise very fast speeds
    return angular_mismatches * log10(abs(speed)+10000)


def do_triangulation(utc_min, utc_max, utc_must_stop):
    # We need to share the list of sight lines to each moving object with the objective function that we minimise
    global sight_line_list, time_span, seed_position

    # Start triangulation process
    logging.info("Triangulating simultaneous object detections between <{}> and <{}>.".
                 format(date_string(utc_min),
                        date_string(utc_max)))

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

    # Open connection to database
    [db0, conn] = connect_db.connect_db()

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

    # Close connection to database
    conn.close()
    db0.close()

    # Compile list of events into list of groups
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

    # Loop over list of simultaneous event detections
    for group_info in obs_group_ids:
        # Make ID string to prefix to all logging messages about this event
        logging_prefix = "{date} [{obs}/{type:16s}]".format(
            date=date_string(utc=group_info['time']),
            obs=group_info['groupId'],
            type=group_info['type']
        )

        # If we've run out of time, stop now
        time_now = time.time()
        if utc_must_stop is not None and time_now > utc_must_stop:
            break

        # Make a list of all our sight-lines to this object, from all observatories
        sight_line_list = []
        observatory_list = {}

        # Fetch information about each observation in turn
        for item in obs_groups[group_info['groupId']]:
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

            # Add to observatory_list, now that we've checked this observatory has all necessary information
            if item['observatory'] not in observatory_list:
                observatory_list[item['observatory']] = projector.obstory_info

            # Add sight lines from this observatory to list which combines all observatories
            sight_line_list.extend(sight_line_list_this)

        # If we have fewer than four sight lines, don't bother trying to triangulate
        if len(sight_line_list) < 4:
            logging.info("{prefix} -- Giving up triangulation as we only have {x:d} sight lines to object.".
                         format(prefix=logging_prefix,
                                x=len(sight_line_list)
                                ))
            continue

        # Initialise maximum baseline between the stations which saw this objects
        maximum_baseline = 0

        # Check the distances between all pairs of observatories
        obstory_info_list = [Point.from_lat_lng(lat=obstory['latitude'],
                                                lng=obstory['longitude'],
                                                alt=0,
                                                utc=None
                                                )
                             for obstory in observatory_list.values()]

        pairs = [[obstory_info_list[i], obstory_info_list[j]]
                 for i in range(len(obstory_info_list))
                 for j in range(i + 1, len(obstory_info_list))
                 ]

        # Work out maximum baseline between the stations which saw this objects
        for pair in pairs:
            maximum_baseline = max(maximum_baseline,
                                   abs(pair[0].displacement_vector_from(pair[1])))

        # If we have no baselines of over 1 km, don't bother trying to triangulate
        if maximum_baseline < 1000:
            logging.info("{prefix} -- Giving up triangulation as longest baseline is only {x:.0f} m.".
                         format(prefix=logging_prefix,
                                x=maximum_baseline
                                ))
            continue

        # Set time range of sight lines
        time_span = [
            min(item['utc'] for item in sight_line_list),
            max(item['utc'] for item in sight_line_list)
        ]

        # Create a seed point to start search for object path. We pick a point above the centroid of the observatories
        # that saw the object
        centroid_v = sum(item['obs_position'].to_vector() for item in sight_line_list) / len(sight_line_list)
        centroid_p = Point(x=centroid_v.x, y=centroid_v.y, z=centroid_v.z)
        centroid_lat_lng = centroid_p.to_lat_lng(utc=None)
        seed_position = Point.from_lat_lng(lat=centroid_lat_lng['lat'],
                                           lng=centroid_lat_lng['lng'],
                                           alt=centroid_lat_lng['alt'] * 2e4,
                                           utc=None)

        # Attempt to fit a linear trajectory through all of the sight lines that we have collected
        parameters_initial = [0, 0, 0, 0, 0, 0]

        # Solve the system of equations
        # See <http://www.scipy-lectures.org/advanced/mathematical_optimization/>
        # for more information about how this works
        parameters_optimised = scipy.optimize.minimize(angular_mismatch_objective, numpy.asarray(parameters_initial),
                                                       options={'disp': False, 'maxiter': 1e8}
                                                       ).x

        # Construct best-fit linear trajectory for best-fitting parameters
        best_triangulation = line_from_parameters(parameters_optimised)
        # logging.info("Best fit path of object is <{}>.".format(best_triangulation))

        # logging.info("Mismatch of observed sight lines from trajectory are {} deg.".format(
        #     ["{:.1f}".format(best_triangulation.find_closest_approach(s['line'])['angular_distance'])
        #      for s in sight_line_list]
        # ))

        # Find sight line with the worst match
        mismatch_list = sight_line_mismatch_list(trajectory=best_triangulation)
        maximum_mismatch = max(mismatch_list)

        # Reject trajectory if it deviates by more than 8 degrees from any observation
        if maximum_mismatch > 8:
            logging.info("{prefix} -- Trajectory mismatch is too great ({x:.1f} deg).".
                         format(prefix=logging_prefix,
                                x=maximum_mismatch
                                ))
            continue

        # Convert start and end points of path into (lat, lng, alt)
        start_point = best_triangulation.point(0).to_lat_lng(utc=None)
        start_point['utc'] = time_span[0]
        end_point = best_triangulation.point(1).to_lat_lng(utc=None)
        end_point['utc'] = time_span[1]

        # Calculate linear speed of object
        speed = abs(best_triangulation.direction) / (time_span[1] - time_span[0])  # m/s

        # Calculate radiant direction for this object
        radiant_direction_vector = best_triangulation.direction * -1
        radiant_direction_coordinates = radiant_direction_vector.to_ra_dec()  # hours, degrees
        radiant_greenwich_hour_angle = radiant_direction_coordinates['ra']
        radiant_dec = radiant_direction_coordinates['dec']
        instantaneous_sidereal_time = sidereal_time(utc=(utc_min + utc_max) / 2)  # hours
        radiant_ra = radiant_greenwich_hour_angle + instantaneous_sidereal_time  # hours
        radiant_direction = [radiant_ra, radiant_dec]

        # Store triangulated information in database
        user = settings['pigazingUser']
        timestamp = time.time()
        triangulation_metadata = {
            "triangulation:speed": speed,
            "triangulation:mean_altitude": (start_point['alt'] + end_point['alt']) / 2,
            "triangulation:max_angular_offset": maximum_mismatch,
            "triangulation:max_baseline": maximum_baseline,
            "triangulation:radiant_direction": json.dumps(radiant_direction),
            "triangulation:sight_line_count": len(sight_line_list),
            "triangulation:path": json.dumps([start_point, end_point])
        }

        # Set metadata on the observation group
        for metadata_key, metadata_value in triangulation_metadata.items():
            db.set_obsgroup_metadata(user_id=user, group_id=group_info['groupId'], utc=timestamp,
                                     meta=mp.Meta(key=metadata_key, value=metadata_value))

        # Set metadata on each observation individually
        for item in obs_groups[group_info['groupId']]:
            for metadata_key, metadata_value in triangulation_metadata.items():
                db.set_observation_metadata(user_id=user, observation_id=item['observationId'], utc=timestamp,
                                            meta=mp.Meta(key=metadata_key, value=metadata_value))

        # Commit metadata to database
        db.commit()

        # Report outcome
        logging.info("{prefix} -- Success -- {path}; speed {mph:11.1f} mph; {sight_lines:6d} detections.".
                     format(prefix=logging_prefix,
                            path="{:5.1f} {:5.1f} {:10.0f} -> {:5.1f} {:5.1f} {:10.0f}".format(
                                start_point['lat'], start_point['lng'], start_point['alt'],
                                end_point['lat'], end_point['lng'], end_point['alt']
                            ),
                            mph=speed / 0.44704,
                            sight_lines=len(sight_line_list)
                            ))

        # Triangulation successful
        outcomes['successful_fits'] += 1

        # Update database
        db.commit()

    # Report how many fits we achieved
    logging.info("{:d} objects successfully triangulated.".format(outcomes['successful_fits']))
    logging.info("{:d} malformed database records.".format(outcomes['error_records']))
    logging.info("{:d} rescued database records.".format(outcomes['rescued_records']))
    logging.info("{:d} objects with incomplete data.".format(outcomes['insufficient_information']))

    # Commit changes
    db.commit()
    db.close_db()


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

    # Delete group metadata fields that start 'triangulation:*'
    conn.execute("""
DELETE m
FROM archive_metadata m
INNER JOIN archive_obs_groups o ON m.groupId = o.uid
WHERE
    fieldId IN (SELECT uid FROM archive_metadataFields WHERE metaKey LIKE 'triangulation:%%') AND
    o.time BETWEEN %s AND %s;
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
                        format='[%(asctime)s] %(levelname)s:%(filename)20s:%(message)s',
                        datefmt='%d/%m/%Y %H:%M:%S',
                        handlers=[
                            logging.FileHandler(os.path.join(settings['pythonPath'], "../datadir/pigazing.log")),
                            logging.StreamHandler()
                        ])
    logger = logging.getLogger(__name__)
    logger.info(__doc__.strip())

    # If flush option was specified, then delete all existing triangulations
    if args.flush:
        flush_triangulation(utc_min=args.utc_min,
                            utc_max=args.utc_max)

    # Triangulate groups of videos
    do_triangulation(utc_min=args.utc_min,
                     utc_max=args.utc_max,
                     utc_must_stop=args.stop_by)
