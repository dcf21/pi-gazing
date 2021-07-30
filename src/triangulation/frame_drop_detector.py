#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# frame_drop_detector.py
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
This script searches through all the moving objects detected within a given time span, and detects time points
where video frames appear to have been dropped, causing the video to skip forwards.
"""

import argparse
import logging
import os
import time
import json
from math import hypot
import numpy as np

from pigazing_helpers import connect_db
from pigazing_helpers.dcf_ast import date_string
from pigazing_helpers.obsarchive import obsarchive_model as mp, obsarchive_db
from pigazing_helpers.settings_read import settings, installation_info


def frame_drop_detection(utc_min, utc_max):
    """
    Detect video frame drop events between the unix times <utc_min> and <utc_max>.

    :param utc_min:
        The start of the time period in which we should search for video frame drop (unix time).
    :type utc_min:
        float
    :param utc_max:
        The end of the time period in which we should search for video frame drop (unix time).
    :type utc_max:
        float
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

    logging.info("Starting video frame drop detection.")

    # Count how many images we manage to successfully fit
    outcomes = {
        'frame_drop_events': 0,
        'non_frame_drop_events': 0,
        'error_records': 0,
        'rescued_records': 0
    }

    # Status update
    logging.info("Searching for frame drops within period {} to {}".format(date_string(utc_min), date_string(utc_max)))

    # Open direct connection to database
    conn = db.con

    # Search for meteors within this time period
    conn.execute("""
SELECT ao.obsTime, ao.publicId AS observationId, f.repositoryFname, l.publicId AS observatory, am6.stringValue AS type
FROM archive_observations ao
LEFT OUTER JOIN archive_files f ON (ao.uid = f.observationId AND
    f.semanticType=(SELECT uid FROM archive_semanticTypes WHERE name="pigazing:movingObject/video"))
INNER JOIN archive_observatories l ON ao.observatory = l.uid
LEFT OUTER JOIN archive_metadata am6 ON ao.uid = am6.observationId AND
    am6.fieldId = (SELECT uid FROM archive_metadataFields WHERE metaKey="web:category")
WHERE ao.obsType=(SELECT uid FROM archive_semanticTypes WHERE name='pigazing:movingObject/') AND
      ao.obsTime BETWEEN %s AND %s
ORDER BY ao.obsTime
""", (utc_min, utc_max))
    results = conn.fetchall()

    # Display logging list of the videos we are going to work on
    logging.info("Searching for dropped frames within {:d} videos.".format(len(results)))

    # Analyse each video in turn
    for item_index, item in enumerate(results):
        # Fetch metadata about this object, some of which might be on the file, and some on the observation
        obs_obj = db.get_observation(observation_id=item['observationId'])
        obs_metadata = {item.key: item.value for item in obs_obj.meta}
        if item['repositoryFname']:
            file_obj = db.get_file(repository_fname=item['repositoryFname'])
            file_metadata = {item.key: item.value for item in file_obj.meta}
        else:
            file_metadata = {}
        all_metadata = {**obs_metadata, **file_metadata}

        # Check we have all required metadata
        if ('pigazing:path' not in all_metadata) or ('pigazing:videoStart' not in all_metadata):
            logging.info("Cannot process <{}> due to inadequate metadata.".format(item['observationId']))
            continue

        # Make ID string to prefix to all logging messages about this event
        logging_prefix = "{date} [{obs}/{type:16s}]".format(
            date=date_string(utc=item['obsTime']),
            obs=item['observationId'],
            type=item['type'] if item['type'] is not None else ''
        )

        # Read path of the moving object in pixel coordinates
        path_json = all_metadata['pigazing:path']
        try:
            path_x_y = json.loads(path_json)
        except json.decoder.JSONDecodeError:
            # Attempt JSON repair; sometimes JSON content gets truncated
            original_json = path_json
            fixed_json = "],[".join(original_json.split("],[")[:-1]) + "]]"
            try:
                path_x_y = json.loads(fixed_json)

                # logging.info("{prefix} -- RESCUE: In: {detections:.0f} / {duration:.1f} sec; "
                #              "Rescued: {count:d} / {json_span:.1f} sec".format(
                #     prefix=logging_prefix,
                #     detections=all_metadata['pigazing:detections'],
                #     duration=all_metadata['pigazing:duration'],
                #     count=len(path_x_y),
                #     json_span=path_x_y[-1][3] - path_x_y[0][3]
                # ))
                outcomes['rescued_records'] += 1
            except json.decoder.JSONDecodeError:
                logging.info("{prefix} -- !!! JSON error".format(
                    prefix=logging_prefix
                ))
            outcomes['error_records'] += 1
            continue

        # Check number of points in path
        path_len = len(path_x_y)

        # Make list of object speed at each point
        path_speed = []  # pixels/sec
        path_distance = []
        for i in range(path_len - 1):
            pixel_distance = hypot(path_x_y[i + 1][0] - path_x_y[i][0], path_x_y[i + 1][1] - path_x_y[i][1])
            time_interval = (path_x_y[i + 1][3] - path_x_y[i][3]) + 1e-8
            speed = pixel_distance / time_interval
            path_speed.append(speed)
            path_distance.append(pixel_distance)

        # Start making a list of frame-drop events
        frame_drop_points = []

        # Scan through for points with anomalously high speed
        scan_half_window = 4
        for i in range(len(path_speed)):
            scan_min = max(0, i - scan_half_window)
            scan_max = min(scan_min + 2 * scan_half_window, len(path_speed) - 1)
            median_speed = max(np.median(path_speed[scan_min:scan_max]), 1)
            if (path_distance[i] > 16) and (path_speed[i] > 4 * median_speed):
                break_time = np.mean([path_x_y[i + 1][3], path_x_y[i][3]])
                video_time = break_time - all_metadata['pigazing:videoStart']
                break_distance = path_distance[i]
                # significance = path_speed[i]/median_speed
                frame_drop_points.append(
                    [i + 1, float("%.4f" % break_time), float("%.1f" % video_time), round(break_distance)]
                )

        # Report result
        if len(frame_drop_points) > 0:
            logging.info("{prefix} -- {x}".
                         format(prefix=logging_prefix,
                                x=frame_drop_points
                                ))

        # Store frame-drop list
        user = settings['pigazingUser']
        timestamp = time.time()
        db.set_observation_metadata(user_id=user, observation_id=item['observationId'], utc=timestamp,
                                    meta=mp.Meta(key="frame_drop:list", value=json.dumps(frame_drop_points)))

        # Video successfully analysed
        if len(frame_drop_points) == 0:
            outcomes['non_frame_drop_events'] += 1
        else:
            outcomes['frame_drop_events'] += 1

        # Update database
        db.commit()

    # Report how many fits we achieved
    logging.info("{:d} videos with frame-drop.".format(outcomes['frame_drop_events']))
    logging.info("{:d} videos without frame-drop.".format(outcomes['non_frame_drop_events']))
    logging.info("{:d} malformed database records.".format(outcomes['error_records']))
    logging.info("{:d} rescued database records.".format(outcomes['rescued_records']))

    # Clean up and exit
    db.commit()
    db.close_db()
    return


def flush_detections(utc_min, utc_max):
    """
    Remove all frame-drop detections within a specified time period.

    :param utc_min:
        The earliest time for which we are to flush frame-drop detections.
    :param utc_max:
        The latest time for which we are to flush frame-drop detections.
    :return:
        None
    """
    # Open connection to database
    [db0, conn] = connect_db.connect_db()

    # Delete observation metadata fields that start 'frame_drop:*'
    conn.execute("""
DELETE m
FROM archive_metadata m
INNER JOIN archive_observations o ON m.observationId = o.uid
WHERE
    fieldId IN (SELECT uid FROM archive_metadataFields WHERE metaKey LIKE 'frame_drop:%%') AND
    o.obsTime BETWEEN %s AND %s;
""", (utc_min, utc_max))

    # Commit changes to database
    db0.commit()
    conn.close()
    db0.close()


# If we're called as a script, run the function frame_drop_detection()
if __name__ == "__main__":
    # Read command-line arguments
    parser = argparse.ArgumentParser(description=__doc__)

    # By default, search all videos recorded since the beginning of time
    parser.add_argument('--utc-min', dest='utc_min', default=0,
                        type=float,
                        help="Only analyse moving objects recorded after the specified unix time")
    parser.add_argument('--utc-max', dest='utc_max', default=time.time(),
                        type=float,
                        help="Only analyse moving objects recorded before the specified unix time")

    parser.add_argument('--flush', dest='flush', action='store_true')
    parser.add_argument('--no-flush', dest='flush', action='store_false')
    parser.set_defaults(flush=True)
    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(level=logging.INFO,
                        format='[%(asctime)s] %(levelname)s:%(filename)32s:%(message)s',
                        datefmt='%d/%m/%Y %H:%M:%S',
                        handlers=[
                            logging.FileHandler(os.path.join(settings['pythonPath'], "../datadir/pigazing.log")),
                            logging.StreamHandler()
                        ])
    logger = logging.getLogger(__name__)
    # logger.info(__doc__.strip())

    # If flush option was specified, then delete all existing frame-drop detections
    if args.flush:
        flush_detections(utc_min=args.utc_min,
                         utc_max=args.utc_max)

    # Search for frame-drop detections
    frame_drop_detection(utc_min=args.utc_min,
                         utc_max=args.utc_max)
