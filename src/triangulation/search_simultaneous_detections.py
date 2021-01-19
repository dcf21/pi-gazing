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
    # Count how many simultaneous detections we discover
    simultaneous_detections_by_type = {}

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

        # Most events must be seen within a maximum offset of 1 second at different stations.
        # Planes are allowed an offset of up to 30 seconds due to their large parallax
        search_margin = 60
        match_margin = 30 if event.category == "Plane" else 1

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

        # Update tally of events by type
        if event.category not in simultaneous_detections_by_type:
            simultaneous_detections_by_type[event.category] = 0
        simultaneous_detections_by_type[event.category] += 1

        # Initialise maximum baseline between the stations which saw this objects
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

        # Work out maximum baseline between the stations which saw this objects
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

    # Report individual events we found
    for item in groups:
        logging.info("""
{time} -- {count:3d} stations; max baseline {baseline:5.0f} m; time spread {spread:4.1f} sec; type <{category}>
""".format(time=dcf_ast.date_string(item['time']),
           count=len(item['obstory_list']),
           baseline=item['geographic_spacing'],
           spread=item['time_spread'],
           category=item['category']).strip())

    # Report statistics on events we found
    logging.info("{:6d} moving objects seen within this time period".
                 format(len(events_raw['obs'])))
    logging.info("{:6d} moving objects rejected because they were unclassified".
                 format(len(events_raw['obs']) - len(events)))
    logging.info("{:6d} simultaneous detections found.".
                 format(len(groups)))

    # Report statistics by event type
    logging.info("Tally of simultaneous detections by type:")
    for event_type in sorted(simultaneous_detections_by_type.keys()):
        logging.info("    * {:32s}: {:6d}".format(event_type, simultaneous_detections_by_type[event_type]))

    # Record simultaneous event detections into the database
    for item in groups:
        # Create new observation group
        group = db.register_obsgroup(title="Multi-station detection", user_id="system",
                                     semantic_type=simultaneous_event_type,
                                     obs_time=item['time'], set_time=time.time(),
                                     obs=item['ids'])

        # logging.info("Simultaneous detection at {time} by {count:3d} stations (time spread {spread:.1f} sec)".
        #              format(time=dcf_ast.date_string(item['time']),
        #                     count=len(item['obstory_list']),
        #                     spread=item['time_spread']))
        # logging.info("Observation IDs: %s" % item['ids'])

        # Register group metadata
        timestamp = time.time()
        db.set_obsgroup_metadata(user_id="system", group_id=group.id, utc=timestamp,
                                 meta=mp.Meta(key="web:category", value=item['category']))
        db.set_obsgroup_metadata(user_id="system", group_id=group.id, utc=timestamp,
                                 meta=mp.Meta(key="simultaneous:time_spread", value=item['time_spread']))
        db.set_obsgroup_metadata(user_id="system", group_id=group.id, utc=timestamp,
                                 meta=mp.Meta(key="simulataneous:geographic_spread", value=item['geographic_spacing']))

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

    # Commit to database
    db.commit()


# If we're called as a script, run the method search_simultaneous_detections()
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
        flush_simultaneous_detections(utc_min=args.utc_min,
                                      utc_max=args.utc_max)

    # Calculate the orientation of images
    search_simultaneous_detections(utc_min=args.utc_min,
                                   utc_max=args.utc_max,
                                   utc_must_stop=args.stop_by)
