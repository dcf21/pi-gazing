#!../../virtual-env/bin/python
# diskUsage.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# This searches through all of the files in the database, and gives a breakdown of the disk usage of different kinds
# of files, day by day

import sys

import mod_settings
import mod_astro

import meteorpi_db

db = meteorpi_db.MeteorDatabase(mod_settings.settings['dbFilestore'])

file_census = {}

# Get list of files in each directory
db.con.execute("SELECT * FROM archive_files;")
for item in db.con.fetchall():
    file_type = item['mimeType']
    date = mod_astro.inv_julian_day( mod_astro.jd_from_utc( item['fileTime']))
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
cols = file_census.keys()
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
