# create-database.sql

# Create user account and database for archiving observations

# Delete pre-existing pigazing user account, if any
DROP USER IF EXISTS 'pigazing'@'localhost';

# Create pigazing user
CREATE USER 'pigazing'@'localhost' IDENTIFIED BY 'pigazing';

# Delete pre-existing database, if one exists
DROP DATABASE IF EXISTS pigazing;

# Create new database
CREATE DATABASE pigazing;
GRANT ALL ON pigazing.* TO 'pigazing'@'localhost';
