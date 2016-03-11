#!../../virtual-env/bin/python
# searchSimultaneousDetections.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# Search the database for moving objects seen at similar times by multiple observatories. Create observation group
# objects to describe the simultaneous detections.

import sys
import time
import json
from math import tan, atan, pi

import meteorpi_db
import meteorpi_model as mp

import mod_astro
import mod_gnomonic
import mod_settings
from mod_log import log_txt


def fetch_option(title, default):
    value = raw_input('Set %s <default %s>: ' % (title, default))
    if not value:
        value = default
    return value


semantic_type = "simultaneous"

# Fetch default search parameters
db = meteorpi_db.MeteorDatabase(mod_settings.settings['dbFilestore'])

obstory_hwm_name = "Cambridge-South-East"  # Association high water marks with this name

utc_min = db.get_high_water_mark(mark_type="simultaneousDetectionSearch",
                                 obstory_name=obstory_hwm_name)
utc_max = time.time()
creation_time = time.time()

if utc_min is None:
    utc_min = 0

# Allow user to override search parameters
utc_min = float(fetch_option("start time", utc_min))
utc_max = float(fetch_option("stop time", utc_max))

# Search for existing observation groups
search = mp.ObservationGroupSearch(semantic_type=semantic_type,
                                   time_min=utc_min, time_max=utc_max, limit=1000000)
existing_groups = db.search_obsgroups(search)
existing_groups = existing_groups['obsgroups']

# Search for moving objects within time span
search = mp.ObservationSearch(observation_type="movingObject",
                              time_min=utc_min, time_max=utc_max, limit=1000000)
triggers_raw = db.search_observations(search)
triggers = [x for x in triggers_raw['obs'] if db.get_observation_metadata(x.id, "web:category") != "Junk"]
triggers.sort(key=lambda x: x.obs_time)

# Look up the duration of each trigger
for trigger in triggers:
    duration = 0
    for meta in trigger.meta:
        if meta.key == "meteorpi:duration":
            duration = meta.value
    trigger.duration = duration
    trigger.obs_time_end = trigger.obs_time + duration

# Search for simultaneous object detections
groups = []
triggers_used = [False for i in range(len(triggers))]
for i in range(len(triggers)):
    if triggers_used[i]:
        continue
    obstory_list = [triggers[i].obstory_id]
    utc_min = triggers[i].obs_time
    utc_max = triggers[i].obs_time_end
    triggers_used[i] = True
    prev_group_size = 0
    group_members = [i]

    while len(group_members) > prev_group_size:
        prev_group_size = len(group_members)
        for scan_direction in [-1, 1]:
            scan = i
            while ((scan >= 0) and (scan < len(triggers)) and (triggers[scan].obs_time_end > utc_min - 60)
                   and (triggers[scan].obs_time < utc_max + 60)):
                if not (triggers_used[scan] or (triggers[scan].obs_time > utc_max + 1)
                        or (triggers[scan].obs_time_end < utc_min - 1)):
                    group_members.append(scan)
                    utc_min = min(utc_min, triggers[scan].obs_time)
                    utc_max = max(utc_max, triggers[scan].obs_time_end)
                    if triggers[scan].obstory_id not in obstory_list:
                        obstory_list.append(triggers[scan].obstory_id)
                    triggers_used[scan] = True
                scan += scan_direction

    # We have found a coincident detection if multiple observatories saw an event at the same time
    if len(obstory_list) > 1:
        groups.append({'time': (utc_min + utc_max) / 2,
                       'obstory_list': obstory_list,
                       'time_spread': utc_max - utc_min,
                       'triggers': [{'obs': triggers[x]} for x in group_members],
                       'ids': [triggers[x].id for x in group_members]})

print "%6d existing observation groups within this time period (will be deleted)." % (len(existing_groups))
print "%6d moving objects seen within this time period" % (len(triggers_raw['obs']))
print "%6d moving objects rejected because tagged as junk" % (len(triggers_raw['obs']) - len(triggers))
print "%6d simultaneous detections found." % (len(groups))

for item in groups:
    print "%s -- %3d stations (time spread %.1f sec)" % (mod_astro.time_print(item['time']),
                                                         len(item['obstory_list']),
                                                         item['time_spread'])

# Get user confirmation to proceed
confirm = raw_input('Replace with newly found simultaneous detections? (Y/N) ')
if confirm not in 'Yy':
    sys.exit(0)

# Delete existing observation groups
for item in existing_groups:
    db.delete_obsgroup(item.id)

# Delete existing triangulation metadata
db.con.execute("""
DELETE m FROM archive_metadata m
INNER JOIN archive_observations o ON m.observationId = o.uid
WHERE
fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey LIKE 'triangulation%%') AND
o.obsTime>=%s AND o.obsTime<=%s;
""", (utc_min, utc_max))

log_txt("Triangulating simultaneous object detections between <%s> and <%s>." % (mod_astro.time_print(utc_min),
                                                                                 mod_astro.time_print(utc_max)))

# Loop over list of simultaneous event detections
for item in groups:
    # Create new observation group
    group = db.register_obsgroup(title="Multi-station detection", user_id="system", semantic_type=semantic_type,
                                 obs_time=item['time'], set_time=creation_time,
                                 obs=item['ids'])
    log_txt("Simultaneous detection at %s by %3d stations (time spread %.1f sec)" % (mod_astro.time_print(item['time']),
                                                                                     len(item['obstory_list']),
                                                                                     item['time_spread']))
    log_txt("Observation IDs: %s" % item['ids'])

    # We do all positional astronomy assuming the position of the observatory and stars at the middle of the event.
    # This means that all speeds are measured in the frame of the observer.
    # There is no displacement to object
    group_time = item['time']

    # Attempt to triangulate object
    triangulations = []

    # Work out position of each observatory, and centre of field of view of each observatory
    for trigger in item['triggers']:

        # Look up information about observatory
        obs = trigger['obs']
        obstory_id = obs.obstory_id
        obstory_name = db.get_obstory_from_id(obstory_id)['name']
        obstory_status = db.get_obstory_status(time=group_time, obstory_name=obstory_name)
        path_json = db.get_observation_metadata(obs.id, "meteorpi:pathBezier")
        if ((path_json is None) or ('lens_barrel_a' not in obstory_status) or ('latitude' not in obstory_status) or
                ('orientation_altitude' not in obstory_status)):
            continue
        bca = obstory_status['lens_barrel_a']
        bcb = obstory_status['lens_barrel_b']
        bcc = obstory_status['lens_barrel_c']
        path = json.loads(path_json)

        # Look up the physical position of the observatory
        observatory_position = mod_astro.Point.from_lat_lng(lat=obstory_status['latitude'],
                                                            lng=obstory_status['longitude'],
                                                            utc=group_time)

        # Calculate the celestial coordinates of the centre of the frame
        [ra0, dec0] = mod_astro.ra_dec(alt=obstory_status['orientation_altitude'],
                                       az=obstory_status['orientation_azimuth'],
                                       utc=group_time,
                                       latitude=obstory_status['latitude'],
                                       longitude=obstory_status['longitude'])
        ra0_rad = ra0 * pi / 12  # Convert hours into radians
        dec0_rad = dec0 * pi / 180  # Convert degrees into radians

        # Convert these to celestial coordinates
        size_x = obstory_status['sensor_width']
        size_y = obstory_status['sensor_height']
        scale_x = obstory_status['orientation_width_field'] * pi / 180
        scale_y = 2 * atan(tan(scale_x / 2) * size_y / size_x)

        # For each positional fix on object, convert pixel coordinates into celestial coordinates
        detected_direction_list = []
        for point in path:
            [ra, dec] = mod_gnomonic.inv_gnom_project(ra0=ra0_rad, dec0=dec0_rad,
                                                      x=point[0], y=point[1],
                                                      size_x=size_x, size_y=size_y,
                                                      scale_x=scale_x, scale_y=scale_y,
                                                      pos_ang=obstory_status['orientation_pa'],
                                                      bca=bca, bcb=bcb, bcc=bcc)
            ra *= 12 / pi  # Convert RA into hours
            dec *= 180 / pi  # Convert Dec into degrees
            direction = mod_astro.Vector.from_ra_dec(ra, dec)
            sight_line = mod_astro.Line(observatory_position, direction)
            detected_direction_list.append({
                'ra': ra,
                'dec': dec,
                'utc': point[2],
                'direction': direction,
                'line': sight_line
            })

            log_txt("Observatory <%s> is pointing at (alt %.2f; az %.2f; PA %.2f) and (RA %.3f h; Dec %.2f deg). "
                    "ScaleX = %.1f deg. ScaleY = %.1f deg." %
                    (obstory_id,
                     obstory_status['orientation_altitude'], obstory_status['orientation_azimuth'],
                     obstory_status['orientation_pa'],
                     ra0, dec0,
                     scale_x * 180 / pi, scale_y * 180 / pi))
            log_txt("Observatory <%s> saw object at RA %.3f h; Dec %.3f deg, with sight line %s." %
                    (obstory_id, ra, dec, sight_line))

        # Get plane containing direction of start and end of path
        object_plane = detected_direction_list[0]['line'].to_plane(detected_direction_list[-1]['direction'])
        log_txt("Observatory <%s> sight lines fit into plane in space: %s." % (obstory_id, object_plane))

        # Store calculated information about observation
        trigger['obs_position'] = observatory_position
        trigger['detected_direction_list'] = detected_direction_list
        trigger['object_plane'] = object_plane
        trigger['can_triangulate'] = True

    # Make a list of all pairs of observations
    triggers = [i for i in item['triggers'] if 'can_triangulate' in i]
    pairs = [[triggers[i], triggers[j], i, j] for i in range(len(triggers)) for j in range(i + 1, len(triggers))]

    # Make a triangulation based on each pair
    for pair in pairs:
        log_txt("Attempting triangulation on the basis of observations %d and %d." % (pair[2], pair[3]))
        planeA = pair[0]['object_plane']
        planeB = pair[1]['object_plane']
        object_trajectory = planeA.line_of_intersection(planeB)
        if object_trajectory is None:
            continue
        vector_between_observatories = pair[0]['obs_position'].displacement_vector_from(pair[1]['obs_position'])
        distance_between_observatories = abs(vector_between_observatories)
        log_txt("Distance between observatories is %s metres." % distance_between_observatories)
        if distance_between_observatories < 400:
            log_txt("Rejecting, because observatories are less than 400 metres apart.")
            continue
        log_txt("Triangulated path of object through space is %s." % object_trajectory)
        weighting = distance_between_observatories
        triangulations.append([object_trajectory, weighting])

    # If we don't have any valid triangulations, give up
    if len(triangulations) < 1:
        continue

    # Average triangulations to find best fit line
    best_triangulation = mod_astro.Line.average_from_list(triangulations)
    log_txt("Best fit path of object through space is %s." % best_triangulation)
    object_direction_ra_dec = best_triangulation.direction.to_ra_dec()

    # Add triangulation information to each observation
    for trigger in item['triggers']:
        if 'can_triangulate' in trigger:
            detected_position_list = []
            detected_position_info = []
            for detection in trigger['detected_direction_list']:
                sight_line = detection['line']
                observatory_position = trigger['obs_position']
                object_position = best_triangulation.find_intersection(sight_line)
                object_lat_lng = object_position.to_lat_lng(detection['utc'])
                object_distance = abs(object_position.displacement_vector_from(observatory_position))
                detected_position_list.append(object_position)
                detected_position_info.append({'ra': detection['ra'],
                                               'dec': detection['dec'],
                                               'utc': detection['utc'],
                                               'lat': object_lat_lng['lat'],
                                               'lng': object_lat_lng['lng'],
                                               'alt': object_lat_lng['alt'],
                                               'dist': object_distance})

            # Make descriptor of triangulated information
            distance_covered = detected_position_list[-1].displacement_vector_from(detected_position_list[0])
            time_span = detected_position_info[-1]['utc'] - detected_position_info[0]['utc']
            speed = abs(distance_covered / time_span)
            triangulation = {'heading_ra': object_direction_ra_dec['ra'],
                             'heading_dec': object_direction_ra_dec['dec'],
                             'speed': speed,
                             'position_list': detected_position_info}
            log_txt("Triangulated details of observation <%s> is %s." % (trigger['obs'].id, triangulation))

            # Store triangulated information in database
            meta_item = mp.Meta("triangulation", json.dumps(triangulation))
            db.set_observation_metadata(observation_id=trigger['obs'].id,
                                        meta=meta_item,
                                        user_id=mod_settings.settings['meteorpiUser'])

# Set high water mark
db.set_high_water_mark(mark_type="simultaneousDetectionSearch",
                       obstory_name=obstory_hwm_name,
                       time=utc_max)

# Commit changes
db.commit()
