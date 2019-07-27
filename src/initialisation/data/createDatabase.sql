# createDatabase.sql
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

# Create user account and database for archiving observations

# Delete pre-existing pigazing user account, if any
DROP USER IF EXISTS 'pigazing'@'localhost';

# Create pigazing user
CREATE USER 'pigazing'@'localhost' IDENTIFIED BY 'pigazing';

# Delete pre-existing database, if one exists
DROP DATABASE IF EXISTS pigazing;

# Create new database
CREATE DATABASE pigazing;
GRANT ALL ON pigazing.* TO 'pigazing'@'localhost';
