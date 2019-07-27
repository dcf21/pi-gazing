#!/usr/bin/python
# -*- coding: utf-8 -*-
# install.py
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

def fix_gpd_demon():
    """
    Fix GPS configuration, so that it looks for USB devices
    """

    gpsd_config = open("/etc/default/gpsd").read()
    gpsd_config = re.sub('DEVICES=""', 'DEVICES="/dev/ttyUSB0"', gpsd_config)
    with open("/etc/default/gpsd", "w") as f:
      f.write(gpsd_config)

def write_apache_virtual_host_config(hostname="pigazing.local"):
    """
    Write a configuration file for the virtual host for the Pi Gazing web interface
    """

    installation_path=os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../.."))

    apache_config = """
<VirtualHost *:80>
        ServerName {hostname}
        RewriteEngine on
        ReWriteCond %{{SERVER_PORT}} !^443$
        RewriteRule ^/(.*) https://%{{HTTP_HOST}/$1 [NC,R,L]
</VirtualHost>
<VirtualHost *:443>
        DocumentRoot {installation_path}/src/observatory_website/dist
        ServerName {hostname}
        SSLEngine On
        SSLCertificateFile    {installation_path}/src/observatory_website/web_api/pigazing_cert.pem
        SSLCertificateKeyFile {installation_path}/src/observatory_website/web_api/pigazing_cert.key
        WSGIPassAuthorization On
        WSGIDaemonProcess pigazingapplication user=www-data group=www-data threads=5 python-home={installation_path}/datadir/virtualenv
        WSGIScriptAlias /api {installation_path}/src/observatory_website/web_api/pigazing_application.wsgi
        <Directory {installation_path}>
                AllowOverride All
                WSGIProcessGroup pigazingapplication
                WSGIApplicationGroup %{GLOBAL}
                Require all granted
        </Directory>
</VirtualHost>
""".format(hostname=hostname, installation_path=installation_path)

# Do it right away if we're run as a script
if __name__ == "__main__":
    fix_gpd_demon()
    write_apache_virtual_host_config()
