#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# editUser.py
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
Edit a user's account details.
"""

import passlib.hash
import argparse

from pigazing_helpers import connect_db


def edit_user(username, delete=False, password=None,
              name=None, job=None, email=None, join_date=None, profile_pic=None, profile_text=None,
              add_roles=None, remove_roles=None):
    """
    Edit a user's account details.

    :param username:
        Username for the user account that we are to edit
    :param delete:
        Boolean flag indicating whether we are to delete the observatory altogether
    :param password:
        New password for this user
    :param name:
        New real name for this user
    :param job:
        New job description for this user
    :param email:
        New email address for this user
    :param join_date:
        New join date for this user
    :param profile_pic:
        New profile picture for this user
    :param profile_text:
        New profile text for this user
    :param add_roles:
        New list of roles for this user
    :type add_roles:
        list
    :param remove_roles:
        List of roles to remove from this user
    :type remove_roles:
        list
    :return:
        None
    """

    # Open connection to database
    [db0, conn] = connect_db.connect_db()

    # Fetch user ID
    user_id = None
    while True:
        conn.execute('SELECT userId FROM pigazing_users WHERE username=%s;', (username,))
        results = conn.fetchall()
        if len(results) > 0:
            user_id = results[0]['userId']
            break
        conn.execute('INSERT INTO pigazing_users (username) VALUES (%s);', (username,))

    if delete:
        conn.execute('DELETE FROM pigazing_users WHERE userId=%s;', (user_id,))
        db0.commit()
        db0.close()
        return

    if password:
        conn.execute('UPDATE pigazing_users SET password=%s WHERE userId=%s;',
                     (passlib.hash.bcrypt.encrypt(password), user_id))

    if name is not None:
        conn.execute('UPDATE pigazing_users SET name = %s WHERE userId = %s', (name, user_id))
    if job is not None:
        conn.execute('UPDATE pigazing_users SET job = %s WHERE userId = %s', (job, user_id))
    if email is not None:
        conn.execute('UPDATE pigazing_users SET email = %s WHERE userId = %s', (email, user_id))
    if join_date is not None:
        conn.execute('UPDATE pigazing_users SET joinDate = %s WHERE userId = %s', (join_date, user_id))
    if profile_pic is not None:
        conn.execute('UPDATE pigazing_users SET profilePic = %s WHERE userId = %s', (profile_pic, user_id))
    if profile_text is not None:
        conn.execute('UPDATE pigazing_users SET profileText = %s WHERE userId = %s', (profile_text, user_id))

    if add_roles:
        for role in add_roles:
            conn.execute("SELECT roleId FROM pigazing_roles WHERE name=%s;", (role,))
            results = conn.fetchall()
            if len(results) < 1:
                conn.execute("INSERT INTO pigazing_roles (name) VALUES (%s);", (role,))
                conn.execute("SELECT roleId FROM pigazing_roles WHERE name=%s;", (role,))
                results = conn.fetchall()

            conn.execute('INSERT INTO pigazing_user_roles (userId, roleId) VALUES '
                         '((SELECT u.userId FROM pigazing_users u WHERE u.userId=%s),'
                         '%s)', (user_id, results[0]['roleId']))

    if remove_roles:
        for role in remove_roles:
            conn.execute('DELETE FROM pigazing_user_roles WHERE userId=%s AND '
                         'roleId=(SELECT roleId FROM pigazing_roles WHERE name=%s);', (user_id, role))

    # Commit changes to database
    db0.commit()
    db0.close()


if __name__ == "__main__":
    # Read commandline arguments
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--username',
                        required=True,
                        dest='username',
                        help='Username for the user account that we are to edit')
    parser.add_argument('--password',
                        default=None,
                        dest='password',
                        help='New password for this user')
    parser.add_argument('--name',
                        default=None,
                        dest='name',
                        help='New real name for this user')
    parser.add_argument('--job',
                        default=None,
                        dest='job',
                        help='New job description for this user')
    parser.add_argument('--email',
                        default=None,
                        dest='email',
                        help='New email address for this user')
    parser.add_argument('--join-date',
                        default=None,
                        dest='join_date',
                        help='New join date for this user')
    parser.add_argument('--profile-pic',
                        default=None,
                        dest='profile_pic',
                        help='New profile picture for this user')
    parser.add_argument('--profile-text',
                        default=None,
                        dest='profile_text',
                        help='New profile text for this user')
    parser.add_argument('--delete',
                        action='store_true',
                        dest='delete',
                        help='This switch deletes the user altogether')
    parser.add_argument('--add_roles',
                        action='append',
                        dest='add_roles',
                        help='Add a role to this user')
    parser.add_argument('--remove_roles',
                        action='append',
                        dest='remove_roles',
                        help='Remove a role from this user')
    args = parser.parse_args()

    edit_user(username=args.username,
              delete=args.delete,
              password=args.password,
              name=args.name,
              job=args.job,
              email=args.email,
              join_date=args.join_date,
              profile_pic=args.profile_pic,
              profile_text=args.profile_text,
              add_roles=args.add_roles,
              remove_roles=args.remove_roles)
