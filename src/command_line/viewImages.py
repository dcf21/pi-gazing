#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# viewImages.py
#
# -------------------------------------------------
# Copyright 2015-2020 Dominic Ford
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
Use qiv (the quick image viewer; needs to be installed) to display the still (time-lapse) images recorded by an
observatory between specified start and end times. For example:

./viewImages.py --img-type "pigazing:timelapse/backgroundSubtracted"
./viewImages.py --img-type "pigazing:timelapse"
./viewImages.py --img-type "pigazing:timelapse/backgroundModel"

"""

import argparse
import os
import sys
import time

from pigazing_helpers import dcf_ast
from pigazing_helpers.obsarchive import obsarchive_db, obsarchive_model
from pigazing_helpers.settings_read import settings, installation_info


def view_images(utc_min, utc_max, obstory, img_type, stride):
    # Open connection to image archive
    db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                           db_host=installation_info['mysqlHost'],
                                           db_user=installation_info['mysqlUser'],
                                           db_password=installation_info['mysqlPassword'],
                                           db_name=installation_info['mysqlDatabase'],
                                           obstory_id=installation_info['observatoryId'])

    pid = os.getpid()
    tmp = os.path.join("/tmp", "dcf_view_images_{:d}".format(pid))
    os.system("mkdir -p {}".format(tmp))

    try:
        obstory_info = db.get_obstory_from_id(obstory_id=obstory)
    except ValueError:
        print("Unknown observatory <{}>. Run ./listObservatories.py to see a list of available observatories.".
              format(obstory))
        sys.exit(0)

    search = obsarchive_model.FileRecordSearch(obstory_ids=[obstory], semantic_type=img_type,
                                               time_min=utc_min, time_max=utc_max, limit=1000000)
    files = db.search_files(search)
    files = files['files']
    files.sort(key=lambda x: x.file_time)

    print("Observatory <{}>".format(obstory))
    print("  * {:d} matching files in time range {} --> {}".format(len(files),
                                                                   dcf_ast.date_string(utc_min),
                                                                   dcf_ast.date_string(utc_max)))

    command_line = "qiv "

    count = 1
    for file_item in files:
        count += 1
        if not (count % stride == 0):
            continue
        [year, month, day, h, m, s] = dcf_ast.inv_julian_day(dcf_ast.jd_from_unix(file_item.file_time))
        fn = "img___{:04d}_{:02d}_{:02d}___{:02d}_{:02d}_{:02d}___{:08d}.png".format(year, month, day,
                                                                                     h, m, int(s), count)
        os.system("ln -s %s %s/%s" % (db.file_path_for_id(file_item.id), tmp, fn))
        command_line += " {}".format(os.path.join(tmp, fn))

    # print "  * Running command: {}".format(command_line)

    os.system(command_line)
    os.system("rm -Rf {}".format(tmp))


if __name__ == "__main__":
    # Read input parameters
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--t-min', dest='utc_min', default=0,
                        type=float,
                        help="Only list events seen after the specified unix time")
    parser.add_argument('--t-max', dest='utc_max', default=time.time(),
                        type=float,
                        help="Only list events seen before the specified unix time")
    parser.add_argument('--observatory', dest='obstory_id', default=installation_info['observatoryId'],
                        help="ID of the observatory we are to list events from")
    parser.add_argument('--img-type', dest='img_type', default="pigazing:timelapse/backgroundSubtracted",
                        help="The type of image to list")
    parser.add_argument('--stride', dest='stride', default=1, type=int,
                        help="Only show every nth item, to reduce output")
    args = parser.parse_args()

    view_images(utc_min=args.utc_min,
                utc_max=args.utc_max,
                obstory=args.obstory_id,
                img_type=args.img_type,
                stride=args.stride
                )
