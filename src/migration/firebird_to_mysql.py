#!../../virtual-env/bin/python
# firebird_to_mysql.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

from contextlib import closing
import os
import math
import fdb
import time
import mod_settings
import mod_hardwareProps
import meteorpi_model as mp
import meteorpi_db

db = meteorpi_db.MeteorDatabase(file_store_path="../../datadir/db_filestore")
hw = mod_hardwareProps.HardwareProps(os.path.join(mod_settings.settings['pythonPath'], "..", "sensorProperties"))


def if3(a, b, c):
    if (a):
        return b
    else:
        return c


# Connect to Firebird DB
con = fdb.connect(
        dsn='localhost:/var/lib/firebird/2.5/data/meteorpi.fdb',
        user='meteorpi',
        password='meteorpi')

# Migrate observatory statuses
with closing(con.trans()) as transaction:
    with closing(transaction.cursor()) as cur:
        cur.execute("""SELECT
internalID, statusID, cameraID, validFrom, softwareVersion, orientationAltitude, orientationAzimuth,
orientationRotation, orientationError, widthOfField, locationLatitude, locationLongitude, locationGPS, locationError,
lens, sensor, instURL, instName
FROM t_cameraStatus;""")
        statuses = cur.fetchall()
        print "Fetched %8d statuses" % len(statuses)

for item in statuses:
    obstory_name = obstory_id = item[2].strip()
    utc = item[3] / 1000.0
    if not db.has_obstory_id(obstory_id):
        db.register_obstory(obstory_id=obstory_id, obstory_name=obstory_name, latitude=item[10], longitude=item[11])
        db.register_obstory_metadata(obstory_name, "instURL", item[16], utc, "migrate")
        db.register_obstory_metadata(obstory_name, "instName", item[17], utc, "migrate")
    db.register_obstory_metadata(obstory_name, "softwareVersion", item[4], utc, "migrate")
    db.register_obstory_metadata(obstory_name, "latitude", item[10], utc, "migrate")
    db.register_obstory_metadata(obstory_name, "longitude", item[11], utc, "migrate")
    db.register_obstory_metadata(obstory_name, "location_source", if3(item[12], "gps", "manual"), utc, "migrate")
    hw.update_sensor(db=db, obstory_name=obstory_name, utc=utc, name=item[15])
    hw.update_lens(db=db, obstory_name=obstory_name, utc=utc, name=item[14])
db.commit()

# Migrate events
event_public_ids = {}
with closing(con.trans()) as transaction:
    with closing(transaction.cursor()) as cur:
        cur.execute("""SELECT
internalID, metaKey, stringValue, dateValue, floatValue, eventID, metaIndex
FROM t_eventMeta;""")
        eventMetas = cur.fetchall()
        print "Fetched %8d event meta items" % len(eventMetas)
        eventMetaDict = {}
        for item in eventMetas:
            if item[5] not in eventMetaDict:
                eventMetaDict[item[5]] = []
            eventMetaDict[item[5]].append(item)

        cur.execute("""SELECT
internalID, eventID, cameraID, eventTime, eventOffset, eventType, statusID
FROM t_event;""")
        events = cur.fetchall()
        print "Fetched %8d events" % len(events)

for item in events:
    obstory_id = item[2].strip()
    utc = item[3] / 1000.0
    meta_list = []
    if item[0] in eventMetaDict:
        for meta in eventMetaDict[item[0]]:
            if meta[2] is not None:
                meta_val = meta[2]
            elif meta[3] is not None:
                meta_val = meta[3] / 1000.0
            else:
                meta_val = meta[4]
            meta_list.append(mp.Meta(meta[1], meta_val))
    obs = db.register_observation(obstory_name=obstory_id,
                                  user_id="migrate",
                                  obs_time=utc,
                                  obs_type="movingObject",
                                  obs_meta=meta_list)
    event_public_ids[item[0]] = obs.obs_id
db.commit()

# Migrate files
with closing(con.trans()) as transaction:
    with closing(transaction.cursor()) as cur:
        cur.execute("""SELECT
internalID, cameraID, fileID, mimeType, fileName, semanticType, fileTime, fileOffset, fileSize, statusID, md5Hex
FROM t_file;""")
        files = cur.fetchall()
        print "Fetched %8d files" % len(files)

        cur.execute("""SELECT
internalID, metaKey, stringValue, dateValue, floatValue, fileID, metaIndex
FROM t_fileMeta;""")
        fileMetas = cur.fetchall()
        print "Fetched %8d file meta items" % len(fileMetas)
        fileMetaDict = {}
        for item in fileMetas:
            if item[5] not in fileMetaDict:
                fileMetaDict[item[5]] = []
            fileMetaDict[item[5]].append(item)

        cur.execute("""SELECT
  fileID, eventID
FROM t_event_to_file;""")
        event_file_links = cur.fetchall()
        print "Fetched %8d event-file-links" % len(event_file_links)
        event_file_dict = {}
        for item in event_file_links:
            event_file_dict[item[0]] = item[1]

created_observations = {}

count = 0
for item in files:
    if (count % 1000) == 0:
        print "[%s] Completed %9d/%9d" % (time.strftime("%b %d %Y %H:%M:%S", time.gmtime(time.time())),
                                          count, len(files))
    count += 1
    obstory_id = item[1].strip()
    utc = item[6] / 1000.0
    utc_floor = math.floor(utc)
    meta_list = []

    # Move file from firebird repository into new repository
    file_path = os.path.join("../../datadir/firebird_files", item[4])
    if not os.path.exists(file_path):
        print "Warning: Could not find file <%s>" % file_path
        open(file_path, "w").write("")
        
    if item[0] in fileMetaDict:
        for meta in fileMetaDict[item[0]]:
            if meta[2] is not None:
                meta_val = meta[2]
            elif meta[3] is not None:
                meta_val = meta[3] / 1000.0
            else:
                meta_val = meta[4]
            meta_list.append(mp.Meta(meta[1], meta_val))
    if item[0] in event_file_dict:
        file_obj = db.register_file(observation_id=event_public_ids[event_file_dict[item[0]]],
                                    user_id="migrate",
                                    file_path=file_path,
                                    file_time=utc,
                                    mime_type=item[3],
                                    semantic_type=item[4],
                                    file_meta=meta_list)
    elif utc_floor in created_observations:
        file_obj = db.register_file(observation_id=created_observations[utc_floor],
                                    user_id="migrate",
                                    file_path=file_path,
                                    file_time=utc,
                                    mime_type=item[3],
                                    semantic_type=item[4],
                                    file_meta=meta_list)
    else:
        if item[3] == "text/plain":
            semantic_type = "logging"
        else:
            semantic_type = "timelapse"
        obs = db.register_observation(obstory_name=obstory_id,
                                      user_id="migrate",
                                      obs_time=utc,
                                      obs_type="timelapse",
                                      obs_meta=meta_list)
        created_observations[utc_floor] = obs.obs_id
        file_obj = db.register_file(observation_id=obs.obs_id,
                                    user_id="migrate",
                                    file_path=file_path,
                                    file_time=utc,
                                    mime_type=item[3],
                                    semantic_type=item[4],
                                    file_meta=meta_list)
    db.commit()
