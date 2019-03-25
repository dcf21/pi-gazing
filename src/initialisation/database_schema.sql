# database_schema.sql

# Schema for database archiving observations

BEGIN;

# Create users tables
CREATE TABLE pigazing_users
(
  userId      INTEGER PRIMARY KEY AUTO_INCREMENT,
  username    VARCHAR(48) UNIQUE NOT NULL,
  name        TEXT,
  job         TEXT,
  password    TEXT,
  email       TEXT,
  joinDate    FLOAT,
  profilePic  TEXT,
  profileText TEXT
);

CREATE TABLE pigazing_user_sessions
(
  sessionId INTEGER PRIMARY KEY AUTO_INCREMENT,
  userId    INTEGER,
  cookie    CHAR(32),
  ip        INTEGER UNSIGNED,
  logIn     REAL,
  lastSeen  REAL,
  logOut    REAL,
  FOREIGN KEY (userId) REFERENCES pigazing_users (userId)
    ON DELETE CASCADE,
  INDEX (cookie)
);

CREATE TABLE pigazing_roles
(
  roleId INTEGER PRIMARY KEY AUTO_INCREMENT,
  name   VARCHAR(128) UNIQUE NOT NULL
);

CREATE TABLE pigazing_user_roles
(
  userId INTEGER NOT NULL,
  roleId INTEGER NOT NULL,
  FOREIGN KEY (userId) REFERENCES pigazing_users (userId)
    ON DELETE CASCADE,
  FOREIGN KEY (roleId) REFERENCES pigazing_roles (roleId)
    ON DELETE CASCADE,
  PRIMARY KEY (userId, roleId)
);

# Create table of sources of data
CREATE TABLE pigazing_sources
(
  sourceId SMALLINT PRIMARY KEY AUTO_INCREMENT,
  abbrev   VARCHAR(32) UNIQUE,
  name     TEXT,
  url      TEXT
);

# Create table of observations

# Table of observatories
CREATE TABLE archive_observatories
(
  uid          INTEGER PRIMARY KEY AUTO_INCREMENT,
  publicId     CHAR(32) UNIQUE NOT NULL,
  userId       VARCHAR(48),
  name         VARCHAR(256),
  location     POINT           NOT NULL,
  locationNull BOOLEAN DEFAULT FALSE,
  INDEX (publicId),
  INDEX (userId),
  INDEX (name),
  FULLTEXT INDEX (name),
  SPATIAL INDEX (location)
);

# Create constellation table
CREATE TABLE pigazing_constellations
(
  constellationId TINYINT PRIMARY KEY AUTO_INCREMENT,
  name            VARCHAR(64) UNIQUE NOT NULL,
  abbrev          VARCHAR(8) UNIQUE  NOT NULL,
  namenospaces    VARCHAR(64) UNIQUE NOT NULL,
  RA              FLOAT,
  Decl            FLOAT,
  area            FLOAT,
  date            TEXT,
  genitiveForm    TEXT,
  FULLTEXT INDEX (name)
);

# Create constellations neighbours table
CREATE TABLE pigazing_constellations_neighbours
(
  uid INTEGER PRIMARY KEY AUTO_INCREMENT,
  a   TINYINT,
  b   TINYINT,
  FOREIGN KEY (a) REFERENCES pigazing_constellations (constellationId),
  FOREIGN KEY (b) REFERENCES pigazing_constellations (constellationId)
);

# Table of types of observation
CREATE TABLE archive_semanticTypes
(
  uid  INTEGER PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(255) NOT NULL UNIQUE
);

# Table of observations
CREATE TABLE archive_observations
(
  uid                      INTEGER PRIMARY KEY AUTO_INCREMENT,
  publicId                 CHAR(32) UNIQUE NOT NULL,
  observatory              INTEGER         NOT NULL,
  userId                   VARCHAR(48),
  obsTime                  REAL            NOT NULL,
  obsType                  INTEGER         NOT NULL,
  creationTime             REAL            NOT NULL,
  published                BOOLEAN         NOT NULL,
  moderated                BOOLEAN         NOT NULL,
  featured                 BOOLEAN         NOT NULL,
  position                 POINT           NOT NULL,
  skyArea                  MULTIPOLYGON    NOT NULL,
  fieldWidth               REAL,
  fieldHeight              REAL,
  positionAngle            REAL,
  centralConstellation     TINYINT,
  astrometrySource         SMALLINT,
  astrometryProcessed      REAL,
  astrometryProcessingTime REAL,
  altAz                    POINT           NOT NULL,
  altAzPositionAngle       REAL,

  derived_published_year   SMALLINT        NOT NULL,
  derived_published_month  TINYINT         NOT NULL,
  derived_published_day    TINYINT         NOT NULL,

  derived_observed_year    SMALLINT        NOT NULL,
  derived_observed_month   TINYINT         NOT NULL,
  derived_observed_day     TINYINT         NOT NULL,

  FOREIGN KEY (observatory) REFERENCES archive_observatories (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (obsType) REFERENCES archive_semanticTypes (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (centralConstellation) REFERENCES pigazing_constellations (constellationId)
    ON DELETE CASCADE,
  FOREIGN KEY (astrometrySource) REFERENCES pigazing_sources (sourceId)
    ON DELETE CASCADE,
  INDEX (obsTime),
  INDEX (creationTime),
  INDEX (publicId),
  INDEX (astrometryProcessed),
  SPATIAL INDEX (position),
  SPATIAL INDEX (skyArea),
  INDEX (derived_observed_year, derived_observed_month, derived_observed_day),
  INDEX (derived_published_year, derived_published_month, derived_published_day)
);

# Groups of observations
CREATE TABLE archive_obs_groups
(
  uid          INTEGER PRIMARY KEY AUTO_INCREMENT,
  publicId     CHAR(32) UNIQUE NOT NULL,
  title        TEXT,
  semanticType INTEGER,
  time         REAL,
  setAtTime    REAL, /* time that metadata was computed */
  setByUser    VARCHAR(48),
  FOREIGN KEY (semanticType) REFERENCES archive_semanticTypes (uid),
  INDEX (time),
  INDEX (setAtTime),
  INDEX (setByUser)
);

CREATE TABLE archive_obs_group_members
(
  uid              INTEGER PRIMARY KEY AUTO_INCREMENT,
  groupId          INTEGER NOT NULL,
  childObservation INTEGER,
  childGroup       INTEGER,
  FOREIGN KEY (groupId) REFERENCES archive_obs_groups (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (childObservation) REFERENCES archive_observations (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (childGroup) REFERENCES archive_obs_groups (uid)
    ON DELETE CASCADE
);

# Links to files in whatever external store we use
CREATE TABLE archive_files
(
  uid             INTEGER PRIMARY KEY AUTO_INCREMENT,
  observationId   INTEGER         NOT NULL,
  mimeType        VARCHAR(100)    NOT NULL,
  fileName        VARCHAR(255)    NOT NULL,
  semanticType    INTEGER         NOT NULL,
  fileTime        REAL            NOT NULL,
  fileSize        INTEGER         NOT NULL,
  repositoryFname CHAR(32) UNIQUE NOT NULL,
  fileMD5         CHAR(32)        NOT NULL, /* MD5 hash of file contents */
  primaryImage    BOOLEAN         NOT NULL,
  FOREIGN KEY (semanticType) REFERENCES archive_semanticTypes (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (observationId) REFERENCES archive_observations (uid)
    ON DELETE CASCADE,
  INDEX (fileTime),
  INDEX (repositoryFname)
);

# Metadata pertaining to observations, observatories, or groups of observations
CREATE TABLE archive_metadataFields
(
  uid     INTEGER PRIMARY KEY AUTO_INCREMENT,
  metaKey VARCHAR(255) NOT NULL UNIQUE,
  INDEX (metaKey)
);

CREATE TABLE archive_metadata
(
  uid           INTEGER PRIMARY KEY AUTO_INCREMENT,
  publicId      CHAR(32) UNIQUE NOT NULL,
  fieldId       INTEGER,
  time          REAL, /* time that metadata is relevant for */
  setAtTime     REAL, /* time that metadata was computed */
  setByUser     VARCHAR(48),
  stringValue   TEXT,
  floatValue    REAL,
  fileId        INTEGER,
  observationId INTEGER,
  observatory   INTEGER,
  groupId       INTEGER,
  FOREIGN KEY (fileId) REFERENCES archive_files (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (observatory) REFERENCES archive_observatories (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (observationId) REFERENCES archive_observations (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (groupId) REFERENCES archive_obs_groups (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (fieldId) REFERENCES archive_metadataFields (uid)
    ON DELETE CASCADE,
  INDEX (setAtTime),
  INDEX (publicId),
  INDEX (fieldId, observationId),
  INDEX (fieldId, fileId),
  INDEX (fieldId, observatory)
);

# Configuration used to export observations to an external server
CREATE TABLE archive_exportConfig
(
  uid            INTEGER PRIMARY KEY AUTO_INCREMENT,
  exportConfigId CHAR(32) UNIQUE NOT NULL,
  exportType     VARCHAR(16)     NOT NULL,
  searchString   VARCHAR(2048)   NOT NULL,
  targetURL      VARCHAR(255)    NOT NULL,
  targetUser     VARCHAR(255)    NOT NULL,
  targetPassword VARCHAR(255)    NOT NULL,
  exportName     VARCHAR(255)    NOT NULL,
  description    VARCHAR(2048)   NOT NULL,
  active         BOOLEAN         NOT NULL,
  INDEX (exportConfigId)
);

CREATE TABLE archive_observationExport
(
  uid           INTEGER PRIMARY KEY AUTO_INCREMENT,
  observationId INTEGER NOT NULL,
  exportConfig  INTEGER NOT NULL,
  exportState   INTEGER NOT NULL, /* 0 for complete, non-zero for active */
  FOREIGN KEY (observationId) REFERENCES archive_observations (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (exportConfig) REFERENCES archive_exportConfig (uid)
    ON DELETE CASCADE
);

CREATE TABLE archive_observationImport
(
  uid           INTEGER PRIMARY KEY AUTO_INCREMENT,
  observationId INTEGER NOT NULL,
  importUser    INTEGER NOT NULL,
  importTime    REAL    NOT NULL,
  FOREIGN KEY (observationId) REFERENCES archive_observations (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (importUser) REFERENCES pigazing_users (userId)
    ON DELETE CASCADE
);

CREATE TABLE archive_fileExport
(
  uid          INTEGER PRIMARY KEY AUTO_INCREMENT,
  fileId       INTEGER NOT NULL,
  exportConfig INTEGER NOT NULL,
  exportState  INTEGER NOT NULL, /* 0 for complete, non-zero for active */
  FOREIGN KEY (fileId) REFERENCES archive_files (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (exportConfig) REFERENCES archive_exportConfig (uid)
    ON DELETE CASCADE
);


CREATE TABLE archive_fileImport
(
  uid        INTEGER PRIMARY KEY AUTO_INCREMENT,
  fileId     INTEGER NOT NULL,
  importUser INTEGER NOT NULL,
  importTime REAL    NOT NULL,
  FOREIGN KEY (fileId) REFERENCES archive_files (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (importUser) REFERENCES pigazing_users (userId)
    ON DELETE CASCADE
);

CREATE TABLE archive_metadataExport
(
  uid          INTEGER PRIMARY KEY AUTO_INCREMENT,
  metadataId   INTEGER NOT NULL,
  exportConfig INTEGER NOT NULL, /* URL of the target import API */
  exportState  INTEGER NOT NULL, /* 0 for complete, non-zero for active */
  FOREIGN KEY (metadataId) REFERENCES archive_metadata (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (exportConfig) REFERENCES archive_exportConfig (uid)
    ON DELETE CASCADE
);

CREATE TABLE archive_metadataImport
(
  uid        INTEGER PRIMARY KEY AUTO_INCREMENT,
  metadataId INTEGER NOT NULL,
  importUser INTEGER NOT NULL,
  importTime REAL    NOT NULL,
  FOREIGN KEY (metadataId) REFERENCES archive_metadata (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (importUser) REFERENCES pigazing_users (userId)
    ON DELETE CASCADE
);

# Create tables of data about observations
CREATE TABLE archive_equipment_type
(
  equipTypeId SMALLINT PRIMARY KEY AUTO_INCREMENT,
  name        VARCHAR(255) UNIQUE NOT NULL
);

CREATE TABLE archive_equipment_item
(
  equipId     INTEGER PRIMARY KEY AUTO_INCREMENT,
  equipTypeId SMALLINT NOT NULL,
  FOREIGN KEY (equipTypeId) REFERENCES archive_equipment_type (equipTypeId)
    ON DELETE CASCADE
);

CREATE TABLE archive_equipment_names
(
  name        VARCHAR(255) UNIQUE NOT NULL PRIMARY KEY,
  primaryName BOOLEAN,
  equipId     INTEGER             NOT NULL,
  INDEX (name),
  FULLTEXT INDEX (name),
  FOREIGN KEY (equipId) REFERENCES archive_equipment_item (equipId)
    ON DELETE CASCADE
);

CREATE TABLE archive_obs_equipment
(
  obsId       INTEGER NOT NULL,
  equipId     INTEGER NOT NULL,
  description TEXT,
  FOREIGN KEY (obsId) REFERENCES archive_observations (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (equipId) REFERENCES archive_equipment_item (equipId)
    ON DELETE CASCADE
);

CREATE TABLE archive_obs_likes
(
  userId        INTEGER NOT NULL,
  observationId INTEGER NOT NULL,
  PRIMARY KEY (userId, observationId),
  FOREIGN KEY (userId) REFERENCES pigazing_users (userId)
    ON DELETE CASCADE,
  FOREIGN KEY (observationId) REFERENCES archive_observations (uid)
    ON DELETE CASCADE
);

# Table of high water marks
CREATE TABLE pigazing_highWaterMarkTypes
(
  uid     INTEGER PRIMARY KEY AUTO_INCREMENT,
  metaKey VARCHAR(255) UNIQUE NOT NULL
);

CREATE TABLE pigazing_highWaterMarks
(
  observatoryId INTEGER,
  markType      INTEGER,
  time          REAL,
  FOREIGN KEY (observatoryId) REFERENCES archive_observatories (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (markType) REFERENCES pigazing_highWaterMarkTypes (uid)
    ON DELETE CASCADE
);

COMMIT;
