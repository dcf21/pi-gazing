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
from pigazing_helpers.obsarchive import obsarchive_db
from pigazing_helpers.dcf_ast import date_string
from pigazing_helpers.gnomonic_project import inv_gnom_project, position_angle
from pigazing_helpers.settings_read import settings
from pigazing_helpers.sunset_times import get_zenith_position, ra_dec


class PathProjection:
    """
    A class for projecting the paths of moving objects, in (x, y) pixel coordinates, into celestial coordinates.
    """
    def __init__(self, db: obsarchive_db, obstory_id: str, observation_id: str, time: float):
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
        :param observation_id:
            The publicId of the observation we are analysing
        :type observation_id:
            str
        :param time:
            The unix time of the observation
        :type time:
            float
        """

        # Record inputs
        self.db = db
        self.obstory_id = obstory_id
        self.observation_id = observation_id
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
            logging.info("{date} [{obs}] -- No observatory status available".format(
                date=date_string(utc=self.time),
                obs=self.observation_id
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
        lens_name = self.obstory_status['lens']
        lens_props = self.hw.lens_data[lens_name]
        # Look up radial distortion model for the lens we are using
        lens_barrel_parameters = self.obstory_status.get('calibration:lens_barrel_parameters',
                                                         lens_props.barrel_parameters)
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

        # Look up orientation of the camera
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
        else:
            # We cannot identify meteors if we don't know which direction camera is pointing
            logging.info("{date} [{obs}] -- Orientation of camera unknown".format(
                date=date_string(utc=self.time),
                obs=self.observation_id
            ))
            self.error = 'insufficient_information'
            return None

        # Look up size of camera sensor
        if 'camera_width' in self.obstory_status:
            orientation['pixel_width'] = self.obstory_status['camera_width']
            orientation['pixel_height'] = self.obstory_status['camera_height']
        else:
            # We cannot identify meteors if we don't know camera field of view
            logging.info("{date} [{obs}] -- Pixel dimensions of video stream could not be determined".format(
                date=date_string(utc=self.time),
                obs=self.observation_id
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

                logging.info("{date} [{obs}] -- RESCUE: In: {detections:.0f} / {duration:.1f} sec; "
                             "Rescued: {count:d} / {json_span:.1f} sec".format(
                    date=date_string(utc=self.time),
                    obs=self.observation_id,
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

                logging.info("{date} [{obs}] -- Added Bezier points: "
                             "In: {detections:.0f} / {duration:.1f} sec; "
                             "Rescued: {count:d} / {json_span:.1f} sec".format(
                    date=date_string(utc=self.time),
                    obs=self.observation_id,
                    detections=detections,
                    duration=duration,
                    count=len(path_x_y),
                    json_span=path_x_y[-1][3] - path_x_y[0][3]
                ))
            except json.decoder.JSONDecodeError:
                logging.info("{date} [{obs}] -- !!! JSON error".format(
                    date=date_string(utc=self.time),
                    obs=self.observation_id
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
            return None, None

        # Extract (x,y) path from input JSON
        path_x_y = self.extract_path_from_json(path_json, path_bezier_json, detections, duration)
        if self.error:
            return None, None

        # Convert path of moving objects into RA / Dec (radians, at epoch of observation)
        path_ra_dec_at_epoch = []
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
            path_ra_dec_at_epoch.append(
                inv_gnom_project(ra0=instantaneous_central_ra_at_epoch * pi / 12,
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
            )
        return path_x_y, path_ra_dec_at_epoch
