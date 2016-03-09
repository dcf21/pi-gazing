#!../../virtual-env/bin/python
# searchCoincidentDetections.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# Search the database for moving objects seen at similar times by multiple observatories. Create observation group
# objects to describe the coincidences.

import sys
import time
import json
from math import tan, atan, pi

import meteorpi_db
import meteorpi_model as mp

import mod_astro
import mod_gnomonic
import mod_settings


def fetch_option(title, default):
    value = raw_input('Set %s <default %s>: ' % (title, default))
    if not value:
        value = default
    return value


semantic_type = "simultaneous"

# Fetch default search parameters
db = meteorpi_db.MeteorDatabase(mod_settings.settings['dbFilestore'])

obstory_hwm_name = "Cambridge-South-East"  # Association high water marks with this name
margin = 3  # Number of seconds offset allowed between coincident detections

utc_min = db.get_high_water_mark(mark_type="simultaneousDetectionSearch",
                                 obstory_name=obstory_hwm_name)
utc_max = time.time()
creation_time = time.time()

if utc_min is None:
    utc_min = 0

# Allow user to override search parameters
utc_min = fetch_option("start time", utc_min)
utc_max = fetch_option("stop time", utc_max)

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

# Search for coincident object detections
groups = []
complete_to = 0
for i in range(len(triggers)):
    if i <= complete_to:
        continue
    obstory_list = [triggers[i].obstory_id]
    utc = triggers[i].obs_time
    group_min = group_max = i
    while (group_min > 0) and (triggers[group_min - 1].obs_time > utc - margin):
        group_min -= 1
        if triggers[group_min].obstory_id not in obstory_list:
            obstory_list.append(triggers[group_min].obstory_id)
    while (group_max < len(triggers) - 1) and (triggers[group_max + 1].obs_time < utc + margin):
        group_max += 1
        if triggers[group_max].obstory_id not in obstory_list:
            obstory_list.append(triggers[group_max].obstory_id)

    # We have found a coincident detection if multiple observatories saw an event at the same time
    if len(obstory_list) > 1:
        groups.append({'time': utc,
                       'obstory_list': obstory_list,
                       'time_spread': triggers[group_max].obs_time - triggers[group_min].obs_time,
                       'triggers': [{'obs': triggers[x]} for x in range(group_min, group_max + 1)],
                       'ids': [triggers[x].id for x in range(group_min, group_max + 1)]})
        complete_to = group_max

print "%6d existing observation groups within this time period (will be deleted)." % (len(existing_groups))
print "%6d moving objects seen within this time period" % (len(triggers_raw['obs']))
print "%6d moving objects rejected because tagged as junk" % (len(triggers_raw['obs']) - len(triggers))
print "%6d coincident detections found." % (len(groups))

for item in groups:
    print "%s -- %3d stations (time spread %.1f sec)" % (mod_astro.time_print(item['time']),
                                                         len(item['obstory_list']),
                                                         item['time_spread'])

# Get user confirmation to proceed
confirm = raw_input('Replace with newly found coincident detections? (Y/N) ')
if confirm not in 'Yy':
    sys.exit(0)

# Delete existing observation groups
for item in existing_groups:
    db.delete_obsgroup(item.id)

# Loop over list of simultaneous event detections
for item in groups:
    # Create new observation group
    group = db.register_obsgroup(title="Multi-station detection", user_id="system", semantic_type=semantic_type,
                                 obs_time=item['time'], set_time=creation_time,
                                 obs=item['ids'])

    # Attempt to triangulate object
    triangulations = []

    # Work out position of each observatory, and centre of field of view of each observatory
    for trigger in item['triggers']:
        # Look up information about observatory
        obs = trigger['obs']
        obstory_id = obs.obstory_id
        obstory_name = db.get_obstory_from_id(obstory_id)['name']
        obstory_status = db.get_obstory_status(time=obs.obs_time, obstory_name=obstory_name)
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
                                                            utc=obs.obs_time)

        # Calculate the celestial coordinates of the centre of the frame
        [ra0, dec0] = mod_astro.ra_dec(alt=obstory_status['orientation_altitude'],
                                       az=obstory_status['orientation_azimuth'],
                                       utc=obs.obs_time,
                                       latitude=obstory_status['latitude'],
                                       longitude=obstory_status['longitude'])

        # Loop up pixel positions of start/end of object's trail across the frame
        [x_a, y_a, utc_a] = path[0]
        [x_b, y_b, utc_b] = path[2]

        # Convert these to celestial coordinates
        size_x = obstory_status['sensor_width']
        size_y = obstory_status['sensor_height']
        scale_x = obstory_status['orientation_width_field'] * pi / 180
        scale_y = 2 * atan(tan(scale_x / 2) * size_y / size_x)

        # For each positional fix on object, convert pixel coordinates into celestial coordinates
        detected_direction_list = []
        for point in path:
            [ra, dec] = mod_gnomonic.inv_gnom_project(ra0=ra0, dec0=dec0,
                                                      x=point[0], y=point[1],
                                                      size_x=size_x, size_y=size_y,
                                                      scale_x=scale_x, scale_y=scale_y,
                                                      pos_ang=obstory_status['orientation_pa'],
                                                      bca=bca, bcb=bcb, bcc=bcc)
            direction = mod_astro.Vector.from_ra_dec(ra, dec)
            detected_direction_list.append({
                'ra': ra,
                'dec': dec,
                'utc': point[2],
                'direction': direction,
                'line': mod_astro.Line(observatory_position, direction)
            })

        # Get plane containing direction of start and end of path
        object_plane = detected_direction_list[0]['line'].to_plane(detected_direction_list[-1]['direction'])

        # Store calculated information about observation
        trigger['observatory_position'] = observatory_position
        trigger['detected_direction_list'] = detected_direction_list
        trigger['object_plane'] = object_plane
        trigger['can_triangulate'] = True

    # Make a list of all pairs of observations
    triggers = [i for i in item['triggers'] if 'can_triangulate' in i]
    pairs = [[triggers[i], triggers[j]] for i in range(len(triggers) - 1) for j in range(i + 1, len(triggers) - 1)]

    # Make a triangulation based on each pair
    for pair in pairs:
        planeA = pair[0]['object_plane']
        planeB = pair[1]['object_plane']
        object_trajectory = planeA.line_of_intersection(planeB)
        triangulations.append(object_trajectory)

    # Average triangulations to find best fit line
    best_triangulation = mod_astro.Line.average_from_list(triangulations)
    object_direction_ra_dec = best_triangulation.direction.to_ra_dec()

    # Add triangulation information to each observation
    for trigger in item['triggers']:
        if 'can_triangulate' in trigger:
            detected_position_list = []
            detected_position_info = []
            for item in trigger['detected_direction_list']:
                sight_line = item['line']
                observatory_position = sight_line.x0
                object_position = best_triangulation.find_intersection(sight_line)
                object_lat_lng = object_position.to_lat_lng(item['utc'])
                object_distance = abs(object_position.displacement_vector_from(object_position))
                detected_position_list.append(object_position)
                detected_position_info.append({'ra': item['ra'],
                                               'dec': item['dec'],
                                               'utc': item['utc'],
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

            # Store triangulated information in database
            meta_item = mp.Meta("triangulation",json.dumps(triangulation))
            db.set_observation_metadata(observation_id=trigger['obs'].id,
                                        meta=meta_item,
                                        user_id=mod_settings.settings['meteorpiUser'])

# Set high water mark
db.set_high_water_mark(mark_type="simultaneousDetectionSearch",
                       obstory_name=obstory_hwm_name,
                       time=utc_max)

# Commit changes
db.commit()
