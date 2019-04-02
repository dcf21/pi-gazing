#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# make_mysql_config.py

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
database = {:s}
""".format(installation_info['mysqlUser'], installation_info['mysqlPassword'], installation_info['mysqlHost'],
           installation_info['mysqlDatabase'])
    open(db_config, "w").write(config_text)


# Do it right away if we're run as a script
if __name__ == "__main__":
    make_mysql_login_config()
