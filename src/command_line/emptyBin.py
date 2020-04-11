#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# emptyBin.py
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
Delete all observation which the webeditor user has classified as being 'bin'
"""

import argparse
import logging
import os

from pigazing_helpers import connect_db
from pigazing_helpers.settings_read import settings


def empty_bin(dry_run):
    """
    Delete all observation which the webeditor user has classified as being 'bin'.

    :param dry_run:
        Boolean indicating whether we should do a dry run, without actually deleting anything

    :return:
        None
    """
    # Open connection to database
    [db0, conn] = connect_db.connect_db()

    # Search for observations
    conn.execute("""
SELECT o.publicId
FROM archive_observations o
INNER JOIN archive_metadata am on o.uid = am.observationId
    AND am.fieldId=(SELECT x.uid FROM archive_metadataFields x WHERE x.metaKey="web:category")
WHERE am.stringValue = 'Bin';
""")
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
    # Read commandline arguments
    parser = argparse.ArgumentParser(description=__doc__)
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

    empty_bin(dry_run=args.dry_run)

