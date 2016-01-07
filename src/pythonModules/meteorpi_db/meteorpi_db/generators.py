# generators.py

# Helper functions for generating MeteorPi objects from SQL query results

import json
import meteorpi_model as mp

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
    def __init__(self, db, con):
        self.con = con
        self.db = db

    def file_generator(self, sql, sql_args):
        """Generator for FileRecord

        :param sql:
            A SQL statement which must return rows describing files.
        :param sql_args:
            Any variables required to populate the query provided in 'sql'
        :return:
            A generator which produces FileRecord instances from the supplied SQL, closing any opened cursors on
            completion.
        """

        self.con.execute(sql, sql_args)
        results = self.con.fetchall()
        output = []
        for result in results:
            file_record = mp.FileRecord(camera_id=result['camera_id'], camera_name=result['camera_name'],
                             repository_fname=result['repositoryFname'],
                             file_time=result['fileTime'], file_size=result['fileSize'],
                             file_name=result['fileName'], mime_type=result['mimeType'],
                             file_md5=result['fileMD5'],
                             semantic_type=result['semanticType'])
            output.append(file_record)
        return output

    def observation_generator(self, sql, sql_args):
        """Generator for Observation

        :param sql:
            A SQL statement which must return rows describing observations
        :param sql_args:
            Any variables required to populate the query provided in 'sql'
        :return:
            A generator which produces Event instances from the supplied SQL, closing any opened cursors on completion.
        """

        self.con.execute(sql, sql_args)
        results = self.con.fetchall()
        output = []
        for result in results:
            observation = mp.Observation(camera_id=result['camera_id'], camera_name=result['camera_name'],
                                        obs_time=result['obsTime'], obs_id=result['publicId'],
                                        observation_type=result['obsType'])

            # Look up observation metadata
            sql = """SELECT f.metaKey, stringValue, floatValue
FROM archive_metadata m
INNER JOIN archive_metadataFields f ON m.fieldId=f.uid
WHERE m.observatory=%s
"""
            self.con.execute(sql, (result['observatory'],))
            for item in self.con.fetchall():
                value = first_non_null([item['stringValue'],item['floatValue']])
                observation.meta.append(mp.Meta(item['metaKey'],value))

            # Count votes for observation
            self.con.execute("SELECT COUNT(*) FROM archive_obs_likes WHERE observationId=%s;", (result['publicId'],))
            observation.likes = self.con.fetchone()['COUNT(*)']

            output.append(observation)

        return output

    def camera_metadata_generator(self, sql, sql_args):
        """
        Generator for :class:`meteorpi_model.CameraStatus`

        :param sql:
            A SQL statement which must return rows describing camera metadata
        :param sql_args:
            Any arguments required to populate the query provided in 'sql'
        :return:
            A generator which produces :class:`meteorpi_model.CameraStatus` instances from the supplied SQL, closing
            any opened cursors on completion
        """

        self.con.execute(sql, sql_args)
        results = self.con.fetchall()
        output = []
        for result in results:
            if result['stringValue'] is None:
                value = result['floatValue']
            else:
                value = result['stringValue']
            obsMeta = mp.ObservatoryMetadata(camera_id=result['camera_id'], camera_name=result['camera_name'],
                                                 camera_lat=result['camera_lat'], camera_lng=result['camera_lng'],
                                                 key=result['metadata_key'], value=value,
                                                 metadata_time=result['time'], time_created=result['time_created'],
                                                 user_created=result['user_created'])
            output.append(obsMeta)

        return output

    def export_configuration_generator(self, sql, sql_args):
        """
        Generator for :class:`meteorpi_model.ExportConfiguration`

        :param sql:
            A SQL statement which must return rows describing export configurations
        :param sql_args:
            Any variables required to populate the query provided in 'sql'
        :return:
            A generator which produces :class:`meteorpi_model.ExportConfiguration` instances from the supplied SQL,
            closing any opened cursors on completion.
        """

        self.con.execute(sql, sql_args)
        results = self.con.fetchall()
        output = []
        for result in results:
            if result['exportType'] == "observation":
                search = mp.ObservationSearch.from_dict(json.loads(result['searchString']))
            elif result['exportType'] == "file":
                search = mp.FileRecordSearch.from_dict(json.loads(result['searchString']))
            else:
                search = mp.ObservatoryMetadataSearch.from_dict(json.loads(result['searchString']))
            conf = mp.ExportConfiguration(target_url=result['targetURL'], user_id=result['targetUser'],
                                          password=result['targetPassword'], search=search,
                                          name=result['exportName'], description=result['description'],
                                          enabled=result['active'], config_id=result['exportConfigId'])
            output.append(conf)

        return output