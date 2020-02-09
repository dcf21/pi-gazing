#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# updateSkyClarity.py
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
Update the sky clarity measurements in the database. This is useful if the algorithm is changed.
"""

import argparse
import os
import subprocess
import time

from pigazing_helpers import connect_db
from pigazing_helpers.settings_read import settings


def update_sky_clarity(utc_min=None, utc_max=None, username=None, obstory=None):
    """
    Update the sky clarity measurements in the database. This is useful if the algorithm is changed.

    :param utc_min:
        Only update observations made after the specified time stamp.

    :type utc_min:
        float

    :param utc_max:
        Only update observations made before the specified time stamp.

    :type utc_max:
        float

    :param username:
        Optionally specify a username, to filter only images by a particular user

    :type username:
        str

    :param obstory:
        The public id of the observatory we are to update observations from

    :type obstory:
        str

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

    conn.execute("""
SELECT o.uid, o.userId, l.name AS place, o.obsTime
FROM archive_observations o
INNER JOIN archive_observatories l ON o.observatory = l.uid
INNER JOIN archive_semanticTypes ast ON o.obsType = ast.uid
WHERE """ + " AND ".join(where) + """
ORDER BY obsTime ASC;
""", args)
    results = conn.fetchall()

    # Update each observation in turn
    for counter, obs in enumerate(results):

        # Fetch list of files in this observation
        conn.execute("""
SELECT ast.name AS semanticType, repositoryFname, am.floatValue AS skyClarity, am.uid AS skyClarityUid
FROM archive_files f
INNER JOIN archive_semanticTypes ast ON f.semanticType = ast.uid
INNER JOIN archive_metadata am ON f.uid = am.fileId AND
    am.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="pigazing:skyClarity")
WHERE f.observationId=%s;
""", (obs['uid'],))

        files = conn.fetchall()

        for item in files:
            # Run sky clarity calculator
            p = subprocess.Popen(args=[os.path.join(settings['imageProcessorPath'], "skyClarity"),
                                       '--input',
                                       os.path.join(settings['dbFilestore'], item['repositoryFname'])],
                                 stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT)

            # Extract new sky clarity measurement
            new_sky_clarity = float(p.communicate(input=bytes("", 'utf-8'))[0].decode('utf-8'))

            # Print new measurement
            print("Updating {} from {:.0f} to {:.0f}".format(item['repositoryFname'],
                                                             item['skyClarity'],
                                                             new_sky_clarity))

            # Commit to database
            conn.execute("UPDATE archive_metadata SET floatValue=%s WHERE uid=%s",
                         (new_sky_clarity, item['skyClarityUid']))

    # Commit changes to database
    db0.commit()
    db0.close()


if __name__ == "__main__":
    # Read commandline arguments
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--username',
                        default=None,
                        dest='username',
                        help='Optionally specify a username, to filter only images by a particular user')
    parser.add_argument('--utc-min', dest='utc_min', default=0,
                        type=float,
                        help="Only update images recorded after the specified unix time")
    parser.add_argument('--utc-max', dest='utc_max', default=time.time(),
                        type=float,
                        help="Only update images recorded before the specified unix time")
    parser.add_argument('--observatory', dest='obstory_id', default=None,
                        help="ID of the observatory we are update images from")
    args = parser.parse_args()

    update_sky_clarity(utc_min=args.utc_min,
                       utc_max=args.utc_max,
                       obstory=args.obstory_id,
                       username=args.username
                       )
