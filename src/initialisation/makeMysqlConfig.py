#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# makeMysqlConfig.py
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
from pigazing_helpers.settings_read import settings, installation_info


def make_mysql_login_config():
    """
    Create MySQL configuration file with username and password, which means we can log into database without
    supplying these on the command line.

    :return:
        None
    """

    db_config = os.path.join(settings['dataPath'], "mysql_login.cfg")

    config_text = """
[client]
user = {:s}
password = {:s}
host = {:s}
default-character-set = utf8mb4

[mysql]
database = {:s}
""".format(installation_info['mysqlUser'], installation_info['mysqlPassword'], installation_info['mysqlHost'],
           installation_info['mysqlDatabase'])
    open(db_config, "w").write(config_text)


# Do it right away if we're run as a script
if __name__ == "__main__":
    make_mysql_login_config()
