# make_htaccess.py
# Pi Gazing
# Dominic Ford

# -------------------------------------------------
# Copyright 2019 Dominic Ford.

# This file is part of Pi Gazing.

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


def make_htaccess(dirpath):
    out = open(os.path.join(dirpath, ".htaccess"), "w")

    force_https = """
RewriteCond %{HTTPS} !=on
RewriteCond %{REQUEST_URI} !google97b1895dd6619486.html
RewriteCond %{REQUEST_URI} !^/berg/
RewriteRule ^/?(.*) https://%{SERVER_NAME}/$1 [R,L]
"""

    out.write("""\
Options +Indexes
DirectoryIndex index.php
AddType application/pdf .pdf
AddType application/json .json
AddType text/html .html
AddType text/css .css
AddType application/rss+xml .rss
AddType application/x-httpd-php .php
AddHandler cgi-script .php
Options +ExecCGI
RewriteEngine on

"""+force_https+"""

####################
# GZIP COMPRESSION #
####################
SetOutputFilter DEFLATE
AddOutputFilterByType DEFLATE text/html text/css text/plain text/xml application/javascript application/json text/xml
BrowserMatch ^Mozilla/4 gzip-only-text/html
BrowserMatch ^Mozilla/4\.0[678] no-gzip
BrowserMatch \bMSIE !no-gzip !gzip-only-text/html
BrowserMatch \bMSI[E] !no-gzip !gzip-only-text/html
SetEnvIfNoCase Request_URI \.(?:gif|jpe?g|png)$ no-gzip
Header append Vary User-Agent env=!dont-vary

<IfModule mod_expires.c>
  ExpiresActive On
  ExpiresDefault "access plus 1 seconds"
  ExpiresByType text/html "access plus 1 seconds"
  ExpiresByType image/gif "access plus 120 minutes"
  ExpiresByType image/jpeg "access plus 120 minutes"
  ExpiresByType image/png "access plus 120 minutes"
  ExpiresByType text/css "access plus 60 minutes"
  ExpiresByType application/json "access plus 120 minutes"
  ExpiresByType application/javascript "access plus 60 minutes"
  ExpiresByType text/xml "access plus 60 minutes"
</IfModule>
""")
    out.close()
