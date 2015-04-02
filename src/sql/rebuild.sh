#!/bin/bash
read -p "This will destroy and rebuild the meteorpi database, hit 'y' to confirm or any other key to cancel." -n 1 -r
echo 
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "1/3: Deleting file at '/var/lib/firebird/2.5/data/meteorpi.fdb' if it exists"
    rm -f /var/lib/firebird/2.5/data/meteorpi.fdb
    echo "2/3: Creating database file at '/var/lib/firebird/2.5/data/meteorpi.fdb'"
    isql-fb -quiet -input create-database.sql
    echo "3/3: Sourcing definitions from 'camera-schema.sql' with user 'meteorpi'"
    isql-fb -quiet -user meteorpi -password meteorpi -input camera-schema.sql
    echo "Operation completed."
    # do dangerous stuff
else
    echo "Operation cancelled, no changes made."
fi
