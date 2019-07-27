#!/usr/bin/python
# -*- coding: utf-8 -*-
# deployRaspberryPi.py
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

import os

# Make sure we are running as root
if os.geteuid() != 0:
    print("This script must be run as root.")
    sys.exit(1)

# Change into the directory <src/initialisation>
os.chdir(os.path.dirname(sys.argv[0]))

print("1/7: Creating database and associated user in MySQL. You will need to enter your MySQL root password")
os.system("mysql -u root < data/createDatabase.sql")

print("2/7: Building the C code")
os.system("cd ../observe/video_analysis/ ; ./prettymake")
os.system("cd ../../helpers/image_processing/ ; ./prettymake")

print("3/7: Creating MySQL configuration file, so that we don't have to pass passwords on the command line")
./makeMysqlConfig.py

print("4/7: Setting up database schema."
os.system("mysql --defaults-extra-file=../../datadir/mysql_login.cfg < data/databaseSchema.sql")

print("5/7: Creating directory to store files associated with database")
os.system("mkdir -p ../../datadir/raw_video ../../datadir/db_filestore ../../datadir/thumbnails")
os.system("chown www-data:www-data ../../datadir/thumbnails")
os.system("rm -f ../../datadir/db_filestore/* ../../datadir/thumbnails/*")

print("6/7: Populating table of constellations")
os.system("./populateConstellations.py")

print("7/7: Set up default exports")
os.system("../command_line/addExport.py")
