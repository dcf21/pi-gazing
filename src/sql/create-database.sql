/* Creates the database, file must not exist */
SET SQL DIALECT 3;
/* localhost:/var/lib/firebird/2.5/data/meteorpi.fdb*/
CREATE DATABASE 'localhost:/var/lib/firebird/2.5/data/DATABASENAME.fdb'
USER 'meteorpi' 
PASSWORD 'meteorpi'
PAGE_SIZE 16384 
DEFAULT CHARACTER SET UNICODE_FSS;
