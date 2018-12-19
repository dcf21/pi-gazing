# pigazing_application.wsgi
# Pi Gazing
# Dominic Ford

# Find path to this file
from os import path
www_path = path.split(path.abspath(__file__))[0]

# Activate python virtual environment with all the packages we need
activate_this = path.join(www_path,'../../../virtualenv/bin/activate_this.py')
execfile(activate_this, dict(__file__=activate_this))

import logging, sys
logging.basicConfig(stream=sys.stderr)


from pigazing_server import ObservationApp, admin_api, importer_api, query_api

# Configure and create database and server objects
file_store_path = '/home/pi/pi-gazing/datadir/db_filestore'
binary_path = '/home/pi/pi-gazing/src/imageProjection/bin'
pigazing_app = ObservationApp(file_store_path=file_store_path, binary_path=binary_path)

# Add routes
admin_api.add_routes(pigazing_app=pigazing_app)
importer_api.add_routes(pigazing_app=pigazing_app)
query_api.add_routes(pigazing_app=pigazing_app)

# Expose WSGI application as 'application'
application = pigazing_app.app
