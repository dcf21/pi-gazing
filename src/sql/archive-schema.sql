# archive-schema.sql

# Schema for database archiving observations

BEGIN;

/* Table of users */
CREATE TABLE archive_users (
  uid    INTEGER PRIMARY KEY AUTO_INCREMENT,
  userId VARCHAR(16) NOT NULL,
  pwHash VARCHAR(87) NOT NULL
);

CREATE TABLE archive_user_sessions (
  sessionId INTEGER PRIMARY KEY AUTO_INCREMENT,
  userId    INTEGER,
  cookie    CHAR(32),
  ip        INTEGER UNSIGNED,
  logIn     REAL,
  lastSeen  REAL,
  logOut    REAL,
  FOREIGN KEY (userId) REFERENCES archive_users (uid)
    ON DELETE CASCADE,
  INDEX (cookie)
);

CREATE TABLE archive_roles (
  uid  INTEGER PRIMARY KEY AUTO_INCREMENT,
  name TEXT
);

CREATE TABLE archive_user_roles (
  userId INTEGER,
  roleId INTEGER,
  FOREIGN KEY (userId) REFERENCES archive_users (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (roleId) REFERENCES archive_roles (uid)
    ON DELETE CASCADE,
  PRIMARY KEY (userId, roleId)
);

/* Table of observatories */
CREATE TABLE archive_observatories (
  uid       INTEGER PRIMARY KEY AUTO_INCREMENT,
  publicId  CHAR(32) NOT NULL,
  name      TEXT,
  latitude  REAL,
  longitude REAL,
  INDEX (publicId)
);

/* Table of high water marks */
CREATE TABLE archive_highWaterMarkTypes (
  uid     INTEGER PRIMARY KEY AUTO_INCREMENT,
  metaKey TEXT
);

CREATE TABLE archive_highWaterMarks (
  observatoryId INTEGER,
  markType      INTEGER,
  time          REAL,
  FOREIGN KEY (observatoryId) REFERENCES archive_observatories (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (markType) REFERENCES archive_highWaterMarkTypes (uid)
    ON DELETE CASCADE
);

/* Table of types of observation */
CREATE TABLE archive_semanticTypes (
  uid  INTEGER PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(255) NOT NULL UNIQUE
);

/* Table of observations */
CREATE TABLE archive_observations (
  uid         INTEGER PRIMARY KEY AUTO_INCREMENT,
  publicId    CHAR(32) NOT NULL,
  observatory INTEGER  NOT NULL,
  userId      VARCHAR(16),
  obsTime     REAL     NOT NULL,
  obsType     INTEGER  NOT NULL,
  FOREIGN KEY (observatory) REFERENCES archive_observatories (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (obsType) REFERENCES archive_semanticTypes (uid)
    ON DELETE CASCADE,
  INDEX (obsTime),
  INDEX (publicId)
);

/* Number of likes each observation has */
CREATE TABLE archive_obs_likes (
  userId        INTEGER,
  observationId INTEGER,
  PRIMARY KEY (userId, observationId),
  FOREIGN KEY (userId) REFERENCES archive_users (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (observationId) REFERENCES archive_observations (uid)
    ON DELETE CASCADE
);

/* Groups of observations */
CREATE TABLE archive_obs_groups (
  uid       INTEGER PRIMARY KEY AUTO_INCREMENT,
  publicId  CHAR(32) NOT NULL,
  title     TEXT,
  semanticType INTEGER,
  time      REAL,
  setAtTime REAL, /* time that metadata was computed */
  setByUser VARCHAR(16),
  FOREIGN KEY (semanticType) REFERENCES archive_semanticTypes (uid),
  INDEX (time),
  INDEX (setAtTime)
);

CREATE TABLE archive_obs_group_members (
  groupId       INTEGER,
  observationId INTEGER,
  PRIMARY KEY (groupId, observationId),
  FOREIGN KEY (groupId) REFERENCES archive_obs_groups (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (observationId) REFERENCES archive_observations (uid)
    ON DELETE CASCADE
);

/* Links to files in whatever external store we use */
CREATE TABLE archive_files (
  uid             INTEGER PRIMARY KEY AUTO_INCREMENT,
  observationId   INTEGER      NOT NULL,
  mimeType        VARCHAR(100) NOT NULL,
  fileName        VARCHAR(255) NOT NULL,
  semanticType    INTEGER      NOT NULL,
  fileTime        REAL         NOT NULL,
  fileSize        INTEGER      NOT NULL,
  repositoryFname CHAR(32)     NOT NULL,
  fileMD5         CHAR(32)     NOT NULL, /* MD5 hash of file contents */
  FOREIGN KEY (semanticType) REFERENCES archive_semanticTypes (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (observationId) REFERENCES archive_observations (uid)
    ON DELETE CASCADE,
  INDEX (fileTime),
  INDEX (repositoryFname)
);

/* Metadata pertaining to observations, observatories, or groups of observations */
CREATE TABLE archive_metadataFields (
  uid     INTEGER PRIMARY KEY AUTO_INCREMENT,
  metaKey VARCHAR(255) NOT NULL UNIQUE,
  INDEX (metaKey)
);

CREATE TABLE archive_metadata (
  uid           INTEGER PRIMARY KEY AUTO_INCREMENT,
  publicId      CHAR(32) NOT NULL,
  fieldId       INTEGER,
  time          REAL, /* time that metadata is relevant for */
  setAtTime     REAL, /* time that metadata was computed */
  setByUser     VARCHAR(16),
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
  INDEX (publicId)
);

/* Configuration used to export observations to an external server */
CREATE TABLE archive_exportConfig (
  uid            INTEGER PRIMARY KEY AUTO_INCREMENT,
  exportConfigId CHAR(32)      NOT NULL,
  exportType     VARCHAR(16)   NOT NULL,
  searchString   VARCHAR(2048) NOT NULL,
  targetURL      VARCHAR(255)  NOT NULL,
  targetUser     VARCHAR(255)  NOT NULL,
  targetPassword VARCHAR(255)  NOT NULL,
  exportName     VARCHAR(255)  NOT NULL,
  description    VARCHAR(2048) NOT NULL,
  active         BOOLEAN       NOT NULL,
  INDEX (exportConfigId)
);

CREATE TABLE archive_observationExport (
  uid           INTEGER PRIMARY KEY AUTO_INCREMENT,
  observationId INTEGER NOT NULL,
  exportConfig  INTEGER NOT NULL,
  exportState   INTEGER NOT NULL, /* 0 for complete, non-zero for active */
  FOREIGN KEY (observationId) REFERENCES archive_observations (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (exportConfig) REFERENCES archive_exportConfig (uid)
    ON DELETE CASCADE
);

CREATE TABLE archive_observationImport (
  uid           INTEGER PRIMARY KEY AUTO_INCREMENT,
  observationId INTEGER NOT NULL,
  importUser    INTEGER NOT NULL,
  importTime    REAL    NOT NULL,
  FOREIGN KEY (observationId) REFERENCES archive_observations (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (importUser) REFERENCES archive_users (uid)
    ON DELETE CASCADE
);

CREATE TABLE archive_fileExport (
  uid          INTEGER PRIMARY KEY AUTO_INCREMENT,
  fileId       INTEGER NOT NULL,
  exportConfig INTEGER NOT NULL,
  exportState  INTEGER NOT NULL, /* 0 for complete, non-zero for active */
  FOREIGN KEY (fileId) REFERENCES archive_files (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (exportConfig) REFERENCES archive_exportConfig (uid)
    ON DELETE CASCADE
);


CREATE TABLE archive_fileImport (
  uid        INTEGER PRIMARY KEY AUTO_INCREMENT,
  fileId     INTEGER NOT NULL,
  importUser INTEGER NOT NULL,
  importTime REAL    NOT NULL,
  FOREIGN KEY (fileId) REFERENCES archive_files (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (importUser) REFERENCES archive_users (uid)
    ON DELETE CASCADE
);

CREATE TABLE archive_metadataExport (
  uid          INTEGER PRIMARY KEY AUTO_INCREMENT,
  metadataId   INTEGER NOT NULL,
  exportConfig INTEGER NOT NULL, /* URL of the target import API */
  exportState  INTEGER NOT NULL, /* 0 for complete, non-zero for active */
  FOREIGN KEY (metadataId) REFERENCES archive_metadata (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (exportConfig) REFERENCES archive_exportConfig (uid)
    ON DELETE CASCADE
);

CREATE TABLE archive_metadataImport (
  uid        INTEGER PRIMARY KEY AUTO_INCREMENT,
  metadataId INTEGER      NOT NULL,
  importUser VARCHAR(255) NOT NULL, /* User ID of the user performing the import */
  importTime REAL         NOT NULL,
  FOREIGN KEY (metadataId) REFERENCES archive_metadata (uid)
    ON DELETE CASCADE
);

COMMIT;
