#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# listImages.py
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
Display a list of all the images registered in the database.
"""

import argparse
import sys
import time

from pigazing_helpers import connect_db
from pigazing_helpers.dcf_ast import date_string


def list_images(utc_min=None, utc_max=None, username=None, obstory=None, img_type=None, obs_type=None, stride=1):
    """
    Display a list of all the images registered in the database.

    :param utc_min:
        Only show observations made after the specified time stamp.

    :type utc_min:
        float

    :param utc_max:
        Only show observations made before the specified time stamp.

    :type utc_max:
        float

    :param username:
        Optionally specify a username, to filter only images by a particular user

    :type username:
        str

    :param obstory:
        The public id of the observatory we are to show observations from

    :type obstory:
        str

    :param img_type:
        Only show images with this semantic type

    :type img_type:
        str

    :param obs_type:
        Only show observations with this semantic type

    :type obs_type:
        str

    :param stride:
        Only show every nth observation matching the search criteria

    :type stride:
        int

    :return:
        None
    """
    # Open connection to database
    [db0, conn] = connect_db.connect_db()

    where = ["1"]
    args = []

    if utc_min is not None:
        where.append("o.obsTime>=%s")
        args.append(utc_min)
    if utc_max is not None:
        where.append("o.obsTime<=%s")
        args.append(utc_max)
    if username is not None:
        where.append("o.userId=%s")
        args.append(username)
    if obstory is not None:
        where.append("l.publicId=%s")
        args.append(obstory)
    if obs_type is not None:
        where.append("ast.name=%s")
        args.append(obs_type)

    conn.execute("""
SELECT o.uid, o.userId, l.name AS place, o.obsTime
FROM archive_observations o
INNER JOIN archive_observatories l ON o.observatory = l.uid
INNER JOIN archive_semanticTypes ast ON o.obsType = ast.uid
WHERE """ + " AND ".join(where) + """
ORDER BY obsTime DESC LIMIT 200;
""", args)
    results = conn.fetchall()

    # List information about each observation in turn
    sys.stdout.write("{:6s} {:10s} {:32s} {:17s} {:20s}\n".format("obsId", "Username", "Observatory", "Time", "Images"))
    for counter, obs in enumerate(results):
        # Only show every nth hit
        if counter % stride != 0:
            continue

        # Print observation information
        sys.stdout.write("{:6d} {:10s} {:32s} {:17s} ".format(obs['uid'], obs['userId'], obs['place'],
                                                              date_string(obs['obsTime'])))

        where = ["f.observationId=%s"]
        args = [obs['uid']]

        if img_type is not None:
            where.append("ast.name=%s")
            args.append(img_type)

        # Fetch list of files in this observation
        conn.execute("""
SELECT ast.name AS semanticType, repositoryFname, am.floatValue AS skyClarity
FROM archive_files f
INNER JOIN archive_semanticTypes ast ON f.semanticType = ast.uid
LEFT OUTER JOIN archive_metadata am ON f.uid = am.fileId AND
    am.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="pigazing:skyClarity")
WHERE """ + " AND ".join(where) + """;
""", args)

        files = conn.fetchall()

        for count, item in enumerate(files):
            if count > 0:
                sys.stdout.write("\n{:69s}".format(""))
            if item['skyClarity'] is None:
                item['skyClarity'] = 0
            sys.stdout.write("{:40s} {:32s} {:10.1f}".format(item['semanticType'],
                                                             item['repositoryFname'],
                                                             item['skyClarity']))
        sys.stdout.write("\n")


if __name__ == "__main__":
    # Read commandline arguments
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--username',
                        default=None,
                        dest='username',
                        help='Optionally specify a username, to filter only images by a particular user')
    parser.add_argument('--utc-min', dest='utc_min', default=0,
                        type=float,
                        help="Only list events seen after the specified unix time")
    parser.add_argument('--utc-max', dest='utc_max', default=time.time(),
                        type=float,
                        help="Only list events seen before the specified unix time")
    parser.add_argument('--observatory', dest='obstory_id', default=None,
                        help="ID of the observatory we are to list events from")
    parser.add_argument('--img-type', dest='img_type', default=None,
                        help="The type of image to list")
    parser.add_argument('--obs-type', dest='obs_type', default=None,
                        help="The type of observation to list")
    parser.add_argument('--stride', dest='stride', default=1, type=int,
                        help="Only show every nth item, to reduce output")
    args = parser.parse_args()

    list_images(utc_min=args.utc_min,
                utc_max=args.utc_max,
                obstory=args.obstory_id,
                username=args.username,
                obs_type=args.obs_type,
                img_type=args.img_type,
                stride=args.stride
                )
