#!/bin/bash
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

# Switch to root directory of this Pi Gazing installation
cd "$(dirname "$0")"
cwd=`pwd`/../..

# Sometimes this line is necessary, if your locale settings are broken
export LC_ALL=C

# Create virtual environment
mkdir -p ../../datadir
rm -Rf ../../datadir/virtualenv
virtualenv -p python3 ../../datadir/virtualenv
source ../../datadir/virtualenv/bin/activate

# Install required python libraries
pip install RPi.GPIO
pip install pyyaml
pip install mysqlclient
pip install pytz
pip install python-magic
pip install pillow
pip install lxml
pip install python-dateutil
pip install passlib[bcrypt]
pip install cairocffi
pip install numpy
pip install scipy
pip install astropy
pip install pyopenssl
pip install ndg-httpsclient
pip install pyasn1
pip install requests[security]
pip install requests-toolbelt
pip install flask
pip install flask-cors
pip install flask-jsonpify
pip install bcrypt
pip install gps3
pip install toolz cytoolz dask distributed bokeh

# Install custom python libraries
cd ${cwd}
cd src/helpers/python_packages
rm -Rf build dist *.egg-info  # Clear out the cache to make sure we install latest version of code
python setup.py develop
