#!../../virtual-env/bin/python
# create_hipparcos_json.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

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
