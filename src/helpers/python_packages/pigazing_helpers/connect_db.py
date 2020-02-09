# -*- coding: utf-8 -*-
# connect_db.py
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

# Ignore SQL warnings
import warnings

import MySQLdb

from .settings_read import installation_info as settings

warnings.filterwarnings("ignore", ".*Unknown table .*")

# Look up MySQL database log in details
db_host = settings['mysqlHost']
db_user = settings['mysqlUser']
db_passwd = settings['mysqlPassword']
db_name = settings['mysqlDatabase']


# Open database
def connect_db():
    """
    Return a new MySQLdb connection to the database.

    :return:
        List of [database handle, connection handle]
    """

    global db_host, db_name, db_passwd, db_user
    db = MySQLdb.connect(host=db_host, user=db_user, passwd=db_passwd, db=db_name)
    c = db.cursor(cursorclass=MySQLdb.cursors.DictCursor)

    db.set_character_set('utf8mb4')
    c.execute('SET NAMES utf8mb4;')
    c.execute('SET CHARACTER SET utf8mb4;')
    c.execute('SET character_set_connection=utf8mb4;')

    return [db, c]


# Fetch the ID number associated with a particular data generator string ID
def fetch_generator_key(c, gen_key):
    """
    Return the ID number associated with a particular data generator string ID. Used to track which python scripts
    generate which entries in the database.

    :param c:
        MySQLdb database connection.
    :param gen_key:
        String data generator identifier.
    :return:
        Numeric data generator identifier.
    """

    c.execute("SELECT generatorId FROM pigazing_generators WHERE name=%s;", (gen_key,))
    tmp = c.fetchall()
    if len(tmp) == 0:
        c.execute("INSERT INTO pigazing_generators VALUES (NULL, %s);", (gen_key,))
        c.execute("SELECT generatorId FROM pigazing_generators WHERE name=%s;", (gen_key,))
        tmp = c.fetchall()
    gen_id = tmp[0]["generatorId"]
    return gen_id


# Fetch the ID number associated with a particular data source
def fetch_source_id(c, source_info):
    """
    Return the ID number associated with a particular data source string ID. Used to track which scientific sources
    generate which entries in the database.

    :param c:
        MySQLdb database connection.
    :param source_info:
        String data source identifier.
    :return:
        Numeric data source identifier.
    """

    [source_abbrev, source_name, source_url] = source_info
    c.execute("SELECT sourceId FROM pigazing_sources WHERE abbrev=%s;", (source_abbrev,))
    tmp = c.fetchall()
    if len(tmp) == 0:
        c.execute("INSERT INTO pigazing_sources VALUES (NULL, %s, %s, %s);",
                  (source_abbrev, source_name, source_url))
        c.execute("SELECT sourceId FROM pigazing_sources WHERE abbrev=%s;", (source_abbrev,))
        tmp = c.fetchall()
    source_id = tmp[0]["sourceId"]
    return source_id
