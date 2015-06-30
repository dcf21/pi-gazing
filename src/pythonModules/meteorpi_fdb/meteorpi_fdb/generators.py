__author__ = 'tom'
import uuid
from contextlib import closing

from yaml import safe_load
import os.path as path
import meteorpi_model as mp
from backports.functools_lru_cache import lru_cache


def first_from_generator(generator):
    """Pull the first value from a generator and return it, closing the generator

    :param generator:
        A generator, this will be mapped onto a list and the first item extracted.
    :return:
        None if there are no items, or the first item otherwise.
    :internal:
    """
    try:
        result = next(generator)
    except StopIteration:
        result = None
    finally:
        generator.close()
    return result

def first_non_null(values):
    """
    Retrieve the first, non-null item in the specified list

    :param values:
        a list of values from which the first non-null is returned
    :return:
        the first non-null item
    :raises:
        ValueError if there isn't any such item in the list.
    """
    for item in values:
        if item is not None:
            return item
    raise ValueError("No non-null item in supplied list.")

class MeteorDatabaseGenerators(object):
    """
    Generator functions used to retrieve, and cache, items from the database.
    """
    def __init__(self, db):
        self.con = db.con
        self.db = db

    def cache_info(self):
        """
        Retrieve cache info for the LRU caches used by this database

        :return:
            A dict of cache name (status, event, file, export, user) to cache info
        """
        return {'status': self._get_camera_status_with_cache.cache_info(),
                'event': self._get_event_with_cache.cache_info(),
                'file': self._get_file_with_cache.cache_info(),
                'export': self._get_export_configuration_with_cache.cache_info()}

    def cache_clear(self, cache):
        """
        Clear a named cache

        :param cache:
            The cache to clear, one of (status, event, file, export, user)
        """
        if cache == 'file':
            self._get_file_with_cache.cache_clear()
        elif cache == 'event':
            self._get_event_with_cache.cache_clear()
        elif cache == 'export':
            self._get_event_with_cache.cache_clear()
        elif cache == 'status':
            self._get_camera_status_with_cache.cache_clear()
        else:
            raise ValueError("Unknown cache {0}, must be one of [file,event,export,status]".format(cache))

    def file_generator(self, sql, sql_args):
        """Generator for FileRecord

        :param sql:
            A SQL statement which must return rows with, in order, internal ID, camera ID, mime type, semantic type,
            file time, file size, file ID, file name and file status ID.
        :param sql_args:
            Any variables required to populate the query provided in 'sql'
        :return:
            A generator which produces FileRecord instances from the supplied SQL, closing any opened cursors on
            completion.
        """
        with closing(self.con.cursor()) as cursor:
            cursor.execute(sql, sql_args)
            for (internalID, cameraID, mimeType, semanticType, fileTime, fileSize, fileID, fileName,
                 statusID) in cursor:
                yield self._get_file_with_cache(internalID, cameraID, mimeType, semanticType, fileTime, fileSize,
                                                fileID, fileName, statusID)

    def event_generator(self, sql, sql_args):
        """Generator for Event

        :param sql:
            A SQL statement which must return rows with, in order: camera ID, event ID, internal ID, event time, event
            semantic type, status ID
        :param sql_args:
            Any variables required to populate the query provided in 'sql'
        :return:
            A generator which produces Event instances from the supplied SQL, closing any opened cursors on completion.
        """

        with closing(self.con.cursor()) as cursor:
            cursor.execute(sql, sql_args)
            for (cameraID, eventID, internalID, eventTime, eventType, statusID) in cursor:
                yield self._get_event_with_cache(cameraID, eventID, internalID, eventTime, eventType, statusID)

    def camera_status_generator(self, sql, sql_args):
        """
        Generator for :class:`meteorpi_model.CameraStatus`

        :param sql:
            A SQL statement which must return rows with, in order: lens, sensor, instURL, instName, locationLatitude,
            locationLongitude, locationGPS, locationError, orientationAltitude, orientationAzimuth, orientationError,
            orientationRotation, widthOfField, validFrom, softwareVersion, internalID, statusID, cameraID
        :param sql_args:
            Any arguments required to populate the query provided in 'sql'
        :return:
            A generator which produces :class:`meteorpi_model.CameraStatus` instances from the supplied SQL, closing
            any opened cursors on completion
        """
        with closing(self.con.cursor()) as cursor:
            cursor.execute(sql, sql_args)
            for (lens, sensor, instURL, instName, locationLatitude,
                 locationLongitude, locationGPS, locationError, orientationAltitude, orientationAzimuth,
                 orientationError, orientationRotation, widthOfField, validFrom, softwareVersion, internalID, statusID,
                 cameraID) in cursor:
                cs = self._get_camera_status_with_cache(lens, sensor, instURL, instName, locationLatitude,
                                                        locationLongitude, locationGPS, locationError,
                                                        orientationAltitude, orientationAzimuth, orientationError,
                                                        orientationRotation, widthOfField, validFrom, softwareVersion,
                                                        internalID, statusID, cameraID)
                yield cs

    def export_configuration_generator(self, sql, sql_args):
        """
        Generator for :class:`meteorpi_model.ExportConfiguration`

        :param sql:
            A SQL statement which must return rows with, in order: internalID, exportConfigID, exportType, searchString,
            targetURL, targetUser, targetPassword, exportName, description, active
        :param sql_args:
            Any variables required to populate the query provided in 'sql'
        :return:
            A generator which produces :class:`meteorpi_model.ExportConfiguration` instances from the supplied SQL,
            closing any opened cursors on completion.
        """

        with closing(self.con.cursor()) as cursor:
            cursor.execute(sql, sql_args)
            for (internalID, exportConfigID, exportType, searchString, targetURL,
                 targetUser, targetPassword, exportName, description, active) in cursor:
                yield self._get_export_configuration_with_cache(internalID, exportConfigID, exportType, searchString,
                                                                targetURL, targetUser, targetPassword, exportName,
                                                                description, active)

    @lru_cache(maxsize=128)
    def _get_file_with_cache(self, internalID, cameraID, mimeType, semanticType, fileTime, fileSize, fileID, fileName,
                             statusID):
        fr = mp.FileRecord(
            camera_id=cameraID,
            mime_type=mimeType,
            semantic_type=mp.NSString.from_string(semanticType),
            status_id=uuid.UUID(bytes=statusID))
        fr.file_id = uuid.UUID(bytes=fileID)
        fr.file_size = fileSize
        fr.file_time = mp.milliseconds_to_utc_datetime(fileTime)
        fr.file_name = fileName
        fr.get_path = lambda: path.join(self.db.file_store_path, fr.file_id.hex)
        with closing(self.con.cursor()) as meta_cur:
            meta_cur.execute(
                'SELECT metaKey, stringValue, floatValue, dateValue '
                'FROM t_fileMeta t '
                'WHERE t.fileID = (?) '
                'ORDER BY metaIndex ASC',
                (internalID,))
            for (metaKey, stringValue, floatValue, dateValue) in meta_cur:
                fr.meta.append(
                    mp.Meta(key=mp.NSString.from_string(metaKey),
                            value=first_non_null(
                                [stringValue, floatValue, mp.milliseconds_to_utc_datetime(dateValue)])))
        return fr

    @lru_cache(maxsize=128)
    def _get_event_with_cache(self, cameraID, eventID, internalID, eventTime, eventType, statusID):
        event = mp.Event(
            camera_id=cameraID,
            event_time=mp.milliseconds_to_utc_datetime(eventTime),
            event_id=uuid.UUID(bytes=eventID),
            event_type=mp.NSString.from_string(eventType),
            status_id=uuid.UUID(bytes=statusID))
        fr_sql = 'SELECT f.internalID, f.cameraID, f.mimeType, ' \
                 'f.semanticType, f.fileTime, f.fileSize, f.fileID, f.fileName, s.statusID ' \
                 'FROM t_file f, t_cameraStatus s, t_event_to_file ef ' \
                 'WHERE f.statusID = s.internalID AND ef.fileID = f.internalID AND ef.eventID = (?)'
        event.file_records = list(self.file_generator(fr_sql, (internalID,)))
        with closing(self.con.cursor()) as meta_cur:
            meta_cur.execute(
                'SELECT metaKey, stringValue, floatValue, dateValue '
                'FROM t_eventMeta t '
                'WHERE t.eventID = (?) '
                'ORDER BY metaIndex ASC',
                (internalID,))
            for (metaKey, stringValue, floatValue, dateValue) in meta_cur:
                event.meta.append(
                    mp.Meta(key=mp.NSString.from_string(metaKey),
                            value=first_non_null(
                                [stringValue, floatValue, mp.milliseconds_to_utc_datetime(dateValue)])))
        return event

    @lru_cache(maxsize=128)
    def _get_camera_status_with_cache(self, lens, sensor, instURL, instName, locationLatitude,
                                      locationLongitude, locationGPS, locationError, orientationAltitude,
                                      orientationAzimuth,
                                      orientationError, orientationRotation, widthOfField, validFrom, softwareVersion,
                                      internalID, statusID,
                                      cameraID):
        # Find if there's a status block for this camera ID after the current one, and use it's validFrom time
        # as the validTo time on the camera status if so
        with closing(self.con.cursor()) as valid_to_cursor:
            valid_to_cursor.execute(
                'SELECT validFrom FROM t_cameraStatus t '
                'WHERE t.cameraID = (?) AND t.validFrom > (?) '
                'ORDER BY t.validFrom ASC '
                'ROWS 1',
                (cameraID,
                 validFrom))
            after_row = valid_to_cursor.fetchone()
            if after_row is None:
                validTo = None
            else:
                validTo = mp.milliseconds_to_utc_datetime(after_row[0])
        cs = mp.CameraStatus(lens=lens,
                             sensor=sensor,
                             inst_url=instURL,
                             inst_name=instName,
                             orientation=mp.Orientation(
                                 altitude=orientationAltitude,
                                 azimuth=orientationAzimuth,
                                 rotation=orientationRotation,
                                 error=orientationError,
                                 width_of_field=widthOfField),
                             location=mp.Location(
                                 latitude=locationLatitude,
                                 longitude=locationLongitude,
                                 gps=locationGPS is True,
                                 error=locationError),
                             camera_id=cameraID,
                             status_id=uuid.UUID(bytes=statusID))
        cs.valid_from = mp.milliseconds_to_utc_datetime(validFrom)
        cs.valid_to = validTo
        cs.software_version = softwareVersion
        with closing(self.con.cursor()) as region_cursor:
            region_cursor.execute('SELECT region, x, y FROM t_visibleRegions t '
                                  'WHERE t.cameraStatusID = (?) '
                                  'ORDER BY region ASC, pointOrder ASC', (internalID,))
            for (region, x, y) in region_cursor:
                if len(cs.regions) <= region:
                    cs.regions.append([])
                cs.regions[region].append(
                    {'x': x, 'y': y})
        return cs

    @lru_cache(maxsize=128)
    def _get_export_configuration_with_cache(self, internalID, exportConfigID, exportType, searchString, targetURL,
                                             targetUser, targetPassword, exportName, description, active):
        if exportType == "event":
            search = mp.EventSearch.from_dict(safe_load(searchString))
        elif exportType == "file":
            search = mp.FileRecordSearch.from_dict(safe_load(searchString))
        else:
            raise ValueError("Unknown search type!")
        return mp.ExportConfiguration(target_url=targetURL, user_id=targetUser, password=targetPassword,
                                      search=search, name=exportName, description=description, enabled=active,
                                      config_id=uuid.UUID(bytes=exportConfigID))
