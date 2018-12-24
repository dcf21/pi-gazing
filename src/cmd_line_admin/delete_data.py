#!../../virtualenv/bin/python3
# -*- coding: utf-8 -*-
# delete_data.py
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
Deletes all of the observations and files recorded by a particular observatory between two times.

Commandline syntax:
./deleteData.py t_min t_max observatory
"""

import argparse
import sys
import time

from pigazing_helpers import dcf_ast
from pigazing_helpers.obsarchive import obsarchive_db
from pigazing_helpers.obsarchive import obsarchive_model as mp
from pigazing_helpers.settings_read import settings, installation_info

# Read input parameters
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--t-min', dest='utc_min', default=time.time() - 3600 * 24,
                    type = float,
                    help="Only delete observations made after the specified unix time")
parser.add_argument('--t-max', dest='utc_max', default=time.time(),
                    type = float,
                    help="Only delete observations made before the specified unix time")
parser.add_argument('--observatory', dest='observatory', default=installation_info['observatoryId'],
                    help="ID of the observatory we are to delete observations from")
args = parser.parse_args()

print("# ./delete_data.py --t-min {:f} --t-max {:f} --observatory \"{}\"\n".format(args.utc_min,
                                                                                   args.utc_max,
                                                                                   args.observatory))

db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                       db_host=installation_info['mysqlHost'],
                                       db_user=installation_info['mysqlUser'],
                                       db_password=installation_info['mysqlPassword'],
                                       db_name=installation_info['mysqlDatabase'],
                                       obstory_id=installation_info['observatoryId'])

obstory_info = db.get_obstory_from_id(obstory_id=args.observatory)
if not obstory_info:
    print("Unknown observatory <{}>.\nRun ./list_observatories.py to see a list of available options.".
          format(args.observatory))
    sys.exit(0)

s = db.get_obstory_status(obstory_id=obstory_info['id'])
if not s:
    print("Unknown observatory <{}>.\nRun ./listObservatories.py to see a list of available options.".
          format(args.observatory))
    sys.exit(0)

search = mp.FileRecordSearch(obstory_ids=[args.observatory],
                             time_min=args.utc_min,
                             time_max=args.utc_max,
                             limit=1000000)
files = db.search_files(search)
files = [i for i in files['files']]
files.sort(key=lambda x: x.file_time)

search = mp.ObservationSearch(obstory_ids=[args.observatory],
                              time_min=args.utc_min,
                              time_max=args.utc_max,
                              limit=1000000)
observations = db.search_observations(search)
observations = observations['obs']
observations.sort(key=lambda x: x.obs_time)

print("Observatory <{}>".format(args.observatory))
print("  * {:6d} matching files in time range {} --> {}".format(len(files),
                                                                dcf_ast.date_string(args.utc_min),
                                                                dcf_ast.date_string(args.utc_max)))
print("  * {:6d} matching observations in time range".format(len(observations)))

confirmation = input('Delete these files? (Y/N) ')
if confirmation not in 'Yy':
    sys.exit(0)

db.clear_database(tmin=args.utc_min, tmax=args.utc_max, obstory_ids=[obstory_info['id']])

# Commit changes to database
db.commit()
