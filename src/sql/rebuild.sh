#!/bin/bash
read -p "This will destroy and rebuild the meteorpi databases, hit 'y' to confirm or any other key to cancel." -n 1 -r
echo 
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "1/2: Creating database and associated user in MySQL. You will need to enter your MySQL root password."
    mysql -u root -p < create-database.sql
    echo "2/2: Setting up database schema"
    mysql -u meteorpi --password=meteorpi meteorpi < archive-schema.sql
else
    echo "Operation cancelled, no changes made."
fi
