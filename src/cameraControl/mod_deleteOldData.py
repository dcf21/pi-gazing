# mod_deleteOldData.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import uuid
import meteorpi_db
import meteorpi_model as mp
from mod_settings import *
from mod_time import *
from contextlib import closing


def delete_old_data(cameraId, utcMin, utcMax):
    db_handle = meteorpi_db.MeteorDatabase(DBPATH, DBFILESTORE)

    search = mp.FileRecordSearch(camera_ids=[cameraId], exclude_events=False, before=UTC2datetime(utcMax),
                                 after=UTC2datetime(utcMin), limit=1000000)
    files = db_handle.search_files(search)
    files = [i for i in files['files']]
    files.sort(key=lambda x: x.file_time)

    search = mp.EventSearch(camera_ids=[cameraId], before=UTC2datetime(utcMax), after=UTC2datetime(utcMin),
                            limit=1000000)
    triggers = db_handle.search_events(search)
    triggers = triggers['events']
    triggers.sort(key=lambda x: x.event_time)

    with closing(db_handle.con.trans()) as transaction:
        with closing(db_handle.con.cursor()) as read_cursor, closing(transaction.cursor()) as update_cursor:
            read_cursor.execute(
                'SELECT fileID AS file_id FROM t_file '
                'WHERE fileTime > (?) AND fileTime < (?) AND cameraID = (?) FOR UPDATE',
                (mp.utc_datetime_to_milliseconds(UTC2datetime(utcMin)),
                 mp.utc_datetime_to_milliseconds(UTC2datetime(utcMax)), cameraId))
            read_cursor.name = "read_cursor"
            for (file_id,) in read_cursor:
                update_cursor.execute("DELETE FROM t_file WHERE CURRENT OF read_cursor")
                file_path = os.path.join(db_handle.file_store_path, uuid.UUID(bytes=file_id).hex)
                try:
                    os.remove(file_path)
                except OSError:
                    print "Warning: could not remove file {0}.".format(file_path)
            update_cursor.execute(
                "DELETE FROM t_event WHERE eventTime > (?) AND eventTime < (?) AND cameraID = (?)",
                (mp.utc_datetime_to_milliseconds(UTC2datetime(utcMin)),
                 mp.utc_datetime_to_milliseconds(UTC2datetime(utcMax)), cameraId))
    transaction.commit()
