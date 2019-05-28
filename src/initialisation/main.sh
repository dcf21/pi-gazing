#!/bin/bash

# Change into the directory <src/initialisation>
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
cd ${DIR}


read -p $'This will destroy and rebuild the Pi Gazing databases.\nHit "Y" to confirm or any other key to cancel.\n' -n 1 -r
echo 
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "1/6: Creating database and associated user in MySQL. You will need to enter your MySQL root password."
    sudo mysql -u root -p < createDatabase.sql

    echo "2/6: Creating MySQL configuration file, so that we don't have to pass passwords on the command line."
    ./makeMysqlConfig.py

    echo "3/6: Setting up database schema."
    sudo mysql --defaults-extra-file=../../datadir/mysql_login.cfg < databaseSchema.sql

    echo "4/6: Creating directory to store files associated with database."
    mkdir -p ../../datadir/raw_video
    mkdir -p ../../datadir/db_filestore
    mkdir -p ../../datadir/thumbnails
    sudo chown www-data:www-data ../../datadir/thumbnails
    sudo rm -f ../../datadir/db_filestore/*
    sudo rm -f ../../datadir/thumbnails/*

    echo "5/6: Populating table of constellations."
    ./populateConstellations.py

    echo "6/6: Set up default exports."
    ./defaultExports.py
else
    echo "Operation cancelled, no changes made."
fi
