#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# databaseBackup.py
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

import os
import datetime

from pigazing_helpers.settings_read import settings, installation_info

now = datetime.datetime.now()

filename = "mysqlDump_{:04d}{:02d}{:02d}_{:02d}{:02d}{:02d}.sql.gz".format(
    now.year, now.month, now.day, now.hour, now.minute, now.second)

cmd = "mysqldump --defaults-extra-file={config} {database} | gzip > {output}".format(
    config=os.path.join(settings['dataPath'], "mysql_login.cfg"),
    database=installation_info['mysqlDatabase'],
    output=os.path.join(settings['dataPath'], filename))

print(cmd)
os.system(cmd)
