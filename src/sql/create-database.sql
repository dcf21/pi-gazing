/* Creates the database, file must not exist */
SET SQL DIALECT 3;

CREATE DATABASE '/var/lib/firebird/2.5/data/meteorpi.fdb' 
USER 'meteorpi' 
PASSWORD 'meteorpi'
PAGE_SIZE 16384 
DEFAULT CHARACTER SET UNICODE_FSS;
