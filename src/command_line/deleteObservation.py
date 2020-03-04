#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# deleteObservation.py
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
Delete an observation and all associated files.
"""

import argparse
import logging
import os

from pigazing_helpers import connect_db
from pigazing_helpers.settings_read import settings


def delete_observation(id, dry_run):
    """
    Delete an observation and all associated files.

    :param id:
        The publicId of the observation to delete

    :param dry_run:
        Boolean indicating whether we should do a dry run, without actually deleting anything

    :return:
        None
    """
    # Open connection to database
    [db0, conn] = connect_db.connect_db()

    # Search for observation
    conn.execute("""
SELECT o.uid
FROM archive_observations o
WHERE o.publicId=%s;
""", (id,))
    results_observations = conn.fetchall()

    # Delete each observation in turn
    for observation in results_observations:
        # Search for files
        conn.execute("""
    SELECT f.uid, f.repositoryFname
    FROM archive_files f
    WHERE f.observationId=%s
    """, (observation['uid'],))
        results_files = conn.fetchall()

        # Delete each file in turn
        for file in results_files:

            logging.info("Deleting file <{}>".format(file['repositoryFname']))

            # Delete files
            if not dry_run:
                os.unlink(os.path.join(settings['dbFilestore'], file['repositoryFname']))

            # Delete file record
            if not dry_run:
                conn.execute("DELETE FROM archive_files WHERE uid=%s", (file['uid'],))

        # Delete observation
        if not dry_run:
            conn.execute("DELETE FROM archive_observations WHERE uid=%s", (observation['uid'],))

    # Commit changes to database
    db0.commit()
    conn.close()
    db0.close()


if __name__ == "__main__":
    # Read commandline arguments
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--id',
                        required=True,
                        dest='id',
                        help='The ID of the observation to delete')
    parser.add_argument('--dry-run', dest='dry_run', action='store_true')
    parser.add_argument('--no-dry-run', dest='dry_run', action='store_false')
    parser.set_defaults(dry_run=False)
    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(level=logging.INFO,
                        format='[%(asctime)s] %(levelname)s:%(filename)s:%(message)s',
                        datefmt='%d/%m/%Y %H:%M:%S',
                        handlers=[
                            logging.FileHandler(os.path.join(settings['pythonPath'], "../datadir/pigazing.log")),
                            logging.StreamHandler()
                        ])
    logger = logging.getLogger(__name__)
    logger.info(__doc__.strip())

    delete_observation(id=args.id,
                       dry_run=args.dry_run
                       )
