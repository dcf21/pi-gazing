#!../../virtual-env/bin/python
# create_hipparcos_json.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# -------------------------------------------------
# Copyright 2016 Cambridge Science Centre.

# This file is part of Meteor Pi.

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

# This script creates a JSON file of the coordinates of all stars brighter than mag 5.5
# The output file is <meteor-pi/src/lensCalibration/hipparcos_catalogue.json>.

import json

# Look up star positions
hipp_positions = {}
for line in open("/home/dcf21/svn_repository/StarPlot_ppl8/DataGenerated/HipparcosMerged/output/merged_hipp.dat"):
    words = line.split()
    hipp = int(words[12])
    ra = float(words[1])
    dec = float(words[2])
    mag = float(words[3])
    if (mag > 5.5):
        continue
    hipp_positions[hipp] = [ra, dec]

open("hipparcos_catalogue.json", "w").write(json.dumps(hipp_positions))
