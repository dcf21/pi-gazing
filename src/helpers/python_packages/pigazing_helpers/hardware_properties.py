# -*- coding: utf-8 -*-
# hardware_properties.py
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

import os
import json

from .vendor import xmltodict
from .settings_read import settings


class Camera:
    """
    Class representing a particular model of camera which can be used with pigazing. This hold all of the metadata
    associated with this particularly camera model.
    """

    def __init__(self, name, width, height, fps, upside_down, camera_type):
        self.name = name
        self.width = width
        self.height = height
        self.fps = fps
        self.upside_down = upside_down
        self.camera_type = camera_type

    def __str__(self):
        print("Camera({},{},{},{},{},{})".format(self.name, self.width, self.height,
                                                 self.fps, self.upside_down, self.camera_type))


class Lens:
    """
    Class representing a particular model of lens which can be used with pigazing. This hold all of the metadata
    associated with this particularly lens.
    """

    def __init__(self, name, fov, barrel_parameters):
        self.name = name
        self.fov = fov
        self.barrel_parameters = barrel_parameters

    def __str__(self):
        print("Lens({},{},{})".format(self.name, self.fov, self.barrel_parameters))


class HardwareProps:
    """
    Class used for holding a database of all of the cameras and lens that we have metadata for.
    """

    def __init__(self, path):
        cameras_data_path = os.path.join(path, "cameras.xml")
        lenses_data_path = os.path.join(path, "lenses.xml")
        assert os.path.exists(cameras_data_path), "Could not find camera data in file <{}>".format(cameras_data_path)
        assert os.path.exists(lenses_data_path), "Could not find lens data in file <{}>".format(lenses_data_path)

        camera_xml = xmltodict.parse(open(cameras_data_path, "rb"))['cameras']['camera']

        self.camera_data = {}
        for d in camera_xml:
            self.camera_data[d['name']] = Camera(name=d['name'], width=int(d['width']), height=int(d['height']),
                                                 fps=float(d['fps']), upside_down=int(d['upside_down']),
                                                 camera_type=d['type'])

        lens_xml = xmltodict.parse(open(lenses_data_path, "rb"))['lenses']['lens']

        self.lens_data = {}
        for d in lens_xml:
            self.lens_data[d['name']] = Lens(name=d['name'],
                                             fov=float(d['fov']),
                                             barrel_parameters=json.loads(d['radial_distortion'])
                                             )

    def update_camera(self, db, obstory_id, utc, name):
        """
        Update the model of camera in use at a particular observatory.

        :param db:
            A obsarchive_db object
        :param obstory_id:
            The string ID of the observatory to update
        :param utc:
            The unix time from which this change of camera is to be applied
        :param name:
            The name of the new camera being used
        :return:
            None
        """
        assert name in self.camera_data, "Unknown camera type <{}>".format(name)
        x = self.camera_data[name]
        user = settings['pigazingUser']
        db.register_obstory_metadata(obstory_id=obstory_id,
                                     key="camera", value=name,
                                     metadata_time=utc, user_created=user)

        db.register_obstory_metadata(obstory_id=obstory_id,
                                     key="camera_width", value=x.width,
                                     metadata_time=utc, user_created=user)

        db.register_obstory_metadata(obstory_id=obstory_id,
                                     key="camera_height", value=x.height,
                                     metadata_time=utc, user_created=user)

        db.register_obstory_metadata(obstory_id=obstory_id,
                                     key="camera_fps", value=x.fps,
                                     metadata_time=utc, user_created=user)

        db.register_obstory_metadata(obstory_id=obstory_id,
                                     key="camera_upside_down", value=x.upside_down,
                                     metadata_time=utc, user_created=user)

        db.register_obstory_metadata(obstory_id=obstory_id,
                                     key="camera_type", value=x.camera_type,
                                     metadata_time=utc, user_created=user)

    def update_lens(self, db, obstory_id, utc, name):
        """
        Update the model of lens in use at a particular observatory.

        :param db:
            A obsarchive_db object
        :param obstory_id:
            The string ID of the observatory to update
        :param utc:
            The unix time from which this change of camera is to be applied
        :param name:
            The name of the new lens being used
        :return:
            None
        """

        assert name in self.lens_data, "Unknown lens type <{}>".format(name)
        x = self.lens_data[name]
        user = settings['pigazingUser']
        db.register_obstory_metadata(obstory_id=obstory_id,
                                     key="lens", value=name,
                                     metadata_time=utc, user_created=user)
        db.register_obstory_metadata(obstory_id=obstory_id,
                                     key="lens_fov", value=x.fov, metadata_time=utc, user_created=user)
