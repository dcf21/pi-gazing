#!/bin/bash

# Change into the directory <src/initialisation>
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
cd ${DIR}


read -p $'This will destroy and rebuild the Pi Gazing databases.\nHit "Y" to confirm or any other key to cancel.\n' -n 1 -r
echo 
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "1/7: Creating database and associated user in MySQL. You will need to enter your MySQL root password."
    sudo mysql -u root -p < createDatabase.sql

    echo "2/7: Building the C code."
    cd ../observe/video_analysis/
    ./prettymake
    cd ../../helpers/image_processing/
    ./prettymake
    cd ${DIR}

    echo "3/7: Creating MySQL configuration file, so that we don't have to pass passwords on the command line."
    ./makeMysqlConfig.py

    echo "4/7: Setting up database schema."
    sudo mysql --defaults-extra-file=../../datadir/mysql_login.cfg < databaseSchema.sql

    echo "5/7: Creating directory to store files associated with database."
    mkdir -p ../../datadir/raw_video
    mkdir -p ../../datadir/db_filestore
    mkdir -p ../../datadir/thumbnails
    sudo chown www-data:www-data ../../datadir/thumbnails
    sudo rm -f ../../datadir/db_filestore/*
    sudo rm -f ../../datadir/thumbnails/*

    echo "6/7: Populating table of constellations."
    ./populateConstellations.py

    echo "7/7: Set up default exports."
    ./defaultExports.py
else
    echo "Operation cancelled, no changes made."
fi
