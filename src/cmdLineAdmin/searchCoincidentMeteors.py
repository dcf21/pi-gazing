#!../../virtual-env/bin/python
# searchCoincidentMeteors.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# Search the database for moving objects seen at similar times by multiple observatories. Create observation group
# objects to describe the coincidences.

import sys
import time

import meteorpi_db
import meteorpi_model as mp

import mod_astro
import mod_settings


def fetch_option(title, default):
    value = raw_input('Set %s <default %s>: ' % (title, default))
    if not value:
        value = default
    return value

semantic_type = "coincidence"

# Fetch default search parameters
db = meteorpi_db.MeteorDatabase(mod_settings.settings['dbFilestore'])

obstory_name = "Cambridge-South-East"  # Association high water marks with this name
margin = 3  # Number of seconds offset allowed between coincident detections

utc_min = db.get_high_water_mark(mark_type="coincidenceSearch",
                                 obstory_name=obstory_name)
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
triggers = db.search_observations(search)
triggers = triggers['obs']
triggers.sort(key=lambda x: x.obs_time)

# Search for coincidences
coincidences = []
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
        coincidences.append({'time': utc,
                             'obstory_list': obstory_list,
                             'time_spread': triggers[group_max].obs_time - triggers[group_min].obs_time,
                             'ids': [triggers[x].id for x in range(group_min, group_max + 1)]})
        complete_to = group_max

print "%6d existing observation groups within this time period (will be deleted)." % (len(existing_groups))
print "%6d moving objects seen within this time period" % (len(triggers))
print "%6d coincident detections found." % (len(coincidences))

for item in coincidences:
    print "%s -- %3d stations (time spread %.1f sec)" % (mod_astro.time_print(item['time']),
                                                         len(item['obstory_list']),
                                                         item['time_spread'])

# Get user confirmation to proceed
confirm = raw_input('Replace with default configuration? (Y/N) ')
if confirm not in 'Yy':
    sys.exit(0)

# Delete existing observation groups
for item in existing_groups:
    db.delete_obsgroup(item.id)

# Create new observation groups
for item in coincidences:
    db.register_obsgroup(title="Multi-station detection", user_id="system", semantic_type=semantic_type,
                         obs_time=item['time'], set_time=creation_time,
                         obs=item['ids'])

# Commit changes
db.commit()
