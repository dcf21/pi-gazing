# meteorapplication.wsgi
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# Find path to this file
from os import path
www_path = path.split(path.abspath(__file__))[0]

# Activate python virtual environment with all the packages we need
activate_this = path.join(www_path,'../virtual-env/bin/activate_this.py')
execfile(activate_this, dict(__file__=activate_this))

import logging, sys
logging.basicConfig(stream=sys.stderr)


from meteorpi_server import MeteorApp, admin_api, importer_api, query_api

# Configure and create database and server objects
file_store_path = '/home/pi/meteor-pi/datadir/db_filestore'
binary_path = '/home/pi/meteor-pi/src/imageProjection/bin'
meteor_app = MeteorApp(file_store_path=file_store_path, binary_path=binary_path)

# Add routes
admin_api.add_routes(meteor_app=meteor_app)
importer_api.add_routes(meteor_app=meteor_app)
query_api.add_routes(meteor_app=meteor_app)

# Expose WSGI application as 'application'
application = meteor_app.app
