# archive-schema.sql

# Schema for database archiving observations

BEGIN;

/* Table of users */
CREATE TABLE archive_users (
  uid      INTEGER PRIMARY KEY AUTO_INCREMENT,
  userID   VARCHAR(16)       NOT NULL,
  pwHash   VARCHAR(87)       NOT NULL,
  roleMask INTEGER DEFAULT 0 NOT NULL
);

CREATE TABLE archive_user_sessions (
  sessionId INTEGER PRIMARY KEY AUTO_INCREMENT,
  userId    INTEGER,
  cookie    CHAR(32),
  ip        INTEGER UNSIGNED,
  logIn     REAL,
  lastSeen  REAL,
  logOut    REAL,
  FOREIGN KEY (userId) REFERENCES archive_users (uid) ON DELETE CASCADE,
  INDEX (cookie)
);

CREATE TABLE archive_roles (
  uid INTEGER PRIMARY KEY AUTO_INCREMENT,
  name TEXT
);

CREATE TABLE archive_user_roles (
  userId INTEGER,
  roleId INTEGER,
  FOREIGN KEY (userId) REFERENCES archive_users (uid) ON DELETE CASCADE,
  FOREIGN KEY (roleId) REFERENCES archive_roles (uid) ON DELETE CASCADE,
  PRIMARY KEY (userId, roleId)
);

/* Table of cameras */
CREATE TABLE archive_observatories (
  uid      INTEGER PRIMARY KEY AUTO_INCREMENT,
  publicId VARCHAR(16) NOT NULL,
  name     TEXT,
  INDEX(publicId)
);

/* Table of high water marks */
CREATE TABLE archive_highWaterMarkTypes (
  uid     INTEGER PRIMARY KEY AUTO_INCREMENT,
  metaKey TEXT
);

CREATE TABLE archive_highWaterMarks (
  observatoryId INTEGER,
  markType      VARCHAR(16),
  time          REAL,
  FOREIGN KEY (observatoryId) REFERENCES archive_observatories (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (markType) REFERENCES archive_highWaterMarkTypes (uid)
    ON DELETE CASCADE
);

/* Table of types of observation */
CREATE TABLE archive_semanticTypes (
  uid     INTEGER PRIMARY KEY AUTO_INCREMENT,
  metaKey VARCHAR(255) NOT NULL
);

/* Table of observations */
CREATE TABLE archive_observations (
  uid         INTEGER PRIMARY KEY AUTO_INCREMENT,
  publicId    VARCHAR(16) NOT NULL,
  observatory INTEGER     NOT NULL,
  userId      VARCHAR(16),
  eventTime   REAL        NOT NULL,
  eventType   INTEGER     NOT NULL,
  FOREIGN KEY (observatory) REFERENCES archive_observatories (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (eventType) REFERENCES archive_semanticTypes (uid)
    ON DELETE CASCADE,
  INDEX(publicId)
);

/* Number of likes each observation has */
CREATE TABLE archive_obs_likes (
  userId       INTEGER,
  observationId INTEGER,
  PRIMARY KEY (userId, observationId),
  FOREIGN KEY (userId) REFERENCES archive_users (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (observationId) REFERENCES archive_observations (uid)
    ON DELETE CASCADE
);

/* Metadata pertaining to observations or observatories */
CREATE TABLE archive_metadataFields (
  uid     INTEGER PRIMARY KEY AUTO_INCREMENT,
  metaKey VARCHAR(255) NOT NULL
);

CREATE TABLE archive_metadata (
  uid           INTEGER PRIMARY KEY AUTO_INCREMENT,
  fieldId       INTEGER,
  time          REAL, /* time that metadata is relavant for */
  setAtTime     REAL, /* time that metadata was computed */
  setByUser     VARCHAR(16),
  stringValue   VARCHAR(255),
  floatValue    REAL,
  observationID INTEGER,
  observatory   INTEGER,
  FOREIGN KEY (setByUser) REFERENCES archive_users (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (observatory) REFERENCES archive_observatories (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (observationId) REFERENCES archive_observations (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (fieldId) REFERENCES archive_metadataFields (uid)
    ON DELETE CASCADE
);

/* Marked out regions of images */
CREATE TABLE archive_imageRegions (
  uid        INTEGER PRIMARY KEY AUTO_INCREMENT,
  metadataId INTEGER           NOT NULL,
  region     INTEGER           NOT NULL,
  pointOrder INTEGER DEFAULT 0 NOT NULL,
  x          INTEGER           NOT NULL,
  y          INTEGER           NOT NULL,
  FOREIGN KEY (metadataId) REFERENCES archive_metadata (uid)
    ON DELETE CASCADE
);

/* Links to files in whatever external store we use */
CREATE TABLE archive_file (
  uid             INTEGER PRIMARY KEY AUTO_INCREMENT,
  observationId   INTEGER      NOT NULL,
  mimeType        VARCHAR(100) NOT NULL,
  fileName        VARCHAR(255),
  semanticType    INTEGER      NOT NULL,
  fileTime        REAL         NOT NULL,
  fileSize        INTEGER      NOT NULL,
  repositoryFname CHAR(32)     NOT NULL,
  INDEX(repositoryFname)
);

/* Configuration used to export observations to an external server */
CREATE TABLE archive_exportConfig (
  uid            INTEGER PRIMARY KEY AUTO_INCREMENT,
  exportConfigID CHAR(16)      NOT NULL,
  exportType     VARCHAR(10)   NOT NULL,
  searchString   VARCHAR(2048) NOT NULL,
  targetURL      VARCHAR(255)  NOT NULL,
  targetUser     VARCHAR(255)  NOT NULL,
  targetPassword VARCHAR(255)  NOT NULL,
  exportName     VARCHAR(255)  NOT NULL,
  description    VARCHAR(2048) NOT NULL,
  active         BOOLEAN       NOT NULL
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
  fileID       INTEGER NOT NULL,
  exportConfig INTEGER NOT NULL, /* URL of the target import API */
  exportTime   REAL    NOT NULL,
  exportState  INTEGER NOT NULL, /* 0 for complete, non-zero for active */
  FOREIGN KEY (fileID) REFERENCES archive_file (uid)
    ON DELETE CASCADE,
  FOREIGN KEY (exportConfig) REFERENCES archive_exportConfig (uid)
    ON DELETE CASCADE
);

CREATE TABLE archive_fileImport (
  uid        INTEGER PRIMARY KEY AUTO_INCREMENT,
  fileID     INTEGER      NOT NULL,
  importUser VARCHAR(255) NOT NULL, /* User ID of the user performing the import */
  importTime REAL         NOT NULL,
  FOREIGN KEY (fileID) REFERENCES archive_file (uid)
    ON DELETE CASCADE
);

COMMIT;
