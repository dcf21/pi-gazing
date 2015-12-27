# create-database.sql

# Create user account and database for archiving observations

# Delete pre-existing meteorpi user account, if any
GRANT USAGE ON *.* TO 'meteorpi'@'localhost';
DROP USER 'meteorpi'@'localhost';

# Create meteorpi user
CREATE USER 'meteorpi'@'localhost'
  IDENTIFIED BY 'meteorpi';
DROP DATABASE IF EXISTS meteorpi;
CREATE DATABASE meteorpi;
GRANT ALL ON meteorpi.* TO 'meteorpi'@'localhost';

