#!../../virtualenv/bin/python3
# -*- coding: utf-8 -*-
# disk_usage.py
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

"""
This searches through all of the files in the database, and gives a breakdown of the disk usage of different kinds
of files, day by day
"""

import sys
from meteorpi_helpers import dcf_ast
from meteorpi_helpers.obsarchive import obsarchive_db
from meteorpi_helpers.settings_read import settings, installation_info

db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                       db_host=settings['mysqlHost'],
                                       db_user=settings['mysqlUser'],
                                       db_password=settings['mysqlPassword'],
                                       db_name=settings['mysqlDatabase'],
                                       obstory_id=installation_info['observatoryId'])

file_census = {}

# Get list of files in each directory
db.con.execute("SELECT * FROM archive_files;")
for item in db.con.fetchall():
    file_type = item['mimeType']
    date = dcf_ast.inv_julian_day( dcf_ast.jd_from_utc( item['fileTime']))
    date_str = "%04d %02d %02d" % (date[0], date[1], date[2])
    if file_type not in file_census:
        file_census[file_type] = {}
    if date_str not in file_census[file_type]:
        file_census[file_type][date_str] = 0
    file_census[file_type][date_str] += item['fileSize']


def render_data_size_list(data):
    total_file_size = sum(data)
    output = []
    for d in data:
        output.append("%8.2f MB (%5.1f%%)" % (d / 1.e6, d * 100. / total_file_size))
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
    out.write("%25s " % col_head)
out.write("\n")
for row_head in rows:
    out.write("%25s " % row_head)
    data = []
    for col_head in cols:
        if row_head in file_census[col_head]:
            data.append(file_census[col_head][row_head])
        else:
            data.append(0)
    dataStr = render_data_size_list(data)
    for i in range(len(cols)):
        out.write("%25s " % dataStr[i])
    out.write("\n")
