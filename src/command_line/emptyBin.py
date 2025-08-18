#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# emptyBin.py
#
# -------------------------------------------------
# Copyright 2015-2021 Dominic Ford
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
Delete all observation which the web editor user has classified as being 'bin'
"""

import argparse
import logging
import os

from pigazing_helpers.obsarchive import obsarchive_db, obsarchive_model
from pigazing_helpers.settings_read import settings, installation_info


def empty_bin(dry_run):
    """
    Delete all observation which the web editor user has classified as being 'bin'.

    :param dry_run:
        Boolean indicating whether we should do a dry run, without actually deleting anything

    :return:
        None
    """
    # Open connection to image archive
    db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                           db_host=installation_info['mysqlHost'],
                                           db_user=installation_info['mysqlUser'],
                                           db_password=installation_info['mysqlPassword'],
                                           db_name=installation_info['mysqlDatabase'],
                                           obstory_id=installation_info['observatoryId'])

    # Open direct connection to database
    conn = db.con

    # Search for observations
    conn.execute("""
SELECT f.repositoryFname, f.fileSize, s.name AS semantic, o.publicId AS obs_id
FROM archive_files f
INNER JOIN archive_observations o ON f.observationId = o.uid
INNER JOIN archive_semanticTypes s ON f.semanticType = s.uid
INNER JOIN archive_metadata am on o.uid = am.observationId
    AND am.fieldId=(SELECT x.uid FROM archive_metadataFields x WHERE x.metaKey="web:category")
INNER JOIN archive_metadata am2 on o.uid = am2.observationId
    AND am2.fieldId=(SELECT x.uid FROM archive_metadataFields x WHERE x.metaKey="pigazing:amplitudePeak")
INNER JOIN archive_metadata am3 on o.uid = am3.observationId
    AND am3.fieldId=(SELECT x.uid FROM archive_metadataFields x WHERE x.metaKey="pigazing:duration")
WHERE o.obsType=(SELECT uid FROM archive_semanticTypes WHERE name='pigazing:movingObject/') AND
      (s.name='pigazing:movingObject/video' OR
       s.name='pigazing:movingObject/previousFrame' OR
       s.name='pigazing:movingObject/mapDifference' OR
       s.name='pigazing:movingObject/mapExcludedPixels' OR
       s.name='pigazing:movingObject/mapTrigger'
      ) AND (
      am.stringValue='Bin' OR (am.stringValue='Plane' AND am2.floatValue < 9000 AND am3.floatValue > 5)
      );
""")
    results_observations = conn.fetchall()

    # Keep track of how many bytes we cleaned up
    total_file_size = 0

    # Delete each observation in turn
    for observation in results_observations:
        # Check that observation is not featured
        conn.execute("""
SELECT COUNT(*)
FROM archive_files f
INNER JOIN archive_observations o ON f.observationId = o.uid
INNER JOIN archive_metadata d ON f.uid = d.fileId AND d.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey='web:featured')
WHERE o.publicId=%s;
""", (observation['obs_id'],))
        featured_file_count = conn.fetchall()[0]['COUNT(*)']

        if featured_file_count > 0:
            logging.info("Not pruning observation <{}> because it is featured.".format(observation['obs_id']))
            continue

        # Keep track of total file size we are deleting
        total_file_size += observation['fileSize']

        # Transfer file metadata to observation
        if observation['semantic'] == 'pigazing:movingObject/video':
            # Open observation object
            obs_obj = db.get_observation(observation_id=observation['obs_id'])
            obs_metadata = {item.key: item.value for item in obs_obj.meta}

            # Open file object
            file_obj = db.get_file(repository_fname=observation['repositoryFname'])
            file_metadata = {item.key: item.value for item in file_obj.meta}

            # Transfer file metadata to observation
            for key in file_metadata:
                if key not in obs_metadata:
                    db.set_observation_metadata(user_id='migrated',
                                                observation_id=observation['obs_id'],
                                                meta=obsarchive_model.Meta(
                                                    key=key,
                                                    value=file_metadata[key]
                                                )
                                                )

        # Delete file
        if not dry_run:
            os.unlink(os.path.join(settings['dbFilestore'], observation['repositoryFname']))

        # Delete file record
        if not dry_run:
            conn.execute("DELETE FROM archive_files WHERE repositoryFname=%s", (observation['repositoryFname'],))

    # Report how much disk space we saved
    logging.info("Total storage saved: {:.3f} GB".format(total_file_size / 1e9))

    # Commit changes to database
    db.commit()
    db.close_db()


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
