#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# addImage.py
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
Insert an image file into the database.
"""

import argparse
import glob
import json
import os
import re
import subprocess
import time
from os import path as os_path

from pigazing_helpers import connect_db
from pigazing_helpers.dcf_ast import julian_day, unix_from_jd
from pigazing_helpers.obsarchive import obsarchive_db, obsarchive_model
from pigazing_helpers.settings_read import settings, installation_info


def fetch_exif_metadata(input_path, time_offset):
    """
    Attempt to extract metadata from a JPEG file's EXIF headers.

    :param input_path:
        The filename of the JPEG file we are to inspect
    :type input_path:
        str
    :param time_offset:
        Time offset to apply to image, seconds (positive means we move time forwards).
    :type time_offset:
        int
    :return:
        A dictionary of metadata
    """
    metadata = {}

    # See if date is specified in filename
    input_filename = os_path.split(input_path)[1]
    test = re.match(r"(?:IMG_)?(\d\d\d\d)(\d\d)(\d\d)_?(\d\d)(\d\d)(\d\d).jpg", input_filename)
    if test:
        metadata['Time'] = unix_from_jd(julian_day(year=int(test.group(1)),
                                                   month=int(test.group(2)),
                                                   day=int(test.group(3)),
                                                   hour=int(test.group(4)),
                                                   minute=int(test.group(5)),
                                                   sec=int(test.group(6))))

    # See if information is specified in EXIF data
    d = subprocess.check_output(["identify", "-verbose", input_path]).decode('utf-8').split('\n')
    for line in d:

        # Test for date
        test = re.search("exif:DateTimeOriginal: (\d\d\d\d):(\d\d):(\d\d) (\d\d):(\d\d):(\d\d)", line)
        if test and ('Time' not in metadata):
            metadata['Time'] = unix_from_jd(julian_day(year=int(test.group(1)),
                                                       month=int(test.group(2)),
                                                       day=int(test.group(3)),
                                                       hour=int(test.group(4)),
                                                       minute=int(test.group(5)),
                                                       sec=int(test.group(6))))

        # Test for camera model
        test = re.search("exif:Model: (.*)", line)
        if test:
            metadata['Camera model'] = test.group(1).strip()

        # Test for ISO setting
        test = re.search("exif:ISOSpeedRatings: (.*)", line)
        if test:
            metadata['ISO setting'] = "ISO " + test.group(1).strip()

        # Test for exposure setting
        test = re.search("exif:ExposureTime: (.*)", line)
        if test:
            test = test.group(1).strip()
            if test.endswith("/1"):
                test = test[:-2]
            metadata['Exposure'] = test + " sec"

        # Test for focal length
        test = re.search("exif:FocalLength: (.*)", line)
        if test:
            test = test.group(1).strip()
            if test.endswith("/1"):
                test = test[:-2]
            elif test.endswith("/1000"):
                test = "%.1f" % (float(test[:-5]) / 1000)
            metadata['Focal length'] = test + " mm"

        # Test for latitude
        test = re.search("exif:GPSLatitude: (\d+)/(\d+), (\d+)/(\d+), (\d+)/(\d+)", line)
        if test:
            metadata['GPS Latitude'] = float(test.group(1)) / float(test.group(2)) + \
                                       float(test.group(3)) / float(test.group(4)) / 60 + \
                                       float(test.group(5)) / float(test.group(6)) / 3600

        # Test for latitude direction
        test = re.search("exif:GPSLatitudeRef: (.*)", line)
        if test and test.group(1).strip() == 'S':
            metadata['GPS Latitude'] *= -1

        # Test for longitude
        test = re.search("exif:GPSLongitude: (\d+)/(\d+), (\d+)/(\d+), (\d+)/(\d+)", line)
        if test:
            metadata['GPS Longitude'] = float(test.group(1)) / float(test.group(2)) + \
                                        float(test.group(3)) / float(test.group(4)) / 60 + \
                                        float(test.group(5)) / float(test.group(6)) / 3600

        # Test for longitude direction
        test = re.search("exif:GPSLongitudeRef: (.*)", line)
        if test and test.group(1).strip() == 'W':
            metadata['GPS Longitude'] *= -1

    # Make sure time is specified
    if 'Time' not in metadata:
        metadata['Time'] = time.time()

    # If we were given a time offset, apply that now
    metadata['Time'] += time_offset

    # Return the metadata we have extracted
    return metadata


def new_image(image, username, observatory, title, semantic_type='Original', time_offset=0):
    """
    Insert an image file into the database.

    :param image:
        The filename of the image to be inserted
    :param username:
        The username of the user who is to own this image
    :param observatory:
        The observatory from which this observation was made
    :param title:
        The title of this image
    :param semantic_type:
        The semantic type of this image file, e.g. "Original"
    :param time_offset:
        Time offset to apply to image, seconds (positive means we move time forwards).
    :type time_offset:
        int
    :return:
        None
    """
    our_path = os_path.split(os_path.abspath(__file__))[0]

    db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                           db_host=installation_info['mysqlHost'],
                                           db_user=installation_info['mysqlUser'],
                                           db_password=installation_info['mysqlPassword'],
                                           db_name=installation_info['mysqlDatabase'],
                                           obstory_id=installation_info['observatoryId'])

    # Open connection to database
    [db0, conn] = connect_db.connect_db()

    # Fetch user ID
    conn.execute('SELECT userId FROM pigazing_users WHERE username=%s;', (username,))
    results = conn.fetchall()
    assert len(results) > 0, "No such user <{}>".format(username)

    # Fetch observatory ID
    conn.execute('SELECT uid FROM archive_observatories WHERE publicId=%s;', (observatory,))
    results = conn.fetchall()
    assert len(results) > 0, "No such observatory <{}>".format(observatory)

    # Look up image EXIF metadata
    metadata = fetch_exif_metadata(input_path=image, time_offset=time_offset)

    # Create observation object for this image
    utc = time.time()
    obs_obj = db.register_observation(obstory_id=observatory,
                                      random_id=True,
                                      obs_time=metadata['Time'],
                                      creation_time=utc,
                                      obs_type="image", user_id=username,
                                      obs_meta=[],
                                      published=1, moderated=1, featured=0,
                                      ra=-999, dec=-999,
                                      field_width=None, field_height=None,
                                      position_angle=None, central_constellation=None,
                                      altitude=-999, azimuth=-999, alt_az_pa=None,
                                      astrometry_processed=None, astrometry_processing_time=None,
                                      astrometry_source=None)

    # Create metadata about image
    obs_id = obs_obj.id
    db.set_observation_metadata(username, obs_id, obsarchive_model.Meta("Observer", username))
    db.set_observation_metadata(username, obs_id, obsarchive_model.Meta("Caption", title))

    for key, value in metadata.items():
        db.set_observation_metadata(user_id=username,
                                    observation_id=obs_id,
                                    meta=obsarchive_model.Meta(key, value))

    db.commit()

    # Make copy of file
    tmp_file_path = os_path.join(our_path, "../auto/tmp/dss_images")
    os.system("mkdir -p {}".format(tmp_file_path))
    img_name = os_path.split(image)[1]
    tmp_filename = os_path.join(tmp_file_path, img_name)
    os.system("cp '{}' '{}'".format(image, tmp_filename))
    os.system("chmod 644 '{}'".format(tmp_filename))

    # Create file object for this image
    file_obj = db.register_file(file_path=tmp_filename, user_id=username, mime_type="image/png",
                                semantic_type=semantic_type, primary_image=True,
                                file_time=metadata['Time'], file_meta=[],
                                observation_id=obs_id,
                                random_id=True)
    db.commit()


if __name__ == "__main__":
    # Read commandline arguments
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--username',
                        required=True,
                        dest='username',
                        help='The username of the user who is to own this image')
    parser.add_argument('--observatory',
                        required=True,
                        dest='observatory',
                        help='The observatory from which this observation was made')
    parser.add_argument('--title',
                        required=True,
                        dest='title',
                        help='The title of this image')
    parser.add_argument('--image',
                        action='append',
                        dest='images',
                        help='The filename(s) of the image(s) to be inserted')
    parser.add_argument('--time-offset',
                        default=0,
                        dest='time_offset',
                        type=int,
                        help='Time offset to apply to the recorded time stamp of an image, seconds. Positive means we '
                             'advance the time.')
    args = parser.parse_args()

    for item in args.images:
        for filename in glob.glob(item):
            new_image(image=filename,
                      username=args.username,
                      title=args.title,
                      observatory=args.observatory,
                      time_offset=args.time_offset)
