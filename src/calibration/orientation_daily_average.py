#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# orientation_daily_average.py
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
Calculate a sigma-clipped mean of the calculated values for the azimuth
and alitude of the camera within each night, and if there are sufficient
values, and they are sufficiently closely aligned, we update the observatory's
status to reflect the new orientation fix.
"""

import argparse
import json
import logging
import operator
import os
import time
from math import pi, floor

import numpy as np
from pigazing_helpers import connect_db, hardware_properties
from pigazing_helpers.dcf_ast import date_string
from pigazing_helpers.gnomonic_project import ang_dist
from pigazing_helpers.obsarchive import obsarchive_model as mp, obsarchive_db
from pigazing_helpers.path_projection import PathProjection
from pigazing_helpers.settings_read import settings, installation_info
from pigazing_helpers.sunset_times import mean_angle, mean_angle_2d

from orientation_calculate import minimum_sky_clarity, reduce_time_window, estimate_fit_quality, deg, rad


def orientation_calc(obstory_id, utc_min, utc_max):
    """
    Use astrometry.net to determine the orientation of a particular observatory within each night within the time
    period between the unix times <utc_min> and <utc_max>.

    :param obstory_id:
        The ID of the observatory we want to determine the orientation for.
    :type obstory_id:
        str
    :param utc_min:
        The start of the time period in which we should determine the observatory's orientation (unix time).
    :type utc_min:
        float
    :param utc_max:
        The end of the time period in which we should determine the observatory's orientation (unix time).
    :type utc_max:
        float
    :param utc_must_stop:
        The unix time after which we must abort and finish work as quickly as possible.
    :type utc_must_stop:
        float
    :return:
        None
    """

    # Open connection to database
    [db0, conn] = connect_db.connect_db()

    # Open connection to image archive
    db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                           db_host=installation_info['mysqlHost'],
                                           db_user=installation_info['mysqlUser'],
                                           db_password=installation_info['mysqlPassword'],
                                           db_name=installation_info['mysqlDatabase'],
                                           obstory_id=installation_info['observatoryId'])

    logging.info("Starting calculation of camera alignment for <{}>".format(obstory_id))

    # Reduce time window we are searching to the interval in which observations are present (to save time)
    utc_max, utc_min = reduce_time_window(conn=conn, obstory_id=obstory_id, utc_max=utc_max, utc_min=utc_min)

    # Try to average the fits within each night to determine the sigma-clipped mean orientation
    average_daily_fits(conn=conn, db=db, obstory_id=obstory_id, utc_max=utc_max, utc_min=utc_min)
    measure_fit_quality_to_daily_fits(conn=conn, db=db, obstory_id=obstory_id, utc_max=utc_max, utc_min=utc_min)

    # Clean up and exit
    db.commit()
    db.close_db()
    db0.commit()
    conn.close()
    db0.close()
    return


def average_daily_fits(conn, db, obstory_id, utc_max, utc_min):
    """
    Average all of the orientation fixes within a given time period, excluding extreme fits. Update the observatory's
    status with a altitude and azimuth of the average fit, if it has a suitably small error bar.

    :param conn:
        Database connection object.
    :param db:
        Database object.
    :param obstory_id:
        Observatory publicId.
    :param utc_max:
        Unix time of the end of the time period.
    :param utc_min:
        Unix time of the beginning of the time period.
    :return:
        None
    """

    # Divide up the time period in which we are working into individual nights, and then work on each night individually
    logging.info("Averaging daily fits within period {} to {}".format(date_string(utc_min), date_string(utc_max)))

    # Each night is a 86400-second period
    daily_block_size = 86400

    # Make sure that blocks start at noon
    utc_min = (floor(utc_min / daily_block_size + 0.5) - 0.5) * daily_block_size
    time_blocks = list(np.arange(start=utc_min, stop=utc_max + daily_block_size, step=daily_block_size))

    # Start new block whenever we have a hardware refresh, even if it's in the middle of the night!
    conn.execute("""
SELECT time FROM archive_metadata
WHERE observatory=(SELECT uid FROM archive_observatories WHERE publicId=%s)
      AND fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey='refresh')
      AND time BETWEEN %s AND %s
""", (obstory_id, utc_min, utc_max))
    results = conn.fetchall()
    for item in results:
        time_blocks.append(item['time'])

    # Make sure that start points for time blocks are in order
    time_blocks.sort()

    # Work on each time block (i.e. night) in turn
    for block_index, utc_block_min in enumerate(time_blocks[:-1]):
        # End point for this time block
        utc_block_max = time_blocks[block_index + 1]

        # Search for observations with orientation fits
        conn.execute("""
SELECT am1.floatValue AS altitude, am2.floatValue AS azimuth, am3.floatValue AS pa, am4.floatValue AS tilt,
       am5.floatValue AS width_x_field, am6.floatValue AS width_y_field,
       am7.stringValue AS fit_quality
FROM archive_observations o
INNER JOIN archive_metadata am1 ON o.uid = am1.observationId AND
    am1.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="orientation:altitude")
INNER JOIN archive_metadata am2 ON o.uid = am2.observationId AND
    am2.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="orientation:azimuth")
INNER JOIN archive_metadata am3 ON o.uid = am3.observationId AND
    am3.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="orientation:pa")
INNER JOIN archive_metadata am4 ON o.uid = am4.observationId AND
    am4.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="orientation:tilt")
INNER JOIN archive_metadata am5 ON o.uid = am5.observationId AND
    am5.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="orientation:width_x_field")
INNER JOIN archive_metadata am6 ON o.uid = am6.observationId AND
    am6.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="orientation:width_y_field")
INNER JOIN archive_metadata am7 ON o.uid = am7.observationId AND
    am7.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="orientation:fit_quality")
WHERE
    o.observatory = (SELECT uid FROM archive_observatories WHERE publicId=%s) AND
    o.obsTime BETWEEN %s AND %s;
""", (obstory_id, utc_block_min, utc_block_max))
        results = conn.fetchall()

        # Remove results with poor fit
        results_filtered = []
        fit_threshold = 2  # pixels
        for item in results:
            fit_quality = float(json.loads(item['fit_quality'])[0])
            if fit_quality > fit_threshold:
                continue
            item['weight'] = 1/(fit_quality + 0.1)
            results_filtered.append(item)
        results = results_filtered

        # Report how many images we found
        logging.info("Averaging fits within period {} to {}: Found {} fits.".format(date_string(utc_block_min),
                                                                                    date_string(utc_block_max),
                                                                                    len(results)))

        # Average the fits we found
        if len(results) < 4:
            logging.info("Insufficient images to reliably average.")
            continue

        # What fraction of the worst fits do we reject?
        rejection_fraction = 0.25

        # Reject the 25% of fits which are further from the average
        rejection_count = int(len(results) * rejection_fraction)

        # Convert alt-az fits into radians and average
        # Iteratively remove the point furthest from the mean
        results_filtered = results

        # Iteratively take the average of the fits, reject the furthest outlier, and then take a new average
        for iteration in range(rejection_count):
            # Average the (alt, az) measurements for this observatory by finding their centroid on a sphere
            alt_az_list = [[i['altitude'] * deg, i['azimuth'] * deg] for i in results_filtered]
            weights_list = [i['weight'] for i in results_filtered]
            alt_az_best = mean_angle_2d(pos_list=alt_az_list, weights=weights_list)[0]

            # Work out the offset of each fit from the average
            fit_offsets = [ang_dist(ra0=alt_az_best[1], dec0=alt_az_best[0],
                                    ra1=fitted_alt_az[1], dec1=fitted_alt_az[0])
                           for fitted_alt_az in alt_az_list]

            # Reject the worst fit which is further from the average
            fits_with_weights = list(zip(fit_offsets, results_filtered))
            fits_with_weights.sort(key=operator.itemgetter(0))
            fits_with_weights.reverse()

            # Create a new list of orientation fits, with the worst outlier excluded
            results_filtered = [item[1] for item in fits_with_weights[1:]]

        # Convert alt-az fits into radians and average by finding their centroid on a sphere
        alt_az_list = [[i['altitude'] * deg, i['azimuth'] * deg] for i in results_filtered]
        weights_list = [i['weight'] for i in results_filtered]
        [alt_az_best, alt_az_error] = mean_angle_2d(pos_list=alt_az_list, weights=weights_list)

        # Average other angles by finding their centroid on a circle
        output_values = {}
        for quantity in ['tilt', 'pa', 'width_x_field', 'width_y_field']:
            # Iteratively remove the point furthest from the mean
            results_filtered = results

            # Iteratively take the average of the values for each parameter, reject the furthest outlier,
            # and then take a new average
            for iteration in range(rejection_count):
                # Average quantity measurements
                quantity_values = [i[quantity] * deg for i in results_filtered]
                weights_list = [i['weight'] for i in results_filtered]
                quantity_mean = mean_angle(angle_list=quantity_values, weights=weights_list)[0]

                # Work out the offset of each fit from the average
                fit_offsets = []
                for index, quantity_value in enumerate(quantity_values):
                    offset = quantity_value - quantity_mean
                    if offset < -pi:
                        offset += 2 * pi
                    if offset > pi:
                        offset -= 2 * pi
                    fit_offsets.append(abs(offset))

                # Reject the worst fit which is furthest from the average
                fits_with_weights = list(zip(fit_offsets, results_filtered))
                fits_with_weights.sort(key=operator.itemgetter(0))
                fits_with_weights.reverse()
                results_filtered = [item[1] for item in fits_with_weights[1:]]

            # Filtering finished; now convert each fit into radians and average
            values_filtered = [i[quantity] * deg for i in results_filtered]
            weights_list = [i['weight'] for i in results_filtered]
            value_best = mean_angle(angle_list=values_filtered, weights=weights_list)[0]
            output_values[quantity] = value_best * rad

        # Print fit information
        success = (alt_az_error * rad < 0.1)  # Only accept determinations with better precision than 0.1 deg
        adjective = "SUCCESSFUL" if success else "REJECTED"
        logging.info("""\
{} ORIENTATION FIT from {:2d} images: Alt: {:.2f} deg. Az: {:.2f} deg. PA: {:.2f} deg. \
ScaleX: {:.2f} deg. ScaleY: {:.2f} deg. Uncertainty: {:.2f} deg.\
""".format(adjective, len(results_filtered),
           alt_az_best[0] * rad,
           alt_az_best[1] * rad,
           output_values['tilt'],
           output_values['width_x_field'],
           output_values['width_y_field'],
           alt_az_error * rad))

        # Update observatory status
        if success:
            # Flush any previous observation status
            flush_orientation(obstory_id=obstory_id, utc_min=utc_block_min - 1, utc_max=utc_block_min + 1)

            user = settings['pigazingUser']
            timestamp = time.time()
            db.register_obstory_metadata(obstory_id=obstory_id, key="orientation:altitude",
                                         value=alt_az_best[0] * rad, time_created=timestamp,
                                         metadata_time=utc_block_min, user_created=user)
            db.register_obstory_metadata(obstory_id=obstory_id, key="orientation:azimuth",
                                         value=alt_az_best[1] * rad, time_created=timestamp,
                                         metadata_time=utc_block_min, user_created=user)
            db.register_obstory_metadata(obstory_id=obstory_id, key="orientation:pa",
                                         value=output_values['pa'], time_created=timestamp,
                                         metadata_time=utc_block_min, user_created=user)
            db.register_obstory_metadata(obstory_id=obstory_id, key="orientation:tilt",
                                         value=output_values['tilt'], time_created=timestamp,
                                         metadata_time=utc_block_min, user_created=user)
            db.register_obstory_metadata(obstory_id=obstory_id, key="orientation:width_x_field",
                                         value=output_values['width_x_field'], time_created=timestamp,
                                         metadata_time=utc_block_min, user_created=user)
            db.register_obstory_metadata(obstory_id=obstory_id, key="orientation:width_y_field",
                                         value=output_values['width_y_field'], time_created=timestamp,
                                         metadata_time=utc_block_min, user_created=user)
            db.register_obstory_metadata(obstory_id=obstory_id, key="orientation:uncertainty",
                                         value=alt_az_error * rad, time_created=timestamp,
                                         metadata_time=utc_block_min, user_created=user)
            db.register_obstory_metadata(obstory_id=obstory_id, key="orientation:image_count",
                                         value=len(results), time_created=timestamp,
                                         metadata_time=utc_block_min, user_created=user)
            db.commit()


def measure_fit_quality_to_daily_fits(conn, db, obstory_id, utc_min, utc_max):
    """
    Measure quality of fit of images to daily-averaged orientation within a specified time period.

    :param conn:
        Database connection object.
    :param db:
        Database object.
    :param obstory_id:
        The ID of the observatory we want to determine the orientation for.
    :type obstory_id:
        str
    :param utc_min:
        The start of the time period in which we should determine the observatory's orientation (unix time).
    :type utc_min:
        float
    :param utc_max:
        The end of the time period in which we should determine the observatory's orientation (unix time).
    :type utc_max:
        float
    :return:
        None
    """

    # Read properties of known lenses, which give us the default radial distortion models to assume for them
    hw = hardware_properties.HardwareProps(
        path=os.path.join(settings['pythonPath'], "..", "configuration_global", "camera_properties")
    )

    # Fetch observatory's database record
    obstory_info = db.get_obstory_from_id(obstory_id)

    logging.info("Measuring fit quality to daily average orientations <{}>".format(obstory_id))

    # Search for background-subtracted time lapse image with good sky clarity within this time period
    conn.execute("""
SELECT ao.obsTime, ao.publicId AS observationId, f.repositoryFname
FROM archive_files f
INNER JOIN archive_observations ao on f.observationId = ao.uid
INNER JOIN archive_metadata am ON f.uid = am.fileId AND
    am.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="pigazing:skyClarity")
WHERE ao.obsTime BETWEEN %s AND %s
    AND ao.observatory=(SELECT uid FROM archive_observatories WHERE publicId=%s)
    AND f.semanticType=(SELECT uid FROM archive_semanticTypes WHERE name="pigazing:timelapse/backgroundSubtracted")
    AND am.floatValue > %s;
""", (utc_min, utc_max, obstory_id, minimum_sky_clarity))
    results = conn.fetchall()

    # Loop over each image in turn
    for item in results:
        # Fetch coordinates of image
        projector = PathProjection(
            db=db,
            obstory_id=obstory_id,
            time=item['obsTime'],
            logging_prefix=item['observationId'],
            must_use_daily_average=True
        )

        # Reject images with incomplete data
        if projector.error is not None:
            continue

        # Build image descriptor
        descriptor = {
            'utc': item['obsTime'],
            'repositoryFname': item['repositoryFname'],
            'observationId': item['observationId'],
            'obstory_info': obstory_info,
            'obstory_status': projector.obstory_status,
            'lens_props': projector.lens_props
        }

        # Find image's full path
        filename = os.path.join(settings['dbFilestore'], item['repositoryFname'])

        # Estimate quality of fit
        fit_quality = estimate_fit_quality(
            image_file=filename,
            item=descriptor,
            fit_parameters={
                'ra': projector.central_ra_at_epoch,  # hours
                'dec': projector.central_dec_at_epoch,  # degrees
                'pa': projector.celestial_pa_at_epoch,  # degrees
                'scale_x': projector.orientation['ang_width'],  # degrees
                'scale_y': projector.orientation['ang_height']  # degrees
            }
        )
        logging.info("{} -- QUALITY {}".format(item['observationId'], fit_quality))

        # Write fit quality metadata
        user = settings['pigazingUser']
        timestamp = time.time()
        db.set_observation_metadata(user_id=user, observation_id=item['observationId'], utc=timestamp,
                                    meta=mp.Meta(key="orientation:fit_quality_to_daily",
                                                 value=json.dumps(fit_quality)))
        db.commit()


def flush_orientation(obstory_id, utc_min, utc_max):
    """
    Remove all orientation data for a particular observatory within a specified time period.

    :param obstory_id:
        The publicId of the observatory we are to flush.
    :param utc_min:
        The earliest time for which we are to flush orientation data.
    :param utc_max:
        The latest time for which we are to flush orientation data.
    :return:
        None
    """
    # Open connection to database
    [db0, conn] = connect_db.connect_db()

    # Delete observatory metadata fields that start 'orientation:*'
    conn.execute("""
DELETE m
FROM archive_metadata m
WHERE
    fieldId IN (SELECT uid FROM archive_metadataFields WHERE metaKey LIKE 'orientation:%%') AND
    m.observatory = (SELECT uid FROM archive_observatories WHERE publicId=%s) AND
    m.time BETWEEN %s AND %s;
""", (obstory_id, utc_min, utc_max))

    # Delete observation metadata field 'orientation:fit_quality_to_daily'
    conn.execute("""
DELETE m
FROM archive_metadata m
INNER JOIN archive_observations o ON m.observationId = o.uid
WHERE
    fieldId IN (SELECT uid FROM archive_metadataFields WHERE metaKey LIKE 'orientation:fit_quality_to_daily') AND
    o.observatory = (SELECT uid FROM archive_observatories WHERE publicId=%s) AND
    o.obsTime BETWEEN %s AND %s;
""", (obstory_id, utc_min, utc_max))

    # Commit changes to database
    db0.commit()
    conn.close()
    db0.close()


# If we're called as a script, run the function orientation_calc()
if __name__ == "__main__":
    # Read command-line arguments
    parser = argparse.ArgumentParser(description=__doc__)

    # By default, study images taken over past 24 hours
    parser.add_argument('--utc-min', dest='utc_min', default=time.time() - 3600 * 24,
                        type=float,
                        help="Only use images recorded after the specified unix time")
    parser.add_argument('--utc-max', dest='utc_max', default=time.time(),
                        type=float,
                        help="Only use images recorded before the specified unix time")

    parser.add_argument('--observatory', dest='obstory_id', default=installation_info['observatoryId'],
                        help="ID of the observatory we are to calibrate")
    parser.add_argument('--flush', dest='flush', action='store_true')
    parser.add_argument('--no-flush', dest='flush', action='store_false')
    parser.set_defaults(flush=False)
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
    # logger.info(__doc__.strip())

    # If flush option was specified, then delete all existing alignment information
    if args.flush:
        flush_orientation(obstory_id=args.obstory_id,
                          utc_min=args.utc_min,
                          utc_max=args.utc_max)

    # Calculate the orientation of images
    orientation_calc(obstory_id=args.obstory_id,
                     utc_min=args.utc_min,
                     utc_max=args.utc_max)
