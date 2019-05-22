#!/bin/python3
# -*- coding: utf-8 -*-
# pigazing_application.wsgi
#
# -------------------------------------------------
# Copyright 2015-2019 Dominic Ford
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
WSGI application for serving the Pi Gazing web API
"""

import logging
import sys

from pigazing_helpers.obsarchive import obsarchive_server, admin_api, importer_api, query_api
from pigazing_helpers.settings_read import settings, installation_info

logging.basicConfig(stream=sys.stderr)

# Configure and create database and server objects
file_store_path = settings['dbFilestore']
pigazing_app = obsarchive_server.ObservationApp(file_store_path=file_store_path,
                                                db_host=installation_info['mysqlHost'],
                                                db_user=installation_info['mysqlUser'],
                                                db_password=installation_info['mysqlPassword'],
                                                db_name=installation_info['mysqlDatabase'],
                                                obstory_id=installation_info['observatoryId'])

# Add routes
admin_api.add_routes(obsarchive_app=pigazing_app)
importer_api.add_routes(obsarchive_app=pigazing_app)
query_api.add_routes(obsarchive_app=pigazing_app)

# Expose WSGI application as 'application'
application = pigazing_app.app
