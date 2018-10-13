#!../../virtualenv/bin/python3
# -*- coding: utf-8 -*-
# recalculate_sky_clarity.py
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
Recomputes the sky clarity of all images in a given time range. This generally only needs to be done when there's a
change in the algorithm used to calculate sky clarity
"""

import os, subprocess
import time
import sys

from meteorpi_helpers import dcf_ast
from meteorpi_helpers import settings_read

from meteorpi_helpers.obsarchive import archive_model as mp
from meteorpi_helpers.obsarchive import archive_db

db = archive_db.MeteorDatabase(settings_read.settings['dbFilestore'])

utc_min = 0
utc_max = time.time()

argc = len(sys.argv)
if argc > 1:
    utc_min = float(sys.argv[1])
if argc > 2:
    utc_max = float(sys.argv[2])

print("# ./recalculateSkyClarity.py %s %s\n" % (utc_min, utc_max))

search = mp.FileRecordSearch(time_min=utc_min, time_max=utc_max, limit=10000000)
files = db.search_files(search)
files = files['files']
files.sort(key=lambda x: x.file_time)
print("  * %d matching files in time range %s --> %s" % (len(files),
                                                         dcf_ast.time_print(utc_min),
                                                         dcf_ast.time_print(utc_max)))


def report_line(file, text):
    print("%s %s -- %s" % (dcf_ast.time_print(file.file_time), file.id, text))


sky_clarity_tool = os.path.join(settings_read.settings['pythonPath'],
                                "../observatoryControl/videoAnalysis/bin/skyClarity")


def get_sky_clarity(file_path, noise_level):
    global sky_clarity_tool
    new_value = subprocess.check_output([sky_clarity_tool, file_path, str(noise_level)])
    try:
        output = float(new_value)
    except ValueError:
        output = -1
    return output


# Switch this on to produce diagnostic images in /tmp to show the sky clarity metrics of sample images
produce_diagnostic_images = False
threshold_sky_clarity = 5
filename_format = "/tmp/sky_clarity_%d_%%08d.png" % (os.getpid())

img_num = 1
for file in files:
    sky_clarity = None
    noise_level = None
    if file.mime_type != "image/png":
        report_line(file, "Ignore. Wrong mime type <%s>" % file.mime_type)
        continue
    for meta in file.meta:
        if meta.key == "meteorpi:skyClarity":
            sky_clarity = meta.value
        if meta.key == "meteorpi:stackNoiseLevel":
            noise_level = meta.value
    if sky_clarity is None:
        report_line(file, "Ignore. Sky clarity is not set on file with semantic type <%s>" % file.semantic_type)
        continue
    if noise_level is None:
        report_line(file, "Ignore. Noise level; is not set on file with semantic type <%s>" % file.semantic_type)
        continue
    new_sky_clarity = get_sky_clarity(db.file_path_for_id(file.id), noise_level)
    report_line(file, "Update sky clarity from %8.3f to %8.3f. Semantic type <%s>" % (sky_clarity, new_sky_clarity,
                                                                                      file.semantic_type))

    if produce_diagnostic_images and (new_sky_clarity>=threshold_sky_clarity):
        os.system("convert %s -gravity SouthEast -fill ForestGreen -pointsize 20 -font Ubuntu-Bold "
                  "-annotate +16+10 '%s - clarity %s' %s""" % (db.file_path_for_id(file.id), file.semantic_type,
                                                               new_sky_clarity, filename_format % img_num))
    img_num += 1
