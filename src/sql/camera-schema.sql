SET SQL DIALECT 3;
SET NAMES UNICODE_FSS;

/* To run this script you need a clean database set up at
 * /var/lib/firebird/2.5/data/meteorpi.fdb, and be connected
 * as a user with write access to this database.
 * See https://github.com/camsci/meteor-pi/wiki/Camera-database-configuration
 */
CONNECT 'localhost:/var/lib/firebird/2.5/data/meteorpi.fdb';

CREATE DOMAIN BOOLEAN AS SMALLINT CHECK (value is null or value in (0, 1));

/* Sequence used to allocate internal IDs */
CREATE SEQUENCE gidSequence;

/* Camera status tables */

CREATE TABLE t_highWaterMark (
	cameraID char(12) NOT NULL,
	mark timestamp NOT NULL
);

CREATE TABLE t_cameraStatus (
	internalID integer NOT NULL,
	cameraID char(12) NOT NULL,
	validFrom timestamp NOT NULL,
	validTo timestamp,
	softwareVersion integer DEFAULT 0 NOT NULL,
	orientationAltitude float NOT NULL,
	orientationAzimuth float NOT NULL,
	orientationRotation float NOT NULL,
	orientationError float NOT NULL,
	widthOfField float NOT NULL,
	locationLatitude float NOT NULL,
	locationLongitude float NOT NULL,
	locationGPS BOOLEAN DEFAULT 0 NOT NULL,
    locationError float NOT NULL,
	lens varchar(40) NOT NULL,
	sensor varchar(40) NOT NULL,
	instURL varchar(255),
	instName varchar(255),
	PRIMARY KEY (internalID)
);

CREATE TABLE t_visibleRegions (
	cameraStatusID integer NOT NULL,
	region integer NOT NULL,
	pointOrder integer DEFAULT 0 NOT NULL,
	x integer NOT NULL,
	y integer NOT NULL,
	FOREIGN KEY (cameraStatusId) REFERENCES t_cameraStatus(internalId) ON DELETE CASCADE,
	PRIMARY KEY (cameraStatusId, region, pointOrder)
);

SET TERM ^ ;
CREATE OR ALTER TRIGGER assignStatusID FOR t_cameraStatus 
BEFORE INSERT position 10 
AS BEGIN
  if ((new.internalID is null) or (new.internalID = 0)) then
  begin
    new.internalID = gen_id(gidSequence, 1);
  end
end ^
SET TERM ; ^

/* A single observed event from a particular camera */
CREATE TABLE t_event (
	internalID integer NOT NULL,
	eventID char(16) CHARACTER SET OCTETS NOT NULL, /* Always use literal byte values */
	cameraID char(12) NOT NULL,
	eventTime timestamp NOT NULL,
	intensity integer DEFAULT 0 NOT NULL,
	x1 integer DEFAULT 0 NOT NULL,
	y1 integer DEFAULT 0 NOT NULL,
	x2 integer DEFAULT 0 NOT NULL,
	y2 integer DEFAULT 0 NOT NULL,
	x3 integer DEFAULT 0 NOT NULL,
	y3 integer DEFAULT 0 NOT NULL,
	x4 integer DEFAULT 0 NOT NULL,
	y4 integer DEFAULT 0 NOT NULL,
    statusID integer NOT NULL,
    FOREIGN KEY (statusID) REFERENCES t_cameraStatus (internalID) ON DELETE CASCADE,
	PRIMARY KEY (internalID)
);

/* Links to files in whatever external store we use */
CREATE TABLE t_file (
	internalID integer NOT NULL,
	cameraID char(12) NOT NULL,
	fileID char(16) CHARACTER SET OCTETS NOT NULL, /* Always use literal byte values */
	mimeType varchar(100) default 'text/plain' NOT NULL,
	semanticType varchar(255) NOT NULL,
	fileTime timestamp NOT NULL,
	fileSize integer NOT NULL,
    statusID integer NOT NULL,
    FOREIGN KEY (statusID) REFERENCES t_cameraStatus (internalID) ON DELETE CASCADE,
	PRIMARY KEY (internalId)
);

/* Rows of metadata pertaining to a single file per row */
CREATE TABLE t_fileMeta (
	internalID integer NOT NULL,
	metaKey varchar(255) NOT NULL,
	stringValue varchar(255) NOT NULL,
	fileID integer NOT NULL,
	metaIndex integer DEFAULT 0 NOT NULL,
	PRIMARY KEY (internalID),
	FOREIGN KEY (fileID) REFERENCES t_file (internalID) ON DELETE CASCADE
);

/* Link table to associate rows in t_file with those in t_event */
CREATE TABLE t_event_to_file (
	fileID integer NOT NULL,
	eventID integer NOT NULL,
	sequenceNumber integer DEFAULT 0 NOT NULL,
	PRIMARY KEY (fileId, eventId),
	FOREIGN KEY (eventId) REFERENCES t_event (internalId) ON DELETE CASCADE,
	FOREIGN KEY (fileId) REFERENCES t_file (internalId) ON DELETE CASCADE
);

/* Change the terminator, need to do this so we can actually 
   have terminators within the trigger scripts. */
SET TERM ^ ;
CREATE OR ALTER TRIGGER assignEventID FOR t_event 
BEFORE INSERT position 0 
AS begin
  if ((new.internalID is null) or (new.internalID = 0)) then
  begin
    new.internalID = gen_id(gidSequence, 1);
  end
  if (new.eventID is null) then
  begin
    new.eventID = gen_uuid();
  end
end ^
CREATE OR ALTER TRIGGER assignFileID FOR t_file 
BEFORE INSERT position 0 
AS begin
  if ((new.internalID is null) or (new.internalID = 0)) then
  begin
    new.internalID = gen_id(gidSequence, 1);
  end
  if (new.fileID is null) then
  begin
    new.fileID = gen_uuid();
  end
end ^
CREATE OR ALTER TRIGGER assignFileMetaID FOR t_fileMeta 
BEFORE INSERT position 0 
AS begin
  if ((new.internalID is null) or (new.internalID = 0)) then
  begin
    new.internalID = gen_id(gidSequence, 1);
  end
end ^
/* Change the terminator back to the semi-colon again */
SET TERM ; ^






