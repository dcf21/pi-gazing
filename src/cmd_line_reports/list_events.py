#!../../virtualenv/bin/python3
# -*- coding: utf-8 -*-
# list_events.py
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
Lists all of the moving objects recorded by an observatory between given unix times
"""

import sys
import time

import meteorpi_db
import meteorpi_model as mp

from meteorpi_helpers import dcf_ast
from meteorpi_helpers import settings_read
import installation_info

utc_min = time.time() - 3600 * 24
utc_max = time.time()
obstory_name = installation_info.local_conf['observatoryName']
label = ""
img_type = ""
stride = 1

if len(sys.argv) > 1:
    utc_min = float(sys.argv[1])
if len(sys.argv) > 2:
    utc_max = float(sys.argv[2])
if len(sys.argv) > 3:
    obstory_name = sys.argv[3]
if len(sys.argv) > 4:
    label = sys.argv[4]
if len(sys.argv) > 5:
    img_type = sys.argv[5]
if len(sys.argv) > 6:
    stride = int(sys.argv[6])

if (utc_max == 0):
    utc_max = time.time()

print("# ./listEvents.py %f %f \"%s\" \"%s\" \"%s\" %d\n" % (utc_min, utc_max, obstory_name, label, img_type, stride))

db = meteorpi_db.MeteorDatabase(settings_read.settings['dbFilestore'])

try:
    obstory_info = db.get_obstory_from_name(obstory_name=obstory_name)
except ValueError:
    print("Unknown observatory <%s>. Run ./listObservatories.py to see a list of available observatories." % \
          obstory_name)
    sys.exit(0)

obstory_id = obstory_info['publicId']

search = mp.ObservationSearch(obstory_ids=[obstory_id],
                              time_min=utc_min, time_max=utc_max, limit=1000000)
triggers = db.search_observations(search)
triggers = triggers['obs']
triggers.sort(key=lambda x: x.obs_time)

print("Observatory <%s>" % obstory_name)
print("  * %d matching triggers in time range %s --> %s" % (len(triggers),
                                                            dcf_ast.date_string(utc_min),
                                                            dcf_ast.date_string(utc_max)))
for event in triggers:
    event_id = event.id
    duration = db.get_observation_metadata(event_id, "meteorpi:duration")
    peak_amplitude = db.get_observation_metadata(event_id, "meteorpi:amplitudePeak")
    if duration is None:
        duration = -1
    if peak_amplitude is None:
        peak_amplitude = -1
    print("  * [ID %s] %s -- Duration %5.1f sec -- Peak amplitude %7.1f" % (event_id,
        dcf_ast.date_string(event.obs_time), duration, peak_amplitude))
