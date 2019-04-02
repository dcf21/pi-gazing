#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# disk_usage.py
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
This searches through all of the files in the database, and gives a breakdown of the disk usage of different kinds
of files, day by day
"""

import sys

from pigazing_helpers import dcf_ast
from pigazing_helpers.obsarchive import obsarchive_db
from pigazing_helpers.settings_read import settings, installation_info

db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                       db_host=installation_info['mysqlHost'],
                                       db_user=installation_info['mysqlUser'],
                                       db_password=installation_info['mysqlPassword'],
                                       db_name=installation_info['mysqlDatabase'],
                                       obstory_id=installation_info['observatoryId'])

file_census = {}

# Get list of files in each directory
db.con.execute("SELECT * FROM archive_files;")
for item in db.con.fetchall():
    file_type = item['mimeType']
    date = dcf_ast.inv_julian_day(dcf_ast.jd_from_unix(item['fileTime']))
    date_str = "{:04d} {:02d} {:02d}".format(date[0], date[1], date[2])
    if file_type not in file_census:
        file_census[file_type] = {}
    if date_str not in file_census[file_type]:
        file_census[file_type][date_str] = 0
    file_census[file_type][date_str] += item['fileSize']


def render_data_size_list(file_sizes):
    """
    Render a list of file sizes and their percentages of the total.

    :param file_sizes:
        A list of file sizes in bytes
    :return:
        Human-readable string
    """
    total_file_size = sum(file_sizes)
    output = []
    for item in file_sizes:
        output.append("{:8.2f} MB ({:5.1f}%)".format(item / 1.e6, item * 100. / total_file_size))
    return output


# Render quick and dirty table
out = sys.stdout
cols = list(file_census.keys())
cols.sort()
rows = []
for col_head in cols:
    for row_head in file_census[col_head]:
        if row_head not in rows:
            rows.append(row_head)
rows.sort()
for col_head in [''] + cols:
    out.write("{:25s} ".format(col_head))
out.write("\n")
for row_head in rows:
    out.write("{:25s} ".format(row_head))
    data = []
    for col_head in cols:
        if row_head in file_census[col_head]:
            data.append(file_census[col_head][row_head])
        else:
            data.append(0)
    data_string = render_data_size_list(file_sizes=data)
    for i in range(len(cols)):
        out.write("{:25s} ".format(data_string[i]))
    out.write("\n")
