#!/bin/bash
read -p "This will destroy and rebuild the meteorpi databases, hit 'y' to confirm or any other key to cancel." -n 1 -r
echo 
if [[ $REPLY =~ ^[Yy]$ ]]
then
    dbs=('meteorpi' 'meteorpi_test1' 'meteorpi_test2')
    for dbname in "${dbs[@]}"
    do
        echo "1/3: Deleting file at '/var/lib/firebird/2.5/data/$dbname.fdb' if it exists"
        rm -f /var/lib/firebird/2.5/data/$dbname.fdb
        echo "2/3: Creating database file at '/var/lib/firebird/2.5/data/$dbname.fdb'"
        sed s/DATABASENAME/$dbname/ < create-database.sql | isql-fb -quiet
        echo "3/3: Sourcing definitions from 'camera-schema.sql' with user 'meteorpi'"
        sed s/DATABASENAME/$dbname/ < camera-schema.sql | isql-fb -quiet -user meteorpi -password meteorpi
        echo "Operation completed."
        # do dangerous stuff
    done
else
    echo "Operation cancelled, no changes made."
fi
