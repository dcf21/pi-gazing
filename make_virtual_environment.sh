#!/bin/bash

cd "$(dirname "$0")"
cwd=`pwd`

# Sometimes this line is necessary, if your locale settings are broken
export LC_ALL=C

# Create virtual environment
mkdir -p datadir
rm -Rf datadir/virtualenv
virtualenv -p python3 datadir/virtualenv
source datadir/virtualenv/bin/activate

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

# Install custom python libraries
cd ${cwd}
cd src/helpers/python_packages
rm -Rf build dist *.egg-info  # Clear out the cache to make sure we install latest version of code
python setup.py develop

# Make data directory
mkdir -p datadir

