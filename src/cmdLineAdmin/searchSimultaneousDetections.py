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
import scipy.optimize

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
        maximum_obstory_spacing = 0

        # Work out locations of all observatories which saw this event
        obstory_locs = []
        for obstory_id in obstory_list:
            obstory_info = db.get_obstory_from_id(obstory_id)
            obstory_loc = mod_astro.Point.from_lat_lng(lat=obstory_info['latitude'],
                                                       lng=obstory_info['longitude'],
                                                       alt=0,
                                                       utc=(utc_min + utc_max) / 2
                                                       )
            obstory_locs.append(obstory_loc)

        # Check the distances between all pairs of observatories
        pairs = [[obstory_locs[i],obstory_locs[j]]
                 for i in range(len(obstory_list))
                 for j in range(i + 1, len(obstory_list))
                 ]
        for pair in pairs:
            maximum_obstory_spacing = max(maximum_obstory_spacing,
                                          pair[0].displacement_vector_from(pair[1]))

        # Reject event if it was not seen by any observatories more than 400 metres apart
        if maximum_obstory_spacing > 400:
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

    # We do all positional astronomy in the frame of the Earth geocentre.
    # This means that all speeds are measured in the non-rotating frame of the centre of the Earth.
    group_time = item['time']

    # Attempt to triangulate object
    all_sight_lines = []

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

        # Look up size of image frame
        size_x = obstory_status['sensor_width']
        size_y = obstory_status['sensor_height']
        scale_x = obstory_status['orientation_width_x_field'] * pi / 180
        scale_y = obstory_status['orientation_width_y_field'] * pi / 180
        # scale_y = 2 * atan(tan(scale_x / 2) * size_y / size_x)

        # For each positional fix on object, convert pixel coordinates into celestial coordinates
        sight_line_list = []
        for point in path:
            utc = point[2]

            # Look up the physical position of the observatory
            if 'altitude' in obstory_status:
                altitude = obstory_status['altitude']
            else:
                altitude = 0
            observatory_position = mod_astro.Point.from_lat_lng(lat=obstory_status['latitude'],
                                                                lng=obstory_status['longitude'],
                                                                alt=altitude,
                                                                utc=utc)

            # Calculate the celestial coordinates of the centre of the frame
            [ra0, dec0] = mod_astro.ra_dec(alt=obstory_status['orientation_altitude'],
                                           az=obstory_status['orientation_azimuth'],
                                           utc=utc,
                                           latitude=obstory_status['latitude'],
                                           longitude=obstory_status['longitude'])
            ra0_rad = ra0 * pi / 12  # Convert hours into radians
            dec0_rad = dec0 * pi / 180  # Convert degrees into radians

            # Convert orientation_pa into position angle of the centre of the field of view
            # This is the position angle of the zenith, clockwise from vertical, at the centre of the frame
            # If the camera is roughly upright, this ought to be close to zero!
            camera_tilt = obstory_status['orientation_pa']

            # Get celestial coordinates of the local zenith
            ra_dec_zenith = mod_astro.get_zenith_position(lat=obstory_status['latitude'],
                                                          lng=obstory_status['longitude'],
                                                          utc=utc)
            ra_zenith = ra_dec_zenith['ra']
            dec_zenith = ra_dec_zenith['dec']

            # Work out the position angle of the zenith, counterclockwise from north, as measured at centre of frame
            zenith_pa = mod_gnomonic.position_angle(ra0, dec0, ra_zenith, dec_zenith)

            # Work out the position angle of the upward vector in the centre of the image, counterclockwise
            # from celestial north.
            celestial_pa = zenith_pa - camera_tilt

            # Work out the RA and Dec of the point where the object was spotted
            [ra, dec] = mod_gnomonic.inv_gnom_project(ra0=ra0_rad, dec0=dec0_rad,
                                                      x=point[0], y=point[1],
                                                      size_x=size_x, size_y=size_y,
                                                      scale_x=scale_x, scale_y=scale_y,
                                                      pos_ang=celestial_pa * pi / 180,
                                                      bca=bca, bcb=bcb, bcc=bcc)
            ra *= 12 / pi  # Convert RA into hours
            dec *= 180 / pi  # Convert Dec into degrees
            direction = mod_astro.Vector.from_ra_dec(ra, dec)
            sight_line = mod_astro.Line(observatory_position, direction)
            sight_line_descriptor = {
                'ra': ra,
                'dec': dec,
                'utc': point[2],
                'obs_position': observatory_position,
                'line': sight_line
            }
            sight_line_list.append(sight_line_descriptor)
            all_sight_lines.append(sight_line_descriptor)

            log_txt("Observatory <%s> is pointing at (alt %.2f; az %.2f; tilt %.2f; PA %.2f) "
                    "and (RA %.3f h; Dec %.2f deg). "
                    "ScaleX = %.1f deg. ScaleY = %.1f deg." %
                    (obstory_id,
                     obstory_status['orientation_altitude'], obstory_status['orientation_azimuth'],
                     celestial_pa, obstory_status['orientation_pa'],
                     ra0, dec0,
                     scale_x * 180 / pi, scale_y * 180 / pi))
            log_txt("Observatory <%s> saw object at RA %.3f h; Dec %.3f deg, with sight line %s." %
                    (obstory_id, ra, dec, sight_line))

        # Store calculated information about observation
        trigger['sight_line_list'] = sight_line_list

    # If we don't have fewer than six sight lines, don't bother trying to triangulate
    if len(all_sight_lines) < 6:
        log_txt("Giving up triangulation as we only have %d sight lines to object." % (len(all_sight_lines)))
        continue


    # Work out the sum of square angular mismatches of sightlines to a test trajectory
    def line_from_parameters(p):
        x0 = mod_astro.Point(p[0] * 1000, p[1] * 1000, 0)
        d = mod_astro.Vector.from_ra_dec(p[2], p[3])
        trajectory = mod_astro.Line(x0=x0, direction=d)
        return trajectory


    def angular_mismatch_slave(p):
        trajectory = line_from_parameters(p)
        mismatch = 0
        for sight in all_sight_lines:
            closest_point = trajectory.find_closest_approach(sight)
            mismatch += closest_point['angular_distance']
        return mismatch


    params_initial = [0, 0, 0, 0]
    params_optimised = scipy.optimize.minimize(angular_mismatch_slave, params_initial, method='nelder-mead',
                                               options={'xtol': 1e-7, 'disp': False, 'maxiter': 1e6, 'maxfev': 1e6}
                                               ).x
    best_triangulation = line_from_parameters(params_optimised)
    log_txt("Best fit path of object through space is %s." % best_triangulation)

    log_txt("Mismatch of observed sight lines from trajectory are %s deg." %
            (["%.1f" % best_triangulation.find_closest_approach(s)['angular_distance'] for s in all_sight_lines]))

    maximum_mismatch = max([best_triangulation.find_closest_approach(s)['angular_distance'] for s in all_sight_lines])

    # Reject trajectory if it deviates by more than 3 degrees from any observation
    if maximum_mismatch > 3:
        log_txt("Mismatch is too great. Trajectory fit is rejected.")
        continue

    # Add triangulation information to each observation
    for trigger in item['triggers']:
        if 'sight_line_list' in trigger:
            detected_position_info = []
            for detection in trigger['detected_direction_list']:
                sight_line = detection['line']
                observatory_position = detection['obs_position']
                object_position = best_triangulation.find_closest_approach(sight_line)
                object_lat_lng = object_position['self_point'].to_lat_lng(detection['utc'])
                object_distance = abs(object_position['self_point'].displacement_vector_from(observatory_position))
                detection['object_position'] = observatory_position
                detected_position_info.append({'ra': detection['ra'],
                                               'dec': detection['dec'],
                                               'utc': detection['utc'],
                                               'lat': object_lat_lng['lat'],
                                               'lng': object_lat_lng['lng'],
                                               'alt': object_lat_lng['alt'],
                                               'dist': object_distance,
                                               'ang_mismatch': observatory_position['angular_distance']
                                               })

            # Make descriptor of triangulated information
            trigger_0 = trigger['detected_direction_list'][0]
            trigger_1 = trigger['detected_direction_list'][-1]
            obs_position_0 = trigger_0['obs_position']  # Position of observatory at first sighting
            obj_position_0 = trigger_0['object_position']  # Position of object at first sighting
            utc_0 = trigger_0['utc']
            obs_position_1 = trigger_1['obs_position']  # Position of observatory at last sighting
            obj_position_1 = trigger_1['object_position']  # Position of object at last sighting
            utc_1 = trigger_1['utc']

            # Work out speed of object relative to centre of the Earth
            displacement_geocentre_frame = obj_position_1.displacement_vector_from(obj_position_0)
            time_span = utc_1 - utc_0
            speed_geocentre_frame = abs(displacement_geocentre_frame / time_span)
            object_direction_geocentre_frame = best_triangulation.direction.to_ra_dec()

            # Work out speed of object relative to observer
            point_0_obs_frame = obj_position_0.displacement_vector_from(obs_position_0)
            point_1_obs_frame = obj_position_1.displacement_vector_from(obs_position_1)
            displacement_obs_frame = point_1_obs_frame - point_0_obs_frame
            speed_obs_frame = abs(displacement_obs_frame / time_span)
            object_direction_obs_frame = displacement_obs_frame.direction.to_ra_dec()

            triangulation_info = {'observer_frame_heading_ra': object_direction_obs_frame['ra'],
                                  'observer_frame_heading_dec': object_direction_obs_frame['dec'],
                                  'observer_frame_speed': speed_obs_frame,
                                  'geocentre_heading_ra': object_direction_geocentre_frame['ra'],
                                  'geocentre_heading_dec': object_direction_geocentre_frame['dec'],
                                  'geocentre_speed': speed_geocentre_frame,
                                  'position_list': detected_position_info}
            log_txt("Triangulated details of observation <%s> is %s." % (trigger['obs'].id, triangulation_info))

            # Store triangulated information in database
            meta_item = mp.Meta("triangulation", json.dumps(triangulation_info))
            db.set_observation_metadata(observation_id=trigger['obs'].id,
                                        meta=meta_item,
                                        user_id=mod_settings.settings['meteorpiUser'])

# Set high water mark
db.set_high_water_mark(mark_type="simultaneousDetectionSearch",
                       obstory_name=obstory_hwm_name,
                       time=utc_max)

# Commit changes
db.commit()
