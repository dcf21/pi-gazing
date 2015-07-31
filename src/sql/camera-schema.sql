SET SQL DIALECT 3;
SET NAMES UNICODE_FSS;

/* To run this script you need a clean database set up at
 * /var/lib/firebird/2.5/data/meteorpi.fdb, and be connected
 * as a user with write access to this database.
 * See https://github.com/camsci/meteor-pi/wiki/Camera-database-configuration
 */
CONNECT 'localhost:/var/lib/firebird/2.5/data/DATABASENAME.fdb';

CREATE DOMAIN BOOLEAN AS SMALLINT CHECK (value IS NULL OR value IN (0, 1));

/* Sequence used to allocate internal IDs */
CREATE SEQUENCE gidSequence;

/* User table */

CREATE TABLE t_user (
  userID   VARCHAR(40)       NOT NULL,
  pwHash   VARCHAR(87)       NOT NULL,
  roleMask INTEGER DEFAULT 0 NOT NULL,
  PRIMARY KEY (userID)
);

/* Camera status tables */

CREATE TABLE t_highWaterMark (
  cameraID CHAR(64)  NOT NULL,
  mark BIGINT NOT NULL /* Time since epoch in milliseconds */
);

CREATE TABLE t_cameraStatus (
  internalID          INTEGER           NOT NULL,
  statusID            CHAR(16) CHARACTER SET OCTETS NOT NULL, /* Always use literal byte values */
  cameraID            CHAR(64)          NOT NULL,
  validFrom BIGINT NOT NULL, /* Time since epoch in milliseconds */
  softwareVersion     INTEGER DEFAULT 0 NOT NULL,
  orientationAltitude FLOAT             NOT NULL,
  orientationAzimuth  FLOAT             NOT NULL,
  orientationRotation FLOAT             NOT NULL,
  orientationError    FLOAT             NOT NULL,
  widthOfField        FLOAT             NOT NULL,
  locationLatitude    FLOAT             NOT NULL,
  locationLongitude   FLOAT             NOT NULL,
  locationGPS         BOOLEAN DEFAULT 0 NOT NULL,
  locationError       FLOAT             NOT NULL,
  lens                VARCHAR(40)       NOT NULL,
  sensor              VARCHAR(40)       NOT NULL,
  instURL             VARCHAR(255),
  instName            VARCHAR(255),
  PRIMARY KEY (internalID)
);

CREATE TABLE t_visibleRegions (
  cameraStatusID INTEGER           NOT NULL,
  region         INTEGER           NOT NULL,
  pointOrder     INTEGER DEFAULT 0 NOT NULL,
  x              INTEGER           NOT NULL,
  y              INTEGER           NOT NULL,
  FOREIGN KEY (cameraStatusId) REFERENCES t_cameraStatus (internalId) ON DELETE CASCADE,
  PRIMARY KEY (cameraStatusId, region, pointOrder)
);

/* A single observed event from a particular camera */
CREATE TABLE t_event (
  internalID  INTEGER      NOT NULL,
  eventID     CHAR(16) CHARACTER SET OCTETS NOT NULL, /* Always use literal byte values */
  cameraID    CHAR(64)     NOT NULL,
  eventTime BIGINT NOT NULL, /* Time since epoch in milliseconds */
  eventOffset INTEGER      NOT NULL,
  eventType   VARCHAR(255) NOT NULL,
  statusID    INTEGER      NOT NULL,
  FOREIGN KEY (statusID) REFERENCES t_cameraStatus (internalID) ON DELETE CASCADE,
  PRIMARY KEY (internalID)
);

/* Rows of metadata pertaining to a single event per row */
CREATE TABLE t_eventMeta (
  internalID  INTEGER           NOT NULL,
  metaKey     VARCHAR(255)      NOT NULL,
  stringValue VARCHAR(255),
  dateValue BIGINT, /* Time since epoch in milliseconds */
  floatValue  FLOAT,
  eventID     INTEGER           NOT NULL,
  metaIndex   INTEGER DEFAULT 0 NOT NULL,
  PRIMARY KEY (internalID),
  FOREIGN KEY (eventID) REFERENCES t_event (internalID) ON DELETE CASCADE
);

/* Links to files in whatever external store we use */
CREATE TABLE t_file (
  internalID   INTEGER                           NOT NULL,
  cameraID     CHAR(64)                          NOT NULL,
  fileID       CHAR(16) CHARACTER SET OCTETS NOT NULL, /* Always use literal byte values */
  mimeType     VARCHAR(100) DEFAULT 'text/plain' NOT NULL,
  fileName     VARCHAR(255),
  semanticType VARCHAR(255)                      NOT NULL,
  fileTime BIGINT NOT NULL, /* Time since epoch in milliseconds */
  fileOffset   INTEGER                           NOT NULL,
  fileSize     INTEGER                           NOT NULL,
  statusID     INTEGER                           NOT NULL,
  md5Hex       CHAR(32)                          NOT NULL,
  FOREIGN KEY (statusID) REFERENCES t_cameraStatus (internalID) ON DELETE CASCADE,
  PRIMARY KEY (internalId)
);

/* Rows of metadata pertaining to a single file per row */
CREATE TABLE t_fileMeta (
  internalID INTEGER           NOT NULL,
  metaKey    VARCHAR(255)      NOT NULL,
  stringValue VARCHAR(255),
  dateValue BIGINT, /* Time since epoch in milliseconds */
  floatValue  FLOAT,
  fileID     INTEGER           NOT NULL,
  metaIndex  INTEGER DEFAULT 0 NOT NULL,
  PRIMARY KEY (internalID),
  FOREIGN KEY (fileID) REFERENCES t_file (internalID) ON DELETE CASCADE
);

/* Link table to associate rows in t_file with those in t_event */
CREATE TABLE t_event_to_file (
  fileID         INTEGER           NOT NULL,
  eventID        INTEGER           NOT NULL,
  sequenceNumber INTEGER DEFAULT 0 NOT NULL,
  PRIMARY KEY (fileId, eventId),
  FOREIGN KEY (eventId) REFERENCES t_event (internalId) ON DELETE CASCADE,
  FOREIGN KEY (fileId) REFERENCES t_file (internalId) ON DELETE CASCADE
);

CREATE TABLE t_exportConfig (
  internalID     INTEGER       NOT NULL,
  exportConfigID CHAR(16)      CHARACTER SET OCTETS NOT NULL,
  exportType     VARCHAR(10)   NOT NULL,
  searchString   VARCHAR(2048) NOT NULL,
  targetURL      VARCHAR(255)  NOT NULL,
  targetUser     VARCHAR(255)  NOT NULL,
  targetPassword VARCHAR(255)  NOT NULL,
  exportName     VARCHAR(255)  NOT NULL,
  description    VARCHAR(2048) NOT NULL,
  active         BOOLEAN       NOT NULL,
  PRIMARY KEY (internalID)
);

CREATE TABLE t_eventExport (
  eventID        INTEGER NOT NULL,
  exportConfig   INTEGER NOT NULL, /* URL of the target import API */
  exportTime     BIGINT  NOT NULL, /* Time since epoch in milliseconds */
  exportState    INTEGER NOT NULL, /* 0 for complete, non-zero for active */
  FOREIGN KEY (eventID) REFERENCES t_event (internalId) ON DELETE CASCADE,
  FOREIGN KEY (exportConfig) REFERENCES t_exportConfig (internalID) ON DELETE CASCADE
);

CREATE TABLE t_eventImport (
  eventID        INTEGER      NOT NULL,
  importUser     VARCHAR(255) NOT NULL, /* User ID of the user performing the import */
  importTime     BIGINT       NOT NULL, /* Time since epoch in milliseconds */
  FOREIGN KEY (eventID) REFERENCES t_event (internalID) ON DELETE CASCADE
);

CREATE TABLE t_fileExport (
  fileID         INTEGER NOT NULL,
  exportConfig   INTEGER NOT NULL, /* URL of the target import API */
  exportTime     BIGINT  NOT NULL, /* Time since epoch in milliseconds */
  exportState    INTEGER NOT NULL, /* 0 for complete, non-zero for active */
  FOREIGN KEY (fileID) REFERENCES t_file (internalId) ON DELETE CASCADE,
  FOREIGN KEY (exportConfig) REFERENCES t_exportConfig (internalID) ON DELETE CASCADE
);

CREATE TABLE t_fileImport (
  fileID         INTEGER      NOT NULL,
  importUser     VARCHAR(255) NOT NULL, /* User ID of the user performing the import */
  importTime     BIGINT       NOT NULL, /* Time since epoch in milliseconds */
  FOREIGN KEY (fileID) REFERENCES t_file (internalID) ON DELETE CASCADE
);

/* Change the terminator, need to do this so we can actually 
   have terminators within the trigger scripts. */
SET TERM ^;
CREATE OR ALTER TRIGGER assignExportConfigID FOR t_exportConfig
BEFORE INSERT POSITION 0
AS BEGIN
IF ((new.internalID IS NULL) OR (new.internalID = 0)) THEN
BEGIN
new.internalID = gen_id(gidSequence, 1);
END
IF (new.exportConfigID IS NULL) THEN
BEGIN
new.exportConfigID = gen_uuid();
END
END ^
CREATE OR ALTER TRIGGER assignEventID FOR t_event
BEFORE INSERT POSITION 0
AS BEGIN
IF ((new.internalID IS NULL) OR (new.internalID = 0)) THEN
BEGIN
new.internalID = gen_id(gidSequence, 1);
END
IF (new.eventID IS NULL) THEN
BEGIN
new.eventID = gen_uuid();
END
END ^
CREATE OR ALTER TRIGGER assignFileID FOR t_file
BEFORE INSERT POSITION 0
AS BEGIN
IF ((new.internalID IS NULL) OR (new.internalID = 0)) THEN
BEGIN
new.internalID = gen_id(gidSequence, 1);
END
IF (new.fileID IS NULL) THEN
BEGIN
new.fileID = gen_uuid();
END
END ^
CREATE OR ALTER TRIGGER assignStatusID FOR t_cameraStatus
BEFORE INSERT POSITION 0
AS BEGIN
IF ((new.internalID IS NULL) OR (new.internalID = 0)) THEN
BEGIN
new.internalID = gen_id(gidSequence, 1);
END
IF (new.statusID IS NULL) THEN
BEGIN
new.statusID = gen_uuid();
END
END ^
CREATE OR ALTER TRIGGER assignFileMetaID FOR t_fileMeta
BEFORE INSERT POSITION 0
AS BEGIN
IF ((new.internalID IS NULL) OR (new.internalID = 0)) THEN
BEGIN
new.internalID = gen_id(gidSequence, 1);
END
END ^
CREATE OR ALTER TRIGGER assignEventMetaID FOR t_eventMeta
BEFORE INSERT POSITION 0
AS BEGIN
IF ((new.internalID IS NULL) OR (new.internalID = 0)) THEN
BEGIN
new.internalID = gen_id(gidSequence, 1);
END
END ^
/* Change the terminator back to the semi-colon again */
SET TERM ;^


