# -*- coding: utf-8 -*-
# path_projection.py
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
A class for projecting paths between pixel coordinates, celestial coordinates, and Cartesian coordinates.
"""

import json
import logging
import os
from math import pi

from pigazing_helpers import hardware_properties
from pigazing_helpers.gnomonic_project import inv_gnom_project, position_angle
from pigazing_helpers.obsarchive import obsarchive_db
from pigazing_helpers.settings_read import settings
from pigazing_helpers.sunset_times import get_zenith_position, sidereal_time, ra_dec, alt_az
from pigazing_helpers.vector_algebra import Point, Vector, Line


class PathProjection:
    """
    A class for projecting the paths of moving objects, in (x, y) pixel coordinates, into celestial coordinates.
    """

    def __init__(self, db: obsarchive_db, obstory_id: str, time: float, logging_prefix: str,
                 must_use_daily_average: bool=False):
        """
        A class for projecting the paths of moving objects, in (x, y) pixel coordinates, into celestial coordinates.

        :param db:
            A handle for a connection to the Pi Gazing database
        :type db:
            obsarchive_db.ObservationDatabase
        :param obstory_id:
            The publicId of the observatory which made the observation.
        :type obstory_id:
            str
        :param time:
            The unix time of the observation
        :type time:
            float
        :param logging_prefix:
            Text to prefix to all logging messages about this event, to identify it.
        :type logging_prefix:
            str
        :param must_use_daily_average:
            If true, we always use the most recent daily average orientation, and do not override with a higher
            quality fit to a single image with similar timestamp, if such an image is available.
        :type must_use_daily_average:
            bool
        """

        # Record inputs
        self.db = db
        self.obstory_id = obstory_id
        self.logging_prefix = logging_prefix
        self.must_use_daily_average = must_use_daily_average
        self.time = time
        self.error = None  # Set to a string in case of failure
        self.notifications = []  # List of notification strings

        # Read properties of known lenses, which give us the default radial distortion models to assume for them
        self.hw = hardware_properties.HardwareProps(
            path=os.path.join(settings['pythonPath'], "..", "configuration_global", "camera_properties")
        )

        # Fetch observatory status at the time of this observation
        self.obstory_info, self.obstory_status = self.fetch_observatory_record()

        # Fetch lens barrel parameters
        self.lens_barrel_parameters = self.fetch_lens_model()

        # Fetch camera orientation
        self.orientation = self.fetch_camera_orientation()

        # Abort in case of error
        if self.error:
            return

        # Position of observatory in Cartesian coordinates, relative to centre of the Earth
        # Units: metres; zero longitude along x axis
        self.observatory_position = Point.from_lat_lng(lat=self.obstory_info['latitude'],
                                                       lng=self.obstory_info['longitude'],
                                                       alt=0,  # Unfortunately <archive_observatories> doesn't store alt
                                                       utc=None)

        # Get celestial coordinates of the local zenith
        ra_dec_zenith_at_epoch = get_zenith_position(latitude=self.obstory_info['latitude'],
                                                     longitude=self.obstory_info['longitude'],
                                                     utc=self.time)
        ra_zenith_at_epoch = ra_dec_zenith_at_epoch['ra']  # hours, epoch of observation
        dec_zenith_at_epoch = ra_dec_zenith_at_epoch['dec']  # degrees, epoch of observation

        # Calculate celestial coordinates of the centre of the field of view
        # hours / degrees, epoch of observation
        central_ra_at_epoch, central_dec_at_epoch = ra_dec(alt=self.orientation['altitude'],
                                                           az=self.orientation['azimuth'],
                                                           utc=self.time,
                                                           latitude=self.obstory_info['latitude'],
                                                           longitude=self.obstory_info['longitude']
                                                           )
        self.central_ra_at_epoch = central_ra_at_epoch
        self.central_dec_at_epoch = central_dec_at_epoch

        # Work out the position angle of the zenith, counterclockwise from north, as measured at centre of frame
        # degrees for north pole at epoch
        zenith_pa_at_epoch = position_angle(ra1=central_ra_at_epoch, dec1=central_dec_at_epoch,
                                            ra2=ra_zenith_at_epoch, dec2=dec_zenith_at_epoch)

        # Calculate the position angle of the north pole, clockwise from vertical, at the centre of the frame
        self.celestial_pa_at_epoch = zenith_pa_at_epoch - self.orientation['tilt']
        while self.celestial_pa_at_epoch < -180:
            self.celestial_pa_at_epoch += 360
        while self.celestial_pa_at_epoch > 180:
            self.celestial_pa_at_epoch -= 360

    def fetch_observatory_record(self):
        """
        Fetch the metadata set for the observatory at the time it made this observation.

        :return:
        List of [Observatory database record, observatory metadata dictionary]
        """
        # Do not proceed if we have already encountered an error
        if self.error:
            return None, None

        # Fetch observatory's database record
        obstory_info = self.db.get_obstory_from_id(obstory_id=self.obstory_id)

        # Fetch observatory status at time of observation
        obstory_status = self.db.get_obstory_status(obstory_id=self.obstory_id, time=self.time)

        if not obstory_status:
            # We cannot identify meteors if we don't have observatory status
            logging.info("{prefix} -- No observatory status available".format(
                prefix=self.logging_prefix
            ))
            self.error = 'insufficient_information'
            return None, None

        return obstory_info, obstory_status

    def fetch_lens_model(self):
        """
        Fetch a description of the lens fitted in this observatory, either from the default properties of the named
        lens installed, or from the properties stored in the observatory's metadata.

        :return:
            Lens descriptor.
            List of [Horizontal fov / deg, Vertical fov / deg, A, B, C]
        """
        # Do not proceed if we have already encountered an error
        if self.error:
            return None

        # Fetch properties of the lens being used at the time of the observation
        self.lens_name = self.obstory_status['lens']
        self.lens_props = self.hw.lens_data[self.lens_name]
        # Look up radial distortion model for the lens we are using
        lens_barrel_parameters = self.obstory_status.get('calibration:lens_barrel_parameters',
                                                         self.lens_props.barrel_parameters)
        if isinstance(lens_barrel_parameters, str):
            lens_barrel_parameters = json.loads(lens_barrel_parameters)
        return lens_barrel_parameters

    def fetch_camera_orientation(self):
        """
        Fetch a dictionary of parameters describing the pointing of the observatory at the moment it took this
        observation.

        :return:
            Dictionary of pointing parameters.
        """
        # Do not proceed if we have already encountered an error
        if self.error:
            return None

        orientation = None

        # Look up daily average orientation of the camera
        if 'orientation:altitude' in self.obstory_status:
            orientation = {
                'altitude': self.obstory_status['orientation:altitude'],
                'azimuth': self.obstory_status['orientation:azimuth'],
                'pa': self.obstory_status['orientation:pa'],
                'tilt': self.obstory_status['orientation:tilt'],
                'ang_width': self.obstory_status['orientation:width_x_field'],
                'ang_height': self.obstory_status['orientation:width_y_field'],
                'orientation_uncertainty': self.obstory_status['orientation:uncertainty'],
                'pixel_width': None,
                'pixel_height': None
            }

        # See if we have a better recent orientation fix
        if not self.must_use_daily_average:
            search_window = 3600
            self.db.con.execute("""
SELECT am1.floatValue AS altitude, am2.floatValue AS azimuth, am3.floatValue AS pa, am4.floatValue AS tilt,
       am5.floatValue AS width_x_field, am6.floatValue AS width_y_field,
       am7.stringValue AS fit_quality, am8.stringValue AS fit_quality_to_daily
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
LEFT OUTER JOIN archive_metadata am8 ON o.uid = am8.observationId AND
    am8.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey="orientation:fit_quality_to_daily")
WHERE
    o.observatory = (SELECT uid FROM archive_observatories WHERE publicId=%s) AND
    o.obsTime BETWEEN %s AND %s
ORDER BY ABS(o.obsTime-%s) LIMIT 1;
""", (self.obstory_id, self.time - search_window, self.time + search_window, self.time))
            results = self.db.con.fetchall()

            if len(results) > 0:
                threshold_fit_quality = 2.5
                fit_quality = fit_quality_to_daily = 999
                item = results[0]
                if item['fit_quality'] is not None:
                    fit_quality = float(json.loads(item['fit_quality'])[0])
                if item['fit_quality_to_daily'] is not None:
                    fit_quality_to_daily = float(json.loads(item['fit_quality_to_daily'])[0])
                if (fit_quality < threshold_fit_quality) and (fit_quality < fit_quality_to_daily):
                    orientation = {
                        'altitude': item['altitude'],
                        'azimuth': item['azimuth'],
                        'pa': item['pa'],
                        'tilt': item['tilt'],
                        'ang_width': item['width_x_field'],
                        'ang_height': item['width_y_field'],
                        'orientation_uncertainty': None,
                        'pixel_width': None,
                        'pixel_height': None
                    }

        # Return an error if we didn't find an orientation
        if orientation is None:
            # We cannot identify meteors if we don't know which direction camera is pointing
            logging.info("{prefix} -- Orientation of camera unknown".format(
                prefix=self.logging_prefix
            ))
            self.error = 'insufficient_information'
            return None

        # Look up size of camera sensor
        if 'camera_width' in self.obstory_status:
            orientation['pixel_width'] = self.obstory_status['camera_width']
            orientation['pixel_height'] = self.obstory_status['camera_height']
        else:
            # We cannot identify meteors if we don't know camera field of view
            logging.info("{prefix} -- Pixel dimensions of video stream could not be determined".format(
                prefix=self.logging_prefix
            ))
            self.error = 'insufficient_information'
            return None

        # Return output
        return orientation

    def extract_path_from_json(self, path_json: str, path_bezier_json: str, detections: float, duration: float):
        """
        Extract a list of [x, y, intensity, utc] points from the JSON metadata associated with this moving object.
        Unfortunately some of these JSON strings are truncated, in which case, we attempt recovery from the
        "bezierPath" metadata field.

        :param path_json:
            Contents of the metadata field "pigazing:path". JSON string with list of [x, y, intensity, utc] points.
        :type path_json:
            str
        :param path_bezier_json:
            Contents of the metadata field "pigazing:pathBezier". JSON string with list of three [x, y, utc] points.
        :type path_bezier_json:
            str
        :param detections:
            Count of the number of detections of this moving object
        :type detections:
            int
        :param duration:
            The duration of time over which this moving object was observed.
        :type duration:
            float
        :return:
            List of [x, y, intensity, utc] points
        """
        # Do not proceed if we have already encountered an error
        if self.error:
            return None

        # Read path of the moving object in pixel coordinates
        try:
            path_x_y = json.loads(path_json)
        except json.decoder.JSONDecodeError:
            # Attempt JSON repair; sometimes JSON content gets truncated
            original_json = path_json
            fixed_json = "],[".join(original_json.split("],[")[:-1]) + "]]"
            try:
                path_x_y = json.loads(fixed_json)

                logging.info("{prefix} -- RESCUE: In: {detections:.0f} / {duration:.1f} sec; "
                             "Rescued: {count:d} / {json_span:.1f} sec".format(
                    prefix=self.logging_prefix,
                    detections=detections,
                    duration=duration,
                    count=len(path_x_y),
                    json_span=path_x_y[-1][3] - path_x_y[0][3]
                ))

                path_bezier = json.loads(path_bezier_json)
                p = path_bezier[1]
                path_x_y.append([p[0], p[1], 0, p[2]])
                p = path_bezier[2]
                path_x_y.append([p[0], p[1], 0, p[2]])
                self.notifications.append('rescued_record')

                logging.info("{prefix} -- Added Bezier points: "
                             "In: {detections:.0f} / {duration:.1f} sec; "
                             "Rescued: {count:d} / {json_span:.1f} sec".format(
                    prefix=self.logging_prefix,
                    detections=detections,
                    duration=duration,
                    count=len(path_x_y),
                    json_span=path_x_y[-1][3] - path_x_y[0][3]
                ))
            except json.decoder.JSONDecodeError:
                logging.info("{prefix} -- !!! JSON error".format(
                    prefix=self.logging_prefix
                ))
                self.error = 'error_record'
                return None

        return path_x_y

    def ra_dec_from_x_y(self, path_json, path_bezier_json, detections, duration):
        """
        Convert a list of the [x, y] positions of the sightings of a moving object to a list of [RA, Dec] positions.

        :param path_json:
            Contents of the metadata field "pigazing:path". JSON string with list of [x, y, intensity, utc] points.
        :type path_json:
            str
        :param path_bezier_json:
            Contents of the metadata field "pigazing:pathBezier". JSON string with list of three [x, y, utc] points.
        :type path_bezier_json:
            str
        :param detections:
            Count of the number of detections of this moving object
        :type detections:
            int
        :param duration:
            The duration of time over which this moving object was observed.
        :type duration:
            float
        :return:
            List of [RA, Dec] points
        """
        # Do not proceed if we have already encountered an error
        if self.error:
            return None, None, None, None

        # Extract (x,y) path from input JSON
        path_x_y = self.extract_path_from_json(path_json, path_bezier_json, detections, duration)
        if self.error:
            return None, None, None, None

        # Convert path of moving objects into RA / Dec (radians, at epoch of observation)
        path_ra_dec_at_epoch = []
        path_alt_az = []
        sight_line_list = []
        for pt_x, pt_y, pt_intensity, pt_utc in path_x_y:
            # Calculate celestial coordinates of the centre of the field of view
            # hours / degrees, epoch of observation
            instantaneous_central_ra_at_epoch, instantaneous_central_dec_at_epoch = ra_dec(
                alt=self.orientation['altitude'],
                az=self.orientation['azimuth'],
                utc=pt_utc,
                latitude=self.obstory_info['latitude'],
                longitude=self.obstory_info['longitude']
            )

            # Calculate RA / Dec of observed position, at observed time
            ra, dec = inv_gnom_project(ra0=instantaneous_central_ra_at_epoch * pi / 12,
                                       dec0=instantaneous_central_dec_at_epoch * pi / 180,
                                       size_x=self.orientation['pixel_width'],
                                       size_y=self.orientation['pixel_height'],
                                       scale_x=self.orientation['ang_width'] * pi / 180,
                                       scale_y=self.orientation['ang_height'] * pi / 180,
                                       x=pt_x, y=pt_y,
                                       pos_ang=self.celestial_pa_at_epoch * pi / 180,
                                       barrel_k1=self.lens_barrel_parameters[2],
                                       barrel_k2=self.lens_barrel_parameters[3],
                                       barrel_k3=self.lens_barrel_parameters[4]
                                       )

            path_ra_dec_at_epoch.append([ra, dec])

            # Work out the Greenwich hour angle of the object; radians eastwards of the prime meridian at Greenwich
            instantaneous_sidereal_time = sidereal_time(utc=pt_utc)  # hours
            greenwich_hour_angle = ra - instantaneous_sidereal_time * pi / 12  # radians

            # Work out alt-az of reported (RA,Dec) using known location of camera (degrees)
            alt, az = alt_az(ra=ra * 12 / pi, dec=dec * 180 / pi,
                             utc=pt_utc,
                             latitude=self.obstory_info['latitude'],
                             longitude=self.obstory_info['longitude'])

            path_alt_az.append([alt, az])

            # Populate description of this sight line from observatory to the moving object
            direction = Vector.from_ra_dec(ra=greenwich_hour_angle * 12 / pi, dec=dec * 180 / pi)
            sight_line = Line(self.observatory_position, direction)
            sight_line_descriptor = {
                'ra': ra,  # radians; at epoch
                'dec': dec,  # radians; at epoch
                'alt': alt,  # degrees
                'az': az,  # degrees
                'utc': pt_utc,  # unix time
                'obs_position': self.observatory_position,  # Point
                'line': sight_line  # Line
            }
            sight_line_list.append(sight_line_descriptor)

            # Debugging
            # logging.info("Observatory <{}> saw object at RA {:.3f} h; Dec {:.3f} deg, with sight line {}.".
            #              format(obstory_info['publicId'],
            #                     ra * 12 / pi,
            #                     dec * 180 / pi,
            #                     sight_line))

        return path_x_y, path_ra_dec_at_epoch, path_alt_az, sight_line_list
