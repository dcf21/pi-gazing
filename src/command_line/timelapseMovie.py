#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# timelapseMovie.py
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
Make a time lapse video of still images recorded between specified start and end times
"""

import argparse
import os
import time

from pigazing_helpers import dcf_ast
from pigazing_helpers.settings_read import settings, installation_info
from viewImages import fetch_images


def timelapse_movie(utc_min, utc_max, obstory, img_types, stride, label):
    # Temporary directory to hold the images we are going to show
    pid = os.getpid()
    tmp = os.path.join("/tmp", "dcf_movie_images_{:d}".format(pid))
    os.system("mkdir -p {}".format(tmp))

    file_list = fetch_images(utc_min=utc_min,
                             utc_max=utc_max,
                             obstory=obstory,
                             img_types=img_types,
                             stride=stride)

    # Report how many files we found
    print("Observatory <{}>".format(obstory))
    print("  * {:d} matching files in time range {} --> {}".format(len(file_list),
                                                                   dcf_ast.date_string(utc_min),
                                                                   dcf_ast.date_string(utc_max)))

    # Make list of the stitched files
    filename_list = []
    filename_format = "frame_{:d}_%08d.jpg".format(pid)

    for counter, file_item in enumerate(file_list):
        # Look up the date of this file
        [year, month, day, h, m, s] = dcf_ast.inv_julian_day(dcf_ast.jd_from_unix(
            utc=file_item['observation']['obsTime']
        ))

        # Filename for stitched image
        fn = filename_format % counter

        # Make list of input files
        input_files = [os.path.join(settings['dbFilestore'],
                                    file_item[semanticType]['repositoryFname'])
                       for semanticType in img_types]

        command = "\
convert {inputs} +append -gravity SouthWest -fill Red -pointsize 26 -font Ubuntu-Bold \
-annotate +16+10 '{date}  -  {label1}  -  {label2}' {output} \
".format(inputs=" ".join(input_files),
         date="{:02d}/{:02d}/{:04d} {:02d}:{:02d}".format(day, month, year, h, m),
         label1="Sky clarity: {}".format(" / ".join(["{:04.0f}".format(file_item[semanticType]['skyClarity'])
                                                    for semanticType in img_types])),
         label2=label,
         output=os.path.join(tmp, fn))
        # print(command)
        os.system(command)
        filename_list.append(fn)

    command_line = "cd {} ; ffmpeg -r 10 -i {} -codec:v libx264 {}".format(tmp , filename_format, "timelapse.mp4")
    print(command_line)
    os.system(command_line)


if __name__ == "__main__":
    # Read input parameters
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--t-min', dest='utc_min', default=time.time() - 3600 * 24,
                        type=float,
                        help="Only list events seen after the specified unix time")
    parser.add_argument('--t-max', dest='utc_max', default=time.time(),
                        type=float,
                        help="Only list events seen before the specified unix time")
    parser.add_argument('--observatory', dest='obstory_id', default=installation_info['observatoryId'],
                        help="ID of the observatory we are to list events from")
    parser.add_argument('--label', dest='label', default="",
                        help="Label to put at the bottom of each frame of the video")
    parser.add_argument('--img-type', dest='img_type', action='append',
                        help="The type of image to list")
    parser.add_argument('--stride', dest='stride', default=1, type=int,
                        help="Only show every nth item, to reduce output")
    args = parser.parse_args()

    # Default list of image types to show
    if args.img_type is None or len(args.img_type) < 1:
        args.img_type = ["pigazing:timelapse/backgroundSubtracted"]

    timelapse_movie(utc_min=args.utc_min,
                    utc_max=args.utc_max,
                    obstory=args.obstory_id,
                    img_types=args.img_type,
                    stride=args.stride,
                    label=args.label
                    )
