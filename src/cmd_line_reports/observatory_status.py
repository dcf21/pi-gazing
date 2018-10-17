#!../../virtualenv/bin/python3
# -*- coding: utf-8 -*-
# observatory_status.py
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
Lists all of the metadata updates posted by a particular observatory between two given unix times
"""

import time
import sys

import meteorpi_model as mp
import meteorpi_db

from meteorpi_helpers import dcf_ast
from meteorpi_helpers import settings_read

import installation_info

db = meteorpi_db.MeteorDatabase(settings_read.settings['dbFilestore'])

utc_min = time.time() - 3600 * 24
utc_max = time.time()
obstory_name = installation_info.local_conf['observatoryName']

argc = len(sys.argv)
if argc > 1:
    utc_min = float(sys.argv[1])
if argc > 2:
    utc_max = float(sys.argv[2])
if len(sys.argv) > 3:
    obstory_name = sys.argv[3]

if utc_max == 0:
    utc_max = time.time()

print("# ./observatoryStatus.py %f %f \"%s\"\n" % (utc_min, utc_max, obstory_name))

try:
 obstory_info = db.get_obstory_from_name(obstory_name=obstory_name)
except ValueError:
    print("Unknown observatory <%s>. Run ./listObservatories.py to see a list of available observatories." % \
          obstory_name)
    sys.exit(0)

obstory_id = obstory_info['publicId']
title = "Observatory <%s>" % obstory_name
print("\n\n%s\n%s" % (title, "-" * len(title)))

search = mp.ObservatoryMetadataSearch(obstory_ids=[obstory_id], time_min=utc_min, time_max=utc_max)
data = db.search_obstory_metadata(search)
data = data['items']
data.sort(key=lambda x: x.time)
print("  * %d matching metadata items in time range %s --> %s" % (len(data),
                                                                  dcf_ast.date_string(utc_min),
                                                                  dcf_ast.date_string(utc_max)))

# Check which items remain current
data.reverse()
keys_seen = []
for item in data:
    if item.key not in keys_seen:
        item.still_current = True
        keys_seen.append(item.key)
    else:
        item.still_current = False
data.reverse()

# Display list of items
for item in data:
    if item.still_current:
        current_flag = "+"
    else:
        current_flag = " "
    print("  * %s [ID %s] %s -- %16s = %s" % (current_flag, item.id, dcf_ast.date_string(item.time),
                                              item.key, item.value))
