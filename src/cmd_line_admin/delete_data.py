#!../../virtualenv/bin/python3
# -*- coding: utf-8 -*-
# delete_data.py
#
# -------------------------------------------------
# Copyright 2015-2018 Dominic Ford
#
# This file is part of Meteor Pi.
#
# Meteor Pi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Meteor Pi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Meteor Pi.  If not, see <http://www.gnu.org/licenses/>.
# -------------------------------------------------

"""
Deletes all of the observations and files recorded by a particular observatory between two times.

Commandline syntax:
./deleteData.py t_min t_max observatory
"""

import os
import sys
import time

from meteorpi_helpers.obsarchive import archive_model as mp
from meteorpi_helpers.obsarchive import archive_db

from meteorpi_helpers import settings_read
from meteorpi_helpers import dcf_ast

pid = os.getpid()

utc_min = time.time() - 3600 * 24
utc_max = time.time()
observatory = installation_info.local_conf['observatoryName']

if len(sys.argv) > 1:
    utc_min = float(sys.argv[1])
if len(sys.argv) > 2:
    utc_max = float(sys.argv[2])
if len(sys.argv) > 3:
    observatory = sys.argv[3]

if utc_max == 0:
    utc_max = time.time()

print("# ./deleteData.py %f %f \"%s\"\n" % (utc_min, utc_max, observatory))

db = archive_db.MeteorDatabase(settings_read.settings['dbFilestore'])

obstory_info = db.get_obstory_from_id(obstory_id=observatory)
if not obstory_info:
    print("Unknown observatory <%s>.\nRun ./listObservatories.py to see a list of available options." % observatory)
    sys.exit(0)

obstory_name = obstory_info['name']

s = db.get_obstory_status(obstory_name=obstory_name)
if not s:
    print("Unknown observatory <%s>.\nRun ./listObservatories.py to see a list of available options." % observatory)
    sys.exit(0)

search = mp.FileRecordSearch(obstory_ids=[observatory],
                             time_min=utc_min,
                             time_max=utc_max,
                             limit=1000000)
files = db.search_files(search)
files = [i for i in files['files']]
files.sort(key=lambda x: x.file_time)

search = mp.ObservationSearch(obstory_ids=[observatory],
                              time_min=utc_min,
                              time_max=utc_max,
                              limit=1000000)
observations = db.search_observations(search)
observations = observations['obs']
observations.sort(key=lambda x: x.obs_time)

print("Observatory <%s>" % observatory)
print("  * %6d matching files in time range %s --> %s" % (len(files),
                                                          dcf_ast.time_print(utc_min),
                                                          dcf_ast.time_print(utc_max)))
print("  * %6d matching observations in time range" % (len(observations)))

confirmation = input('Delete these files? (Y/N) ')
if confirmation not in 'Yy':
    sys.exit(0)

db.clear_database(tmin=utc_min, tmax=utc_max, obstory_names=obstory_name)

# Commit changes to database
db.commit()
