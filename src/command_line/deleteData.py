#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# deleteData.py
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
Delete all observations and files recorded by a particular observatory between two times.
"""

import os
import argparse
import logging
import time

from pigazing_helpers import connect_db
from pigazing_helpers.settings_read import settings, installation_info


def delete_data(utc_min, utc_max, obstory, dry_run):
    # Open connection to database
    [db0, conn] = connect_db.connect_db()

    # Search for observations
    conn.execute("""
SELECT o.publicId
FROM archive_observations o
INNER JOIN archive_observatories ao on o.observatory = ao.uid
WHERE (o.obsTime BETWEEN %s AND %s) AND ao.publicId=%s;
""", (utc_min, utc_max, obstory))
    results_observations = conn.fetchall()

    # Delete each observation in turn
    for observation in results_observations:
        command = """
./deleteObservation.py --id {}
""".format(observation['publicId']).strip()

        logging.info(command)

        if not dry_run:
            os.system(command)


if __name__ == "__main__":
    # Read input parameters
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--t-min', dest='utc_min', default=0,
                        type=float,
                        help="Only delete observations made after the specified unix time")
    parser.add_argument('--t-max', dest='utc_max', default=(time.time() -
                                                            3600 * 24 * installation_info['dataLocalLifetime']),
                        type=float,
                        help="Only delete observations made before the specified unix time")
    parser.add_argument('--observatory', dest='observatory', default=installation_info['observatoryId'],
                        help="ID of the observatory we are to delete observations from")
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

    delete_data(utc_min=args.utc_min,
                utc_max=args.utc_max,
                obstory=args.observatory,
                dry_run=args.dry_run
                )
