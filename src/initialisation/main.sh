#!/bin/bash

# Change into the sql directory
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
cd ${DIR}


read -p $'This will destroy and rebuild the Pi Gazing databases.\nHit "Y" to confirm or any other key to cancel.\n' -n 1 -r
echo 
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "1/5: Creating database and associated user in MySQL. You will need to enter your MySQL root password."
    sudo mysql -u root -p < create_database.sql

    echo "2/5: Creating MySQL configuration file, so that we don't have to pass passwords on the command line."
    ./make_mysql_config.py

    echo "3/5: Setting up database schema."
    sudo mysql --defaults-extra-file=../../datadir/mysql_login.cfg < database_schema.sql

    echo "4/5: Populating table of constellations."
    ./populate_constellations.py

    echo "5/5: Set up default exports."
    ./default_exports.py
else
    echo "Operation cancelled, no changes made."
fi
