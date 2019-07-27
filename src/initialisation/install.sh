#!/bin/bash
# install.sh
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

# Switch to the directory containing the installation scripts
cd "$(dirname "$0")"
cwd=`pwd`

# Check that script is being run as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root"
   exit 1
fi

# Send output to log file
mkdir -p ../../datadir
exec &> ../../datadir/install.stdout

# Log that we've starting installation
echo "[`date`] Starting Pi Gazing installation" | tee -a ../../datadir/install.stderr

# Install required packages
echo "[`date`] Updating Ubuntu" | tee -a ../../datadir/install.stderr
apt-get update 2>> ../../datadir/install.stderr
apt-get -y dist-upgrade 2>> ../../datadir/install.stderr

# Packages required to go headless
echo "[`date`] Installing Ubuntu packages required to go headless" | tee -a ../../datadir/install.stderr
apt-get -y install openssh-server vim screen avahi-daemon 2>> ../../datadir/install.stderr

# Packages required to build Pi Gazing
echo "[`date`] Installing Ubuntu packages required by Pi Gazing" | tee -a ../../datadir/install.stderr
apt-get -y install gpsd gpsd-clients libjpeg-dev libpng-dev libgsl-dev git qiv mplayer libv4l-dev libavutil-dev \
           libavcodec-dev libavformat-dev libx264-dev scons libcairo2-dev libcfitsio-dev libnetpbm10-dev netpbm \
           python3-dev python3-astropy python3-numpy python3-scipy python3-pil python3-dateutil python3-pip swig \
           ffmpeg python3-setuptools python3-virtualenv apache2 libapache2-mod-wsgi-py3 python3-tornado python3-flask \
           build-essential libpcre++-dev libboost-dev libboost-program-options-dev libboost-thread-dev \
           libboost-filesystem-dev libblas-dev liblapack-dev gfortran libffi-dev libssl-dev imagemagick gphoto2 \
           libbz2-dev php-db php-mysql php-pear libapache2-mod-php mysql-server mysql-client libmysqlclient-dev \
           software-properties-common cmake astrometry.net astrometry-data-tycho2 python-virtualenv python-pip \
           python-dev libxml2-dev libxslt-dev certbot \
           2>> ../../datadir/install.stderr

# Steps that we only need to run on Raspberry Pi
if [ -x "$(command -v python)" ] ; then
    R_PI=`python -c "import platform; print 'raspberrypi' in platform.uname()"`

    if [ "$R_PI" = "True" ] ; then

        # If we're running on a raspberry pi, we need more than 1GB of RAM for some build steps. We add some
        # virtual memory
        echo "[`date`] Activating swap, to avoid running out of RAM" | tee -a ../../datadir/install.stderr
        dd if=/dev/zero of=/swapfile bs=1024 count=1048576
        chmod 600 /swapfile
        mkswap /swapfile
        swapon /swapfile
        swapon --show

        # We need to Raspberry Pi GPU header files, which aren't shipped in Ubuntu. So let's compile the drivers
        # from source
        echo "[`date`] Installing Raspberry Pi libraries" | tee -a ../../datadir/install.stderr
        cd /root
        git clone https://github.com/raspberrypi/userland.git 2>> ${cwd}/../../datadir/install.stderr
        cd userland
        ./buildme 2>> ${cwd}/../../datadir/install.stderr
    fi
fi

# Fix broken locales
echo "[`date`] Fixing locales" | tee -a ../../datadir/install.stderr
export LANGUAGE=en_GB.UTF-8; export LANG=en_GB.UTF-8; export LC_ALL=en_GB.UTF-8; locale-gen en_GB.UTF-8
dpkg-reconfigure --frontend noninteractive locales

# Create virtual environment
cd $cwd
echo "[`date`] Creating python virtual environment" | tee -a ../../datadir/install.stderr
./makeVirtualEnvironment.sh 2>> ../../datadir/install.stderr

# Set up database
cd $cwd
echo "[`date`] Creating Pi Gazing database" | tee -a ../../datadir/install.stderr
./flushDatabase.py 2>> ../../datadir/install.stderr

# Install node.js
cd $cwd
echo "[`date`] Building node.js" | tee -a ../../datadir/install.stderr
cd /root
wget https://nodejs.org/dist/v10.14.2/node-v10.14.2.tar.gz
tar xvfz node-v10.14.2.tar.gz
cd node-v10.14.2
./configure 2>> ${cwd}/../../datadir/install.stderr
make 2>> ${cwd}/../../datadir/install.stderr
sudo make install 2>> ${cwd}/../../datadir/install.stderr
sudo npm update 2>> ${cwd}/../../datadir/install.stderr
sudo npm install npm -g 2>> ${cwd}/../../datadir/install.stderr
sudo npm install -g bower uglify-js less less-plugin-clean-css 2>> ${cwd}/../../datadir/install.stderr

# Set up web interface
cd $cwd
echo "[`date`] Setting up web interface" | tee -a ../../datadir/install.stderr
cd ../web_interface
bower --allow-root install
cd build
./build.py

# Create HTTPS certificate
cd $cwd
echo "[`date`] Creating https certificate" | tee -a ../../datadir/install.stderr
cd ../web_interface/web_api/
openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout pigazing_cert.key -out pigazing_cert.pem -subj '/CN=localhost'

# Configure apache
cd $cwd
echo "[`date`] Configuring apache" | tee -a ../../datadir/install.stderr
cd /etc/apache2/mods-enabled/
ln -s ../mods-available/rewrite.load
ln -s ../mods-available/ssl.conf
ln -s ../mods-available/ssl.load
ln -s ../mods-available/socache_shmcb.load

# Write apache virtual host configuration
cd $cwd
echo "[`date`] Writing apache virtual host configuration" | tee -a ../../datadir/install.stderr
python install.py | tee -a ../../datadir/install.stderr

# Enable the web interface
cd $cwd
echo "[`date`] Enabling the web interface" | tee -a ../../datadir/install.stderr
a2ensite pigazing.local.conf
service apache2 restart

# Log that we've finished installation
echo "[`date`] Completed Pi Gazing installation" | tee -a ../../datadir/install.stderr

