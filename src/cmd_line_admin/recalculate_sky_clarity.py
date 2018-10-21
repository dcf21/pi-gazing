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

import argparse
import os
import subprocess
import time

from meteorpi_helpers import dcf_ast
from meteorpi_helpers.obsarchive import obsarchive_db
from meteorpi_helpers.obsarchive import obsarchive_model as mp
from meteorpi_helpers.settings_read import settings, installation_info

db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                       db_host=settings['mysqlHost'],
                                       db_user=settings['mysqlUser'],
                                       db_password=settings['mysqlPassword'],
                                       db_name=settings['mysqlDatabase'],
                                       obstory_id=installation_info['observatoryId'])

# Read input parameters
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--t-min', dest='utc_min', default=0,
                    type=float,
                    help="Only delete observations made after the specified unix time")
parser.add_argument('--t-max', dest='utc_max', default=time.time(),
                    type=float,
                    help="Only delete observations made before the specified unix time")
parser.add_argument('--observatory', dest='observatory', default=installation_info.local_conf['observatoryId'],
                    help="ID of the observatory we are to delete observations from")
args = parser.parse_args()

print("# ./recalculateSkyClarity.py {} {}\n".format(args.utc_min, args.utc_max))

search = mp.FileRecordSearch(time_min=args.utc_min, time_max=args.utc_max, limit=10000000)
files = db.search_files(search)
files = files['files']
files.sort(key=lambda x: x.file_time)
print("  * {:d} matching files in time range {} --> {}".format(len(files),
                                                               dcf_ast.date_string(args.utc_min),
                                                               dcf_ast.date_string(args.utc_max)))


def report_line(file_object, text):
    print("{} {} -- {}".format(dcf_ast.date_string(file_object.file_time), file_object.id, text))


sky_clarity_tool = os.path.join(settings['pythonPath'],
                                "../observatory_control/videoAnalysis/bin/skyClarity")


def get_sky_clarity(file_path, noise_level):
    global sky_clarity_tool
    new_value = subprocess.check_output([sky_clarity_tool, file_path, str(noise_level)]).decode('utf-8')
    try:
        output = float(new_value)
    except ValueError:
        output = -1
    return output


# Switch this on to produce diagnostic images in /tmp to show the sky clarity metrics of sample images
produce_diagnostic_images = False
threshold_sky_clarity = 5
filename_format = "/tmp/sky_clarity_{:d}_{{:08d}}.png".format(os.getpid())

img_num = 1
for file in files:
    sky_clarity = None
    noise_level = None
    if file.mime_type != "image/png":
        report_line(file, "Ignore. Wrong mime type <{}>".format(file.mime_type))
        continue
    for meta in file.meta:
        if meta.key == "meteorpi:skyClarity":
            sky_clarity = meta.value
        if meta.key == "meteorpi:stackNoiseLevel":
            noise_level = meta.value
    if sky_clarity is None:
        report_line(file, "Ignore. Sky clarity is not set on file with semantic type <{}>".format(file.semantic_type))
        continue
    if noise_level is None:
        report_line(file, "Ignore. Noise level; is not set on file with semantic type <{}>".format(file.semantic_type))
        continue
    new_sky_clarity = get_sky_clarity(db.file_path_for_id(file.id), noise_level)
    report_line(file, "Update sky clarity from {:8.3f} to {:8.3f}. Semantic type <{}>".format(sky_clarity,
                                                                                              new_sky_clarity,
                                                                                              file.semantic_type))

    if produce_diagnostic_images and (new_sky_clarity >= threshold_sky_clarity):
        os.system("convert {} -gravity SouthEast -fill ForestGreen -pointsize 20 -font Ubuntu-Bold "
                  "-annotate +16+10 '{} - clarity {}' {}""".format(db.file_path_for_id(file.id),
                                                                   file.semantic_type,
                                                                   new_sky_clarity,
                                                                   filename_format.format(img_num))
                  )
    img_num += 1
