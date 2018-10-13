# -*- coding: utf-8 -*-
# hardware_properties.py
#
# -------------------------------------------------
# Copyright 2015-2018 Dominic Ford
#
# This file is part of Meteor Pi.
#
# Meteor Pi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Meteor Pi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Meteor Pi.  If not, see <http://www.gnu.org/licenses/>.
# -------------------------------------------------

import os
import xml.etree.cElementTree as ElementTree

from . import mod_xml
from . import settings_read


class Sensor:
    def __init__(self, name, width, height, fps, upside_down, camera_type):
        self.name = name
        self.width = width
        self.height = height
        self.fps = fps
        self.upside_down = upside_down
        self.camera_type = camera_type

    def __str__(self):
        print("sensor(%s,%s,%s,%s,%s,%s)" % (
            self.name, self.width, self.height, self.fps, self.upside_down, self.camera_type))


class Lens:
    def __init__(self, name, fov, barrel_a, barrel_b, barrel_c):
        self.name = name
        self.fov = fov
        self.barrel_a = barrel_a
        self.barrel_b = barrel_b
        self.barrel_c = barrel_c

    def __str__(self):
        print("lens(%s,%s,%s,%s,%s)" % (self.name, self.fov, self.barrel_a, self.barrel_b, self.barrel_c))


class HardwareProps:
    def __init__(self, path):
        sensors_data_path = os.path.join(path, "sensors.xml")
        lenses_data_path = os.path.join(path, "lenses.xml")
        assert os.path.exists(sensors_data_path), "Could not find sensor data in file <%s>" % sensors_data_path
        assert os.path.exists(lenses_data_path), "Could not find lens data in file <%s>" % lenses_data_path

        tree = ElementTree.parse(sensors_data_path)
        root = tree.getroot()
        sensor_xml = mod_xml.XmlListConfig(root)

        self.sensor_data = {}
        for d in sensor_xml:
            self.sensor_data[d['name']] = Sensor(d['name'], int(d['width']), int(d['height']), float(d['fps']),
                                                 int(d['upsidedown']), d['type'])

        tree = ElementTree.parse(lenses_data_path)
        root = tree.getroot()
        lens_xml = mod_xml.XmlListConfig(root)

        self.lens_data = {}
        for d in lens_xml:
            self.lens_data[d['name']] = Lens(d['name'], float(d['fov']), float(d['barrel_a']), float(d['barrel_b']),
                                             float(d['barrel_c']))

    def update_sensor(self, db, obstory_name, utc, name):
        assert name in self.sensor_data, "Unknown sensor type <%s>" % name
        x = self.sensor_data[name]
        user = settings_read.settings['meteorpiUser']
        db.register_obstory_metadata(obstory_name, "sensor", name, utc, user)
        db.register_obstory_metadata(obstory_name, "sensor_width", x.width, utc, user)
        db.register_obstory_metadata(obstory_name, "sensor_height", x.height, utc, user)
        db.register_obstory_metadata(obstory_name, "sensor_fps", x.fps, utc, user)
        db.register_obstory_metadata(obstory_name, "sensor_upside_down", x.upside_down, utc, user)
        db.register_obstory_metadata(obstory_name, "sensor_camera_type", x.camera_type, utc, user)

    def update_lens(self, db, obstory_name, utc, name):
        assert name in self.lens_data, "Unknown lens type <%s>" % name
        x = self.lens_data[name]
        user = settings_read.settings['meteorpiUser']
        db.register_obstory_metadata(obstory_name, "lens", name, utc, user)
        db.register_obstory_metadata(obstory_name, "lens_fov", x.fov, utc, user)
        db.register_obstory_metadata(obstory_name, "lens_barrel_a", x.barrel_a, utc, user)
        db.register_obstory_metadata(obstory_name, "lens_barrel_b", x.barrel_b, utc, user)
        db.register_obstory_metadata(obstory_name, "lens_barrel_c", x.barrel_c, utc, user)
