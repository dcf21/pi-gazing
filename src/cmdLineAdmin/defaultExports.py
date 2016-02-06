#!../../virtual-env/bin/python
# defaultExports.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# This script is used to set up an observatory to use the default export configuration specified in installation_info.py

# It is useful to run this after <sql/rebuild.sh>

import sys

import meteorpi_db
import meteorpi_model as mp

import mod_settings
import installation_info

db = meteorpi_db.MeteorDatabase(mod_settings.settings['dbFilestore'])

# List all current user accounts
print "Current export configurations"
print "-----------------------------"
configs = db.get_export_configurations()
for config in configs:
    print config.as_dict()
print "\n"

confirm = raw_input('Replace with default configuration? (Y/N) ')
if confirm not in 'Yy':
    sys.exit(0)

# Delete all export config
for config in configs:
    db.delete_export_configuration(config.config_id)

# Set up default observatory metadata export configuration
search = mp.ObservatoryMetadataSearch(limit=None)
config = mp.ExportConfiguration(target_url=installation_info.local_conf['exportURL'],
                                user_id=installation_info.local_conf['exportUsername'],
                                password=installation_info.local_conf['exportPassword'],
                                search=search, name="metadata_export",
                                description="Export all observatory metadata to remote server", enabled=True)
db.create_or_update_export_configuration(config)

# Set up default observation export configuration
search = mp.ObservationSearch(limit=None)
config = mp.ExportConfiguration(target_url=installation_info.local_conf['exportURL'],
                                user_id=installation_info.local_conf['exportUsername'],
                                password=installation_info.local_conf['exportPassword'],
                                search=search, name="obs_export",
                                description="Export all observation objects to remote server", enabled=True)
db.create_or_update_export_configuration(config)

# Set up default file export configuration
search = mp.FileRecordSearch(limit=None)
config = mp.ExportConfiguration(target_url=installation_info.local_conf['exportURL'],
                                user_id=installation_info.local_conf['exportUsername'],
                                password=installation_info.local_conf['exportPassword'],
                                search=search, name="file_export",
                                description="Export all image files to remote server", enabled=True)
db.create_or_update_export_configuration(config)

# Commit changes to database
db.commit()
