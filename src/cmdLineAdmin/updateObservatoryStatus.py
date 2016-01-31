#!../../virtual-env/bin/python
# updateObservatoryStatus.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# This script is used to manually set up metadata about an observatory in the database.

# It is useful to run this after <sql/rebuild.sh> to specify the lens, camera, etc being used.

import os
import sys

import meteorpi_db
import meteorpi_model as mp

import mod_settings
import installation_info
import mod_hardwareProps

db = meteorpi_db.MeteorDatabase(mod_settings.settings['dbFilestore'])
hw = mod_hardwareProps.HardwareProps( os.path.join( mod_settings.settings['pythonPath'], "..", "sensorProperties") )

def fetch_option(title, key, indict, default, argv_index):
    if key in indict:
        default = indict[key]
    if (argv_index > 0) and (len(sys.argv) > argv_index):
        value = sys.argv[argv_index]
    else:
        value = raw_input('Set %s <default %s>: ' % (title, default))
    if not value:
        value = default
    return value


# List current observatory statuses
print "Current observatory statuses"
print "----------------------------"
obstory_list = db.get_obstory_names()
for obstory in obstory_list:
    print "%s\n" % obstory
    print "  * Observatory configuration"
    o = db.get_obstory_from_name(obstory)
    for item in ['latitude', 'longitude', 'name', 'publicId']:
        print "    * %s = %s" % (item, o[item])
    status = db.get_obstory_status(obstory_name=obstory)
    status_keys = status.keys()
    status_keys.sort()
    print "\n  * Additional metadata"
    for item in status_keys:
        print "    * %s = %s" % (item, status[item])
    print "\n"
if len(obstory_list)==0:
    print "None!\n"

print
print "Update or add an observatory"
print "----------------------------"

# Select observatory status to update
obstory = fetch_option(title="observatory to update",
                       key="_",
                       indict={},
                       default=installation_info.local_conf['observatoryName'],
                       argv_index=1)

if obstory not in obstory_list:
    obstory_id = fetch_option(title="observatory ID code",
                              key="observatoryId",
                              indict=installation_info.local_conf,
                              default="obs0",
                              argv_index=5)
    latitude = fetch_option(title="latitude",
                            key="latitude",
                            indict=installation_info.local_conf,
                            default=0,
                            argv_index=6)
    longitude = fetch_option(title="longitude",
                             key="longitude",
                             indict=installation_info.local_conf,
                             default=0,
                             argv_index=7)
    db.register_obstory(obstory_id=obstory_id,
                        obstory_name=obstory,
                        latitude=latitude,
                        longitude=longitude)
    db.register_obstory_metadata(obstory_name=obstory,
                                 key="latitude",
                                 value=installation_info.local_conf['latitude'],
                                 metadata_time=get_utc(),
                                 time_created=get_utc(),
                                 user_created=mod_settings.settings['meteorpiUser'])
    db.register_obstory_metadata(obstory_name=obstory_name,
                                 key="longitude",
                                 value=installation_info.local_conf['longitude'],
                                 metadata_time=get_utc(),
                                 time_created=get_utc(),
                                 user_created=mod_settings.settings['meteorpiUser'])
    db.register_obstory_metadata(obstory_name=obstory_name,
                                 key="location_source",
                                 value="manual",
                                 metadata_time=get_utc(),
                                 time_created=get_utc(),
                                 user_created=mod_settings.settings['meteorpiUser'])
    obstory_status = {}
else:
    obstory_status = db.get_obstory_status(obstory_id=obstory)

# Find out time that metadata update should be applied to
metadata_time = fetch_option(title="time stamp for update",
                             key="_",
                             indict={},
                             default=mp.now(),
                             argv_index=2)
metadata_time = float(metadata_time)

# Register software version in use
db.register_obstory_metadata(obstory_name=obstory,
                             key="softwareVersion",
                             value=mod_settings.settings['softwareVersion'],
                             metadata_time=metadata_time,
                             time_created=mp.now(),
                             user_created=mod_settings.settings['meteorpiUser'])

# Offer user options to update metadata
sensor = fetch_option(title="new sensor",
                      key="sensor",
                      indict=obstory_status,
                      default="watec_902h2_ultimate",
                      argv_index=3)
hw.update_sensor(db=db, obstory_name=obstory, utc=metadata_time, name=sensor)

lens = fetch_option(title="new lens",
                    key="lens",
                    indict=obstory_status,
                    default="VF-DCD-AI-3.5-18-C-2MP",
                    argv_index=4)
hw.update_lens(db=db, obstory_name=obstory, utc=metadata_time, name=lens)

# Commit changes to database
db.commit()
