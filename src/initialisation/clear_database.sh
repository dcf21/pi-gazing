#!/bin/bash

# Change into the sql directory
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
cd ${DIR}


read -p "This will destroy and rebuild the Pi Gazing databases, hit 'y' to confirm or any other key to cancel." -n 1 -r
echo 
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "1/4: Creating database and associated user in MySQL. You will need to enter your MySQL root password."
    sudo mysql -u root -p < create_database.sql

    echo "2/4: Creating MySQL configuration file, so that we don't have to pass passwords on the command line."
    ./make_mysql_config.py

    echo "3/4: Setting up database schema."
    sudo mysql --defaults-extra-file=../../datadir/mysql_login.cfg < database_schema.sql

    echo "4/4: Populating table of constellations."
    ./populate_constellations.py
else
    echo "Operation cancelled, no changes made."
fi
