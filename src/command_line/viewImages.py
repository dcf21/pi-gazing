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
import time

from pigazing_helpers import dcf_ast, connect_db
from pigazing_helpers.settings_read import settings, installation_info


def fetch_images(utc_min, utc_max, obstory, img_types, stride):
    """
    Fetch a list of all the images registered in the database.

    :param utc_min:
        Only return observations made after the specified time stamp.

    :type utc_min:
        float

    :param utc_max:
        Only return observations made before the specified time stamp.

    :type utc_max:
        float

    :param obstory:
        The public id of the observatory we are to fetch observations from

    :type obstory:
        str

    :param img_types:
        Only return images with these semantic types

    :type img_types:
        list[str]

    :param stride:
        Only return every nth observation matching the search criteria

    :type stride:
        int

    :return:
        None
    """
    # Open connection to database
    [db0, conn] = connect_db.connect_db()

    # Get list of observations
    conn.execute("""
SELECT o.uid, o.userId, l.name AS place, o.obsTime
FROM archive_observations o
INNER JOIN archive_observatories l ON o.observatory = l.uid
INNER JOIN archive_semanticTypes ast ON o.obsType = ast.uid
WHERE o.obsTime BETWEEN %s AND %s AND l.publicId=%s
ORDER BY obsTime ASC;
""", (utc_min, utc_max, obstory))
    results = conn.fetchall()

    # Show each observation in turn
    file_list = []
    for counter, obs in enumerate(results):
        # Only show every nth hit
        if counter % stride != 0:
            continue

        # Fetch list of files in this observation
        conn.execute("""
SELECT ast.name AS semanticType, repositoryFname, am.floatValue AS skyClarity
FROM archive_files f
INNER JOIN archive_semanticTypes ast ON f.semanticType = ast.uid
LEFT OUTER JOIN archive_metadata am ON f.uid = am.fileId AND
    am.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="pigazing:skyClarity")
WHERE f.observationId=%s;
""", (obs['uid'],))

        files = conn.fetchall()

        # Make dictionary of files by semantic type
        files_by_type = {'observation': obs}
        for file in files:
            files_by_type[file['semanticType']] = file

        # Check that we have all the requested types of file
        have_all_types = True
        for img_type in img_types:
            if img_type not in files_by_type:
                have_all_types = False

        if not have_all_types:
            continue

        file_list.append(files_by_type)

    return file_list


def view_images(utc_min, utc_max, obstory, img_types, stride):
    """
    View images registered in the database using the command line tool qiv.

    :param utc_min:
        Only return observations made after the specified time stamp.

    :type utc_min:
        float

    :param utc_max:
        Only return observations made before the specified time stamp.

    :type utc_max:
        float

    :param obstory:
        The public id of the observatory we are to fetch observations from

    :type obstory:
        str

    :param img_types:
        Only return images with these semantic types

    :type img_types:
        list[str]

    :param stride:
        Only return every nth observation matching the search criteria

    :type stride:
        int

    :return:
        None
    """

    # Temporary directory to hold the images we are going to show
    pid = os.getpid()
    tmp = os.path.join("/tmp", "dcf_view_images_{:d}".format(pid))
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

    for file_item in file_list:
        # Look up the date of this file
        [year, month, day, h, m, s] = dcf_ast.inv_julian_day(dcf_ast.jd_from_unix(
            utc=file_item['observation']['obsTime']
        ))

        # Filename for stitched image
        fn = "img___{:04d}_{:02d}_{:02d}___{:02d}_{:02d}_{:02d}.png".format(year, month, day, h, m, int(s))

        # Make list of input files
        input_files = [os.path.join(settings['dbFilestore'],
                                    file_item[semanticType]['repositoryFname'])
                       for semanticType in img_types]

        command = "\
convert {inputs} +append -gravity SouthWest -fill Red -pointsize 26 -font Ubuntu-Bold \
-annotate +16+10 '{date}  -  {label}' {output} \
".format(inputs=" ".join(input_files),
         date="{:02d}/{:02d}/{:04d} {:02d}:{:02d}".format(day, month, year, h, m),
         label="Sky clarity: {}".format(" / ".join(["{:04.0f}".format(file_item[semanticType]['skyClarity'])
                                                    for semanticType in img_types])),
         output=os.path.join(tmp, fn))
        # print(command)
        os.system(command)
        filename_list.append(fn)

    command_line = "cd {} ; qiv {}".format(tmp, " ".join(filename_list))
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
    parser.add_argument('--img-type', dest='img_type', action='append',
                        help="The type of image to list")
    parser.add_argument('--stride', dest='stride', default=1, type=int,
                        help="Only show every nth item, to reduce output")
    args = parser.parse_args()

    # Default list of image types to show
    if args.img_type is None or len(args.img_type) < 1:
        args.img_type = ["pigazing:timelapse/backgroundSubtracted"]

    view_images(utc_min=args.utc_min,
                utc_max=args.utc_max,
                obstory=args.obstory_id,
                img_types=args.img_type,
                stride=args.stride
                )
