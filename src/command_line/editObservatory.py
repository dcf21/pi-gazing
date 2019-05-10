#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# editObservatory.py
#
# -------------------------------------------------
# Copyright 2015-2019 Dominic Ford
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
Edit an observatory record, or create a new one
"""

import argparse

from pigazing_helpers import connect_db
from pigazing_helpers.settings_read import installation_info


def edit_observatory(public_id, delete=False, name=None, latitude=None, longitude=None, owner=None):
    """
    Edit an observatory record, or create a new one.

    :param public_id:
        The public id of the observatory we are to edit
    :param delete:
        Boolean flag indicating whether we are to delete the observatory altogether
    :param name:
        The new name of the observatory
    :param latitude:
        The new latitude of the observatory
    :param longitude:
        The new longitude of the observatory
    :param owner:
        The user responsible for this observatory
    :return:
        None
    """
    # Open connection to database
    [db0, conn] = connect_db.connect_db()

    # Fetch observatory ID
    obs_id = None
    while True:
        conn.execute('SELECT uid FROM archive_observatories WHERE publicId=%s;', (public_id,))
        results = conn.fetchall()
        if len(results) > 0:
            obs_id = results[0]['uid']
            break
        conn.execute('INSERT INTO archive_observatories (publicId, location) VALUES (%s, POINT(-999,-999));',
                     (public_id,))

    if delete:
        conn.execute('DELETE FROM archive_observatories WHERE uid=%s;', (obs_id,))
        db0.commit()
        db0.close()
        return

    if name:
        conn.execute('UPDATE archive_observatories SET name=%s WHERE uid=%s;', (name, obs_id))

    if latitude and longitude:
        conn.execute('UPDATE archive_observatories SET location=POINT(%s,%s) WHERE uid=%s;',
                     (longitude, latitude, obs_id))
        
    if owner:
        conn.execute('UPDATE archive_observatories SET userId=%s WHERE uid=%s;', (owner, obs_id))

    # Commit changes to database
    db0.commit()
    db0.close()


if __name__ == "__main__":
    # Read commandline arguments
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publicId',
                        default=installation_info['observatoryId'],
                        dest='publicId',
                        help='The public id of the observatory we are to edit or create')
    parser.add_argument('--name',
                        default=None,
                        dest='name',
                        help='The new name of the observatory')
    parser.add_argument('--owner',
                        default=None,
                        dest='owner',
                        help='The username of the owner of the observatory')
    parser.add_argument('--delete',
                        action='store_true',
                        dest='delete',
                        help='This switch deletes the observatory altogether')
    parser.add_argument('--lat',
                        default=None,
                        dest='lat',
                        type=float,
                        help='The new latitude of the observatory')
    parser.add_argument('--lng',
                        default=None,
                        dest='lng',
                        type=float,
                        help='The new longitude of the observatory')
    args = parser.parse_args()

    edit_observatory(public_id=args.publicId,
                     delete=args.delete,
                     name=args.name,
                     latitude=args.lat,
                     longitude=args.lng,
                     owner=args.owner)
