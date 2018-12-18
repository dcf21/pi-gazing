# -*- coding: utf-8 -*-
# obsarchive_model.py


# Classes which represent observation archive objects

import hashlib
import numbers
import random
import re
import time


def _boolean_from_dict(d, key):
    return key in d and d[key] == True


def _string_from_dict(d, key, default=None):
    if key in d:
        return str(d[key])
    else:
        return default


def _value_from_dict(d, key, default=None):
    if key in d:
        return d[key]
    else:
        return default


def _add_string(d, key, value):
    if value is not None:
        d[key] = str(value)


def _add_value(d, key, value):
    if value is not None:
        d[key] = value


def _add_boolean(d, key, value, include_false=False):
    if value:
        d[key] = True
    elif include_false:
        d[key] = False


def now():
    """Returns the current UTC timestamp"""
    return time.time()


def get_hash(utc, str1, str2, str3=None):
    if str3 is None:
        str3 = "%s_%s" % (time.time(), random.random())
    tstr = time.strftime("%Y%m%d_%H%M%S", time.gmtime(utc))
    key = "%s_%s_%s" % (str1, str2, str3)
    uid = hashlib.md5(key.encode()).hexdigest()

    # Preserve file extension, so that Apache serves it with the right MIME type
    test = re.match(".*(\.[^.]*)", str2)
    if not (test is None):
        suffix = test.group(1)
        output = ("%s_%s" % (tstr, uid))[0:32 - len(suffix)] + suffix
    else:
        output = ("%s_%s" % (tstr, uid))[0:32]

    return output


def get_md5_hash(file_path):
    """
    Calculate the MD5 checksum for a file.

    :param string file_path:
        Path to the file
    :return:
        MD5 checksum
    """
    checksum = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(128 * checksum.block_size), b''):
            checksum.update(chunk)
    return checksum.hexdigest()


class ModelEqualityMixin(object):
    """
    Taken from http://stackoverflow.com/questions/390250/, simplifies object equality tests.

    :internal:
    """

    def __eq__(self, other):
        """Override the default Equals behavior"""
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return NotImplemented

    def __ne__(self, other):
        """Define a non-equality test"""
        if isinstance(other, self.__class__):
            return not self.__eq__(other)
        return NotImplemented

    def __hash__(self):
        """Override the default hash behavior (that returns the id or the object)"""
        return hash(tuple(sorted(self.__dict__.items())))


class User(ModelEqualityMixin):
    """
    A single user in an instance of the observation archive server

    Class variables:

    :cvar list[string] roles:
        A sequence of roles.

    Instance variables:

    :ivar string user_id:
        a string ID for the user
    :ivar int roles:
        a list of roles the user has assigned
    """

    def __init__(self, user_id, roles, name, job, email, join_date, profile_pic, profile_text):
        self.user_id = user_id
        self.roles = roles
        self.name = name
        self.job = job
        self.email = email
        self.joinDate = join_date
        self.profilePic = profile_pic
        self.profileText = profile_text

    def has_role(self, role):
        """
        Determine whether the user has a given role

        :param string role:
            The role to test
        :returns:
            True if the user can act in that role, False otherwise
        """
        return role in self.roles

    def get_roles(self):
        """
        :returns:
            A sequence of strings, each string being a role that the user can access
        """
        return self.roles

    def as_dict(self):
        return {"user_id": self.user_id,
                "roles": self.roles,
                "name": self.name,
                "job": self.job,
                "email": self.email,
                "joinDate": self.joinDate,
                "profilePic": self.profilePic,
                "profileText": self.profileText
                }

    @staticmethod
    def from_dict(d):
        return User(user_id=d['user_id'],
                    roles=d['roles'],
                    name=d['name'],
                    job=d['job'],
                    email=d['email'],
                    join_date=d['joinDate'],
                    profile_pic=d['profilePic'],
                    profile_text=d['profileText'])


class FileRecordSearch(ModelEqualityMixin):
    """
    Encapsulates the possible parameters which can be used to search for :class:`obsarchive_model.FileRecord` instances
    """

    def __init__(self, obstory_ids=None, lat_min=None, lat_max=None, long_min=None, long_max=None, time_min=None,
                 time_max=None, mime_type=None, semantic_type=None, observation_type=None,
                 observation_id=None, repository_fname=None,
                 meta_constraints=None, limit=100, skip=0, exclude_export_to=None,
                 exclude_imported=False):
        """
        Create a new FileRecordSearch. All parameters are optional, a default search will be created which returns
        at most the first 100 FileRecord instances. All parameters specify restrictions on these results.

        :param list[string] obstory_ids:
            Optional - if specified, restricts results to only those the the specified obstory IDs which
            are expressed as an array of strings.
        :param float lat_min:
            Optional - if specified, only returns results where the obstory status at the time of the file
            had a latitude field of at least the specified value.
        :param float lat_max:
            Optional - if specified, only returns results where the obstory status at the time of the file
            had a latitude field of at most the specified value.
        :param float long_min:
            Optional - if specified, only returns results where the obstory status at the time of the file
            had a longitude field of at least the specified value.
        :param float long_max:
            Optional - if specified, only returns results where the obstory status at the time of the file
            had a longitude field of at most the specified value.
        :param float time_min:
            Optional - if specified, only returns results where the file time is after the specified value.
        :param float time_max:
            Optional - if specified, only returns results where the file time is before the specified value.
        :param string mime_type:
            Optional - if specified, only returns results where the MIME type exactly matches the
            specified value.
        :param string semantic_type:
            Optional - if specified, only returns results where the semantic type exactly matches.
            The type of this value should be an instance of :class:`obsarchive_model.NSString`
        :param string observation_type:
            Optional - search only for files associated with a particular observation type.
        :param int observation_id:
            Optional - return only files associated with a particular observation
        :param string repository_fname:
            Optional - fetch file with this repository filename
        :param list[MetaConstraint] meta_constraints:
            Optional - a list of :class:`obsarchive_model.MetaConstraint` objects providing restrictions over the file
            record metadata.
        :param int limit:
            Optional, defaults to 100 - controls the maximum number of results that will be returned by this
            search. If set to 0 will return all results, but be aware that this may potentially have negative effects on
            the server software. Only set this to 0 when you are sure that you won't return too many results!
        :param int skip:
            Optional, defaults to 0 - used with the limit parameter, this will skip the specified number
            of results from the result set. Use when limiting the number returned by each query to paginate the results,
            i.e. use skip 0 and limit 10 to get the first ten, then skip 10 limit 10 to get the next and so on.
        :param string exclude_export_to:
            Optional, if specified excludes FileRecords with an entry in t_fileExport for the specified file export
            configuration.
        :param Boolean exclude_imported:
            Optional, if True excludes any FileRecords which were imported from another node.
        """
        if ((obstory_ids is not None) and (type(obstory_ids) is not str) and
                ((type(obstory_ids) is not list) or (len(obstory_ids) == 0))):
            raise ValueError('If obstory_ids is specified it must be a list and must contain at least one ID')
        if lat_min is not None and lat_max is not None and lat_max < lat_min:
            raise ValueError('Latitude max cannot be less than latitude minimum')
        if long_min is not None and long_max is not None and long_max < long_min:
            raise ValueError('Longitude max cannot be less than longitude minimum')
        if time_min is not None and time_max is not None and time_max < time_min:
            raise ValueError('Time max cannot be after before time min')
        if isinstance(obstory_ids, str):
            obstory_ids = [obstory_ids]
        self.obstory_ids = obstory_ids
        self.lat_min = lat_min
        self.lat_max = lat_max
        self.long_min = long_min
        self.long_max = long_max
        self.time_min = time_min
        self.time_max = time_max
        self.mime_type = mime_type
        self.skip = skip
        self.limit = limit
        self.semantic_type = semantic_type
        self.observation_type = observation_type
        self.observation_id = observation_id
        self.repository_fname = repository_fname
        # Import / export related functions
        self.exclude_imported = exclude_imported
        self.exclude_export_to = exclude_export_to
        # FileMeta constraints
        if meta_constraints is None:
            self.meta_constraints = []
        else:
            self.meta_constraints = meta_constraints

    def __str__(self):
        fields = []
        for field in self.__dict__:
            if self.__dict__[field] is not None:
                fields.append({'name': field, 'value': self.__dict__[field]})
        return '{0}[{1}]'.format(self.__class__.__name__,
                                 ','.join(('{0}=\'{1}\''.format(x['name'], str(x['value'])) for x in fields)))

    def as_dict(self):
        """
        Convert this FileRecordSearch to a dict, ready for serialization to JSON for use in the API.

        :return:
            Dict representation of this FileRecordSearch instance
        """
        d = {}
        _add_value(d, 'obstory_ids', self.obstory_ids)
        _add_value(d, 'lat_min', self.lat_min)
        _add_value(d, 'lat_max', self.lat_max)
        _add_value(d, 'long_min', self.long_min)
        _add_value(d, 'long_max', self.long_max)
        _add_value(d, 'time_min', self.time_min)
        _add_value(d, 'time_max', self.time_max)
        _add_value(d, 'mime_type', self.mime_type)
        _add_value(d, 'skip', self.skip)
        _add_value(d, 'limit', self.limit)
        _add_string(d, 'semantic_type', self.semantic_type)
        _add_string(d, 'observation_type', self.observation_type)
        _add_value(d, 'observation_id', self.observation_id)
        _add_string(d, 'repository_fname', self.repository_fname)
        _add_boolean(d, 'exclude_imported', self.exclude_imported)
        _add_string(d, 'exclude_export_to', self.exclude_export_to)
        d['meta'] = list((x.as_dict() for x in self.meta_constraints))
        return d

    @staticmethod
    def from_dict(d):
        """
        Builds a new instance of FileRecordSearch from a dict

        :param Object d: the dict to parse
        :return: a new FileRecordSearch based on the supplied dict
        """
        obstory_ids = _value_from_dict(d, 'obstory_ids')
        lat_min = _value_from_dict(d, 'lat_min')
        lat_max = _value_from_dict(d, 'lat_max')
        long_min = _value_from_dict(d, 'long_min')
        long_max = _value_from_dict(d, 'long_max')
        time_min = _value_from_dict(d, 'time_min')
        time_max = _value_from_dict(d, 'time_max')
        mime_type = _string_from_dict(d, 'mime_type')
        skip = _value_from_dict(d, 'skip', 0)
        limit = _value_from_dict(d, 'limit', 100)
        semantic_type = _string_from_dict(d, 'semantic_type')
        observation_type = _string_from_dict(d, 'observation_type')
        observation_id = _value_from_dict(d, 'observation_id')
        repository_fname = _string_from_dict(d, 'repository_fname')
        exclude_imported = _boolean_from_dict(d, 'exclude_imported')
        exclude_export_to = _string_from_dict(d, 'exclude_export_to')
        if 'meta' in d:
            meta_constraints = list((MetaConstraint.from_dict(x) for x in d['meta']))
        else:
            meta_constraints = []
        return FileRecordSearch(obstory_ids=obstory_ids, lat_min=lat_min, lat_max=lat_max, long_min=long_min,
                                long_max=long_max, time_min=time_min, time_max=time_max, mime_type=mime_type,
                                semantic_type=semantic_type,
                                observation_type=observation_type,
                                observation_id=observation_id, repository_fname=repository_fname,
                                meta_constraints=meta_constraints, limit=limit, skip=skip,
                                exclude_imported=exclude_imported,
                                exclude_export_to=exclude_export_to)


class ObservationSearch(ModelEqualityMixin):
    """
    Encapsulates the possible parameters which can be used to search for :class:`Observation` instances in the database.
    If parameters are set to None this means they won't be used to restrict the possible set of results.
    """

    def __init__(self, obstory_ids=None, lat_min=None, lat_max=None, long_min=None, long_max=None, time_min=None,
                 time_max=None, observation_type=None, observation_id=None, meta_constraints=None, limit=100,
                 skip=0, exclude_export_to=None, exclude_imported=False):
        """
        Create a new ObservationSearch. All parameters are optional, a default search will be created which returns
        at most the first 100 instances. All parameters specify restrictions on these results.

        :param list[string] obstory_ids:
            Optional - if specified, restricts results to only those the the specified obstory IDs which
            are expressed as an array of strings.
        :param float lat_min:
            Optional - if specified, only returns results where the obstory status at the time of the observation
            had a latitude field of at least the specified value.
        :param float lat_max:
            Optional - if specified, only returns results where the obstory status at the time of the observation
            had a latitude field of at most the specified value.
        :param float long_min:
            Optional - if specified, only returns results where the obstory status at the time of the observation
            had a longitude field of at least the specified value.
        :param float long_max:
            Optional - if specified, only returns results where the obstory status at the time of the observation
            had a longitude field of at most the specified value.
        :param float time_min:
            Optional - if specified, only returns results where the observation time is after the specified value.
        :param float time_max:
            Optional - if specified, only returns results where the observation time is before the specified value
        :param list[MetaConstraint] meta_constraints:
            Optional - a list of :class:`obsarchive_model.MetaConstraint` objects providing restrictions over the
            observation metadata.
        :param int limit:
            Optional, defaults to 100 - controls the maximum number of results that will be returned by this
            search. If set to 0 will return all results, but be aware that this may potentially have negative effects on
            the server software. Only set this to 0 when you are sure that you won't return too many results!
        :param int skip:
            Optional, defaults to 0 - used with the limit parameter, this will skip the specified number
            of results from the result set. Use when limiting the number returned by each query to paginate the results,
            i.e. use skip 0 and limit 10 to get the first ten, then skip 10 limit 10 to get the next and so on.
        :param string exclude_export_to:
            Optional, if specified excludes Observations with an entry in t_observationExport for the specified
            observation export configuration.
        :param Boolean exclude_imported:
            Optional, if True excludes any Observations which were imported from another node.
        """
        if ((obstory_ids is not None) and (type(obstory_ids) is not str) and
                ((type(obstory_ids) is not list) or (len(obstory_ids) == 0))):
            raise ValueError('If obstory_ids is specified it must be a list and must contain at least one ID')
        if lat_min is not None and lat_max is not None and lat_max < lat_min:
            raise ValueError('Latitude max cannot be less than latitude minimum')
        if long_min is not None and long_max is not None and long_max < long_min:
            raise ValueError('Longitude max cannot be less than longitude minimum')
        if time_min is not None and time_max is not None and time_max < time_min:
            raise ValueError('Time min cannot be after before time max')
        if isinstance(obstory_ids, str):
            obstory_ids = [obstory_ids]
        self.obstory_ids = obstory_ids
        self.lat_min = lat_min
        self.lat_max = lat_max
        self.long_min = long_min
        self.long_max = long_max
        self.time_min = time_min
        self.time_max = time_max
        self.observation_type = observation_type
        self.observation_id = observation_id
        self.limit = limit
        self.skip = skip
        # Import / export related functions
        self.exclude_imported = exclude_imported
        self.exclude_export_to = exclude_export_to
        if meta_constraints is None:
            self.meta_constraints = []
        else:
            self.meta_constraints = meta_constraints

    def __str__(self):
        fields = []
        for field in self.__dict__:
            if self.__dict__[field] is not None:
                fields.append({'name': field, 'value': self.__dict__[field]})
        return '{0}[{1}]'.format(self.__class__.__name__,
                                 ','.join(('{0}=\'{1}\''.format(x['name'], str(x['value'])) for x in fields)))

    def as_dict(self):
        """
        Convert this ObservationSearch to a dict, ready for serialization to JSON for use in the API.

        :return:
            Dict representation of this ObservationSearch instance
        """
        d = {}
        _add_value(d, 'obstory_ids', self.obstory_ids)
        _add_value(d, 'lat_min', self.lat_min)
        _add_value(d, 'lat_max', self.lat_max)
        _add_value(d, 'long_min', self.long_min)
        _add_value(d, 'long_max', self.long_max)
        _add_value(d, 'time_min', self.time_min)
        _add_value(d, 'time_max', self.time_max)
        _add_value(d, 'skip', self.skip)
        _add_value(d, 'limit', self.limit)
        _add_string(d, 'observation_type', self.observation_type)
        _add_string(d, 'observation_id', self.observation_id)
        _add_boolean(d, 'exclude_imported', self.exclude_imported)
        _add_string(d, 'exclude_export_to', self.exclude_export_to)
        d['meta'] = list((x.as_dict() for x in self.meta_constraints))
        return d

    @staticmethod
    def from_dict(d):
        obstory_ids = _value_from_dict(d, 'obstory_ids')
        lat_min = _value_from_dict(d, 'lat_min')
        lat_max = _value_from_dict(d, 'lat_max')
        long_min = _value_from_dict(d, 'long_min')
        long_max = _value_from_dict(d, 'long_max')
        time_min = _value_from_dict(d, 'time_min')
        time_max = _value_from_dict(d, 'time_max')
        skip = _value_from_dict(d, 'skip', 0)
        limit = _value_from_dict(d, 'limit', 100)
        observation_type = _string_from_dict(d, 'observation_type')
        observation_id = _string_from_dict(d, 'observation_id')
        exclude_imported = _boolean_from_dict(d, 'exclude_imported')
        exclude_export_to = _string_from_dict(d, 'exclude_export_to')
        if 'meta' in d:
            meta_constraints = list((MetaConstraint.from_dict(x) for x in d['meta']))
        else:
            meta_constraints = []
        return ObservationSearch(obstory_ids=obstory_ids, lat_min=lat_min, lat_max=lat_max, long_min=long_min,
                                 long_max=long_max, time_min=time_min, time_max=time_max,
                                 meta_constraints=meta_constraints,
                                 observation_type=observation_type, observation_id=observation_id,
                                 limit=limit, skip=skip, exclude_imported=exclude_imported,
                                 exclude_export_to=exclude_export_to)


class ObservationGroupSearch(ModelEqualityMixin):
    """
    Encapsulates the possible parameters which can be used to search for :class:`ObservationGroup` instances in
    the database. If parameters are set to None this means they won't be used to restrict the possible set of results.
    """

    def __init__(self, obstory_name=None, semantic_type=None, time_min=None, group_id=None,
                 time_max=None, child_observation_id=None, child_group_id=None,
                 meta_constraints=None, limit=100, skip=0):
        """
        Create a new ObservationGroupSearch. All parameters are optional, a default search will be created which returns
        at most the first 100 instances. All parameters specify restrictions on these results.

        :param string obstory_name:
            Optional - if specified, restricts results to groups containing observations from the specified obstory,
            expressed as string.
        :param float time_min:
            Optional - if specified, only returns results where the observation time is after the specified value.
        :param float time_max:
            Optional - if specified, only returns results where the observation time is before the specified value.
        :param string group_id:
            Optional - search for a group by ID
        :param string child_observation_id:
            Optional - search for groups containing a particular observation
        :param string child_group_id:
            Optional - search for groups containing a particular sub-group
        :param list[MetaConstraint] meta_constraints:
            Optional - a list of :class:`obsarchive_model.MetaConstraint` objects providing restrictions over the
            observation group metadata.
        :param int limit:
            Optional, defaults to 100 - controls the maximum number of results that will be returned by this
            search. If set to 0 will return all results, but be aware that this may potentially have negative effects on
            the server software. Only set this to 0 when you are sure that you won't return too many results!
        :param int skip:
            Optional, defaults to 0 - used with the limit parameter, this will skip the specified number
            of results from the result set. Use when limiting the number returned by each query to paginate the results,
            i.e. use skip 0 and limit 10 to get the first ten, then skip 10 limit 10 to get the next and so on.
        """
        if time_min is not None and time_max is not None and time_max < time_min:
            raise ValueError('Time min cannot be after before time max')
        self.obstory_name = obstory_name
        self.semantic_type = semantic_type
        self.time_min = time_min
        self.time_max = time_max
        self.group_id = group_id
        self.child_observation_id = child_observation_id
        self.child_group_id = child_group_id
        self.limit = limit
        self.skip = skip

        if meta_constraints is None:
            self.meta_constraints = []
        else:
            self.meta_constraints = meta_constraints

    def __str__(self):
        fields = []
        for field in self.__dict__:
            if self.__dict__[field] is not None:
                fields.append({'name': field, 'value': self.__dict__[field]})
        return '{0}[{1}]'.format(self.__class__.__name__,
                                 ','.join(('{0}=\'{1}\''.format(x['name'], str(x['value'])) for x in fields)))

    def as_dict(self):
        """
        Convert this ObservationGroupSearch to a dict, ready for serialization to JSON for use in the API.

        :return:
            Dict representation of this ObservationGroupSearch instance
        """
        d = {}
        _add_string(d, 'obstory_name', self.obstory_name)
        _add_string(d, 'semantic_type', self.semantic_type)
        _add_value(d, 'time_min', self.time_min)
        _add_value(d, 'time_max', self.time_max)
        _add_string(d, 'group_id', self.group_id)
        _add_string(d, 'child_observation_id', self.child_observation_id)
        _add_string(d, 'child_group_id', self.child_group_id)
        _add_value(d, 'skip', self.skip)
        _add_value(d, 'limit', self.limit)
        d['meta'] = list((x.as_dict() for x in self.meta_constraints))
        return d

    @staticmethod
    def from_dict(d):
        obstory_name = _value_from_dict(d, 'obstory_name')
        semantic_type = _string_from_dict(d, 'semantic_type')
        time_min = _value_from_dict(d, 'time_min')
        time_max = _value_from_dict(d, 'time_max')
        group_id = _string_from_dict(d, 'group_id')
        child_observation_id = _string_from_dict(d, 'child_observation_id')
        child_group_id = _string_from_dict(d, 'child_group_id')
        skip = _value_from_dict(d, 'skip', 0)
        limit = _value_from_dict(d, 'limit', 100)
        if 'meta' in d:
            meta_constraints = list((MetaConstraint.from_dict(x) for x in d['meta']))
        else:
            meta_constraints = []
        return ObservationGroupSearch(obstory_name=obstory_name, semantic_type=semantic_type,
                                      time_min=time_min, time_max=time_max,
                                      meta_constraints=meta_constraints,
                                      child_observation_id=child_observation_id,
                                      child_group_id=child_group_id,
                                      group_id=group_id,
                                      limit=limit, skip=skip)


class ObservatoryMetadataSearch(ModelEqualityMixin):
    """
    Encapsulates the possible parameters which can be used to search for :class:`ObservatoryMetadata` instances in the
    database. If parameters are set to None this means they won't be used to restrict the possible set of results.
    """

    def __init__(self, obstory_ids=None, field_name=None, lat_min=None, lat_max=None, long_min=None, long_max=None,
                 time_min=None, time_max=None, item_id=None,
                 limit=100, skip=0, exclude_export_to=None, exclude_imported=False):
        """
        Create a new ObservatoryMetadataSearch. All parameters are optional, a default search will be created which
        returns at most the first 100 instances. All parameters specify restrictions on these results.

        :param list[string] obstory_ids:
            Optional - if specified, restricts results to only the specified obstory IDs which
            are expressed as an array of strings.
        :param string field_name:
            Optional - name of metadata field to search for
        :param float lat_min:
            Optional - if specified, only returns results where the latitude field of at least the specified value.
        :param float lat_max:
            Optional - if specified, only returns results where the latitude field of at most the specified value.
        :param float long_min:
            Optional - if specified, only returns results where the longitude field of at least the specified value.
        :param float long_max:
            Optional - if specified, only returns results where the longitude field of at most the specified value.
        :param float time_min:
            Optional - if specified, only returns results where the time is after the specified value.
        :param float time_max:
            Optional - if specified, only returns results where the time is before the specified value
        :param int limit:
            Optional, defaults to 100 - controls the maximum number of results that will be returned by this
            search. If set to 0 will return all results.
        :param int skip:
            Optional, defaults to 0 - used with the limit parameter, this will skip the specified number
            of results from the result set. Use when limiting the number returned by each query to paginate the results,
            i.e. use skip 0 and limit 10 to get the first ten, then skip 10 limit 10 to get the next and so on.
        :param string exclude_export_to:
            Optional, if specified excludes Observations with an entry in t_metadataExport for the specified
            observation export configuration.
        :param Boolean exclude_imported:
            Optional, if True excludes any Metadata which were imported from another node.
        """
        if ((obstory_ids is not None) and (type(obstory_ids) is not str) and
                ((type(obstory_ids) is not list) or (len(obstory_ids) == 0))):
            raise ValueError('If obstory_ids is specified it must be a list and must contain at least one ID')
        if lat_min is not None and lat_max is not None and lat_max < lat_min:
            raise ValueError('Latitude max cannot be less than latitude minimum')
        if long_min is not None and long_max is not None and long_max < long_min:
            raise ValueError('Longitude max cannot be less than longitude minimum')
        if time_min is not None and time_max is not None and time_max < time_min:
            raise ValueError('Time min cannot be after before time max')
        if isinstance(obstory_ids, str):
            obstory_ids = [obstory_ids]
        self.obstory_ids = obstory_ids
        self.field_name = field_name
        self.lat_min = lat_min
        self.lat_max = lat_max
        self.long_min = long_min
        self.long_max = long_max
        self.time_min = time_min
        self.time_max = time_max
        self.item_id = item_id
        self.limit = limit
        self.skip = skip
        # Import / export related functions
        self.exclude_imported = exclude_imported
        self.exclude_export_to = exclude_export_to

    def __str__(self):
        fields = []
        for field in self.__dict__:
            if self.__dict__[field] is not None:
                fields.append({'name': field, 'value': self.__dict__[field]})
        return '{0}[{1}]'.format(self.__class__.__name__,
                                 ','.join(('{0}=\'{1}\''.format(x['name'], str(x['value'])) for x in fields)))

    def as_dict(self):
        """
        Convert this ObservatoryMetadataSearch to a dict, ready for serialization to JSON for use in the API.

        :return:
            Dict representation of this ObservatoryMetadataSearch instance
        """
        d = {}
        _add_value(d, 'obstory_ids', self.obstory_ids)
        _add_string(d, 'field_name', self.field_name)
        _add_value(d, 'lat_min', self.lat_min)
        _add_value(d, 'lat_max', self.lat_max)
        _add_value(d, 'long_min', self.long_min)
        _add_value(d, 'long_max', self.long_max)
        _add_value(d, 'time_min', self.time_min)
        _add_value(d, 'time_max', self.time_max)
        _add_string(d, 'item_id', self.item_id)
        _add_value(d, 'skip', self.skip)
        _add_value(d, 'limit', self.limit)
        _add_boolean(d, 'exclude_imported', self.exclude_imported)
        _add_string(d, 'exclude_export_to', self.exclude_export_to)
        return d

    @staticmethod
    def from_dict(d):
        obstory_ids = _value_from_dict(d, 'obstory_ids')
        field_name = _string_from_dict(d, 'field_name')
        lat_min = _value_from_dict(d, 'lat_min')
        lat_max = _value_from_dict(d, 'lat_max')
        long_min = _value_from_dict(d, 'long_min')
        long_max = _value_from_dict(d, 'long_max')
        time_min = _value_from_dict(d, 'time_min')
        time_max = _value_from_dict(d, 'time_max')
        item_id = _string_from_dict(d, 'item_id')
        skip = _value_from_dict(d, 'skip', 0)
        limit = _value_from_dict(d, 'limit', 100)
        exclude_imported = _boolean_from_dict(d, 'exclude_imported')
        exclude_export_to = _string_from_dict(d, 'exclude_export_to')
        return ObservatoryMetadataSearch(obstory_ids=obstory_ids, field_name=field_name, lat_min=lat_min,
                                         lat_max=lat_max,
                                         long_min=long_min, long_max=long_max, time_min=time_min, time_max=time_max,
                                         item_id=item_id,
                                         limit=limit, skip=skip, exclude_imported=exclude_imported,
                                         exclude_export_to=exclude_export_to)


class MetaConstraint(ModelEqualityMixin):
    """Defines a constraint over metadata on a FileRecord or Observation, used in the respective searches."""

    def __init__(self, constraint_type, key, value):
        """
        Constructor

        :param string constraint_type:
            one of 'string_equals', 'number_equals', 'less', 'greater'
        :param string key:
            an :class:`obsarchive_model.NSString` containing the namespace prefixed string to use as a key
        :param object value:
            the value, for string_equals this is a String, and for 'less', 'greater' and 'number_equals' a number
            (generally a :class:`float` or :class:`int`).
        """
        self.constraint_type = constraint_type
        self.key = key
        self.value = value

    def as_dict(self):
        c_type = self.constraint_type
        d = {'key': str(self.key),
             'type': c_type}
        if c_type == 'less' or c_type == 'greater' or c_type == 'number_equals':
            _add_value(d, 'value', self.value)
        elif c_type == 'string_equals':
            _add_string(d, 'value', self.value)
        else:
            raise ValueError("Unknown MetaConstraint constraint type!")
        return d

    @staticmethod
    def from_dict(d):
        c_type = _string_from_dict(d, 'type')
        key = _string_from_dict(d, 'key')
        if c_type == 'less' or c_type == 'greater' or c_type == 'number_equals':
            return MetaConstraint(constraint_type=c_type, key=key, value=_value_from_dict(d, 'value'))
        elif c_type == 'string_equals':
            return MetaConstraint(constraint_type=c_type, key=key, value=_string_from_dict(d, 'value'))
        else:
            raise ValueError("Unknown MetaConstraint constraint type!")


class Observation(ModelEqualityMixin):
    """
    Represents a single observation.

    :ivar string obstory_id:
        the string ID of the obstory which produced this observation.
    :ivar string obs_id:
        the unique Id of the observation.
    :ivar float obs_time:
        the unix time the observation was made.
    :ivar float creation_time:
        the unix time when this observation was created.
    :ivar integer published:
        flag indicating whether this observations has been published
    :ivar integer moderated:
        flag indicating whether this observation has been accepted by the moderators
    :ivar string obs_type:
        the type of observation. The type might be, for example 'still image' or 'moving object'. This is a
        string, and can take any arbitrary value.
    :ivar list[FileRecord] file_records:
        a list of zero or more :class:`obsarchive_model.FileRecord` objects. You can think of these as the supporting
        evidence for the other information in the observation.
    :ivar list[Meta] meta:
        a list of zero or more :class:`obsarchive_model.Meta` objects. Meta objects are used to provide arbitrary extra,
        searchable, information about the observation.
    """

    def __init__(
            self,
            obstory_id,
            obstory_name,
            obstory_owner,
            obs_time,
            obs_id,
            obs_type,
            creation_time,
            published,
            moderated,
            featured, ra, dec, field_width, field_height, position_angle, central_constellation, astrometry_processed,
            file_records=None,
            meta=None):
        """
        Constructor function. Note that typically you'd use the methods on the database to
        create a new Observation, or on the client API to retrieve an existing one. This constructor is only for
        internal use within the database layer.

        :param string obstory_id: Camera ID which is responsible for this observation
        :param string obstory_name: Name of the obstory which is responsible for this observation
        :param float obs_time: Date for the observation
        :param string obs_id: UUID for this observation
        :param string obs_type: string defining the observation type
        :param float creation_time: Date when this observation was created
        :param integer published: flag indicating whether this observations has been published
        :param integer moderated: flag indicating whether this observation has been accepted by the moderators
        :param featured:
            flag indicating whether this is a "featured" observation
        :param ra:
            Right ascension of the centre of the field, in hours.
        :param dec:
            Declination of the centre of the field, in degrees.
        :param field_width:
            Width of the field of view, in degrees.
        :param field_height:
            Height of the field of view, in degrees.
        :param position_angle:
            Position angle at the centre of the image, in degrees.
        :param central_constellation:
            Constellation where the centre of the image falls.
        :param astrometry_processed:
            Unix time when the astrometric coordinates of this image were (last) processed.
        :param list[FileRecord] file_records:
            A list of :class:`obsarchive_model.FileRecord`, or None to specify no files, which support the observation.
        :param list[Meta] meta:
            A list of :class:`obsarchive_model.Meta`, or None to specify an empty list, which provide additional
            information about the observation.
        """
        self.obstory_id = obstory_id
        self.obstory_name = obstory_name
        self.obstory_owner = obstory_owner
        self.id = self.obs_id = obs_id
        self.obs_time = obs_time
        self.obs_type = obs_type
        self.creation_time = creation_time
        self.published = published
        self.moderated = moderated
        self.featured = featured
        self.ra = ra
        self.dec = dec
        self.field_width = field_width
        self.field_height = field_height
        self.position_angle = position_angle
        self.central_constellation = central_constellation
        self.astrometry_processed = astrometry_processed
        self.likes = 0

        # Sequence of FileRecord
        if file_records is None:
            self.file_records = []
        else:
            self.file_records = file_records

        # Observation metadata
        if meta is None:
            self.meta = []
        else:
            self.meta = meta

    def __str__(self):
        return (
            'Observation(obstory_id={0}, obstory_name={1}, obstory_owner={2}, obs_time={3}, obs_id={4}, obs_type={5}, creation_time={6})'.format(
                self.obstory_id,
                self.obstory_name,
                self.obstory_owner,
                self.obs_time,
                self.obs_id,
                self.obs_type,
                self.creation_time
            )
        )

    def as_dict(self):
        return {'obstory_id': self.obstory_id,
                'id': self.id,
                'obstory_name': self.obstory_name,
                'obs_id': self.obs_id,
                'obstory_owner': self.obstory_owner,
                'obs_time': self.obs_time,
                'obs_type': self.obs_type,
                'creation_time': self.creation_time,
                'published': self.published,
                'moderated': self.moderated,
                'featured': self.featured,
                'ra': self.ra,
                'dec': self.dec,
                'field_width': self.field_width,
                'field_height': self.field_height,
                'position_angle': self.position_angle,
                'central_constellation': self.central_constellation,
                'astrometry_processed': self.astrometry_processed,
                'files': list(fr.as_dict() for fr in self.file_records),
                'meta': list(fm.as_dict() for fm in self.meta)}

    @staticmethod
    def from_dict(d):
        return Observation(obstory_id=_string_from_dict(d, 'obstory_id'),
                           obstory_name=_string_from_dict(d, 'obstory_name'),
                           obstory_owner=_string_from_dict(d, 'obstory_owner'),
                           obs_id=_string_from_dict(d, 'obs_id'),
                           obs_time=_value_from_dict(d, 'obs_time'),
                           obs_type=_string_from_dict(d, 'obs_type'),
                           creation_time=_value_from_dict(d, 'creation_time'),
                           published=_value_from_dict(d, 'published'),
                           moderated=_value_from_dict(d, 'moderated'),
                           featured=_value_from_dict(d, 'featured'),
                           ra=_value_from_dict(d, 'ra'),
                           dec=_value_from_dict(d, 'dec'),
                           field_width=_value_from_dict(d, 'field_width'),
                           field_height=_value_from_dict(d, 'field_height'),
                           position_angle=_value_from_dict(d, 'position_angle'),
                           central_constellation=_value_from_dict(d, 'central_constellation'),
                           astrometry_processed=_value_from_dict(d, 'astrometry_processed'),
                           file_records=list(FileRecord.from_dict(frd) for frd in d['files']),
                           meta=list((Meta.from_dict(m) for m in d['meta'])))


class FileRecord(ModelEqualityMixin):
    """
    Represents a single data file within an observation. You will typically not construct
    FileRecord instances yourself, rather using the search methods in the client, or (for internal use) the register
    methods in the database API.


    :ivar string obstory_id:
        String ID of the observatory which produced this file.
    :ivar string obstory_name:
        Name of the observatory which produced this file.
    :ivar string observation_id:
        Observation of which this file is a part
    :ivar string repository_fname:
        File name of the file in the repository.
    :ivar float file_time:
        Datetime the file was created on the obstory.
    :ivar int file_size:
        File size in bytes. A value of 0 means that the underlying file is not yet available, so it
        cannot be downloaded. This may happen if you are retrieving results from a central server which has received
        the information about a file from another system but has not yet received the actual file.
    :ivar string file_name:
        Optional, and can be None, this contains a suggested name for the file. This is used in the web
        interface to show the file name to download, but is not guaranteed to be unique (if you need a unique ID you
        should use the file_id)
    :ivar string mime_type:
        MIME type of the file, typically used to determine which application opens it. Values are
        strings like 'text/plain' and 'image/png'
    :ivar string semantic_type:
        Semantic type of the file. This defines the meaning of the contents (mime_type defining the
        format of the contents). This is a string, and can take any arbitrary value. You
        should consult the documentation for the particular project you're working with for more information on what
        might appear here.
    :ivar boolean primary_image:
        Flag indicating whether this is the primary image within this observation.
    :ivar string file_md5:
        The hex representation of the MD5 sum for the file, as computed by model.get_md5_hash()
    """

    def __init__(self, obstory_id, obstory_name, observation_id, repository_fname, file_time, file_size, file_name,
                 mime_type, semantic_type, primary_image=False, file_md5=None, meta=None):
        self.obstory_id = obstory_id
        self.obstory_name = obstory_name
        self.observation_id = observation_id
        self.id = self.repository_fname = repository_fname
        self.file_time = file_time
        self.file_size = file_size
        self.file_name = file_name
        self.mime_type = mime_type
        self.semantic_type = semantic_type
        self.primary_image = primary_image
        self.file_md5 = file_md5

        # Observation metadata
        if meta is None:
            self.meta = []
        else:
            self.meta = meta

    def __str__(self):
        return (
            'FileRecord(obstory_id={0}, obstory_name={1}, observation_id={2}, repository_fname={3}, file_time={4}, '
            'file_size={5}, file_name={6}, mime_type={7}, semantic_type={8}, file_md5={9}, primary_image={10}'.format(
                self.obstory_id,
                self.obstory_name,
                self.observation_id,
                self.repository_fname,
                self.file_time,
                self.file_size,
                self.file_name,
                self.mime_type,
                self.semantic_type,
                self.file_md5,
                self.primary_image))

    def as_dict(self):
        d = {}
        _add_string(d, 'id', self.id)
        _add_string(d, 'obstory_id', self.obstory_id)
        _add_string(d, 'obstory_name', self.obstory_name)
        _add_string(d, 'observation_id', self.observation_id)
        _add_string(d, 'repository_fname', self.repository_fname)
        _add_value(d, 'file_time', self.file_time)
        _add_value(d, 'file_size', self.file_size)
        _add_string(d, 'file_name', self.file_name)
        _add_string(d, 'mime_type', self.mime_type)
        _add_string(d, 'semantic_type', self.semantic_type)
        _add_value(d, 'primary_image', self.primary_image)
        _add_string(d, 'file_md5', self.file_md5)
        d['meta'] = list(fm.as_dict() for fm in self.meta)
        return d

    @staticmethod
    def from_dict(d):
        return FileRecord(
            obstory_id=_string_from_dict(d, 'obstory_id'),
            obstory_name=_string_from_dict(d, 'obstory_name'),
            observation_id=_string_from_dict(d, 'observation_id'),
            repository_fname=_string_from_dict(d, 'repository_fname'),
            file_time=_value_from_dict(d, 'file_time'),
            file_size=_value_from_dict(d, 'file_size'),
            file_name=_string_from_dict(d, 'file_name'),
            mime_type=_string_from_dict(d, 'mime_type'),
            semantic_type=_string_from_dict(d, 'semantic_type'),
            primary_image=_value_from_dict(d, 'primary_image'),
            file_md5=_string_from_dict(d, 'file_md5'),
            meta=list((Meta.from_dict(m) for m in d['meta']))
        )


class ObservatoryMetadata(ModelEqualityMixin):
    """
    Represents a piece of data about an observatory.

    :ivar string obstory_id:
        String ID of the observatory.
    :ivar string obstory_name:
        Name of the observatory.
    :ivar float obstory_lat:
        Latitude of the observatory (degrees north)
    :ivar float obstory_lng:
        Longitude of the observatory (degrees east)
    :ivar string key:
        Name of the metadata key.
    :ivar object value:
        Name of the metadata value.
    :ivar float metadata_time:
        Time the metadata is relevant to.
    :ivar float time_created:
        Time the metadata was computed
    :ivar string user_created:
        Username of the user who set this value
    """

    def __init__(self, metadata_id, obstory_id, obstory_name, obstory_lat, obstory_lng, key, value,
                 metadata_time, time_created, user_created):
        self.id = self.metadata_id = metadata_id
        self.obstory_id = obstory_id
        self.obstory_name = obstory_name
        self.obstory_lat = obstory_lat
        self.obstory_lng = obstory_lng
        self.key = key
        self.value = value
        self.time = metadata_time
        self.time_created = time_created
        self.user_created = user_created

    def type(self):
        """Returns 'number', 'string', 'date' or 'unknown' based on the type of the value"""
        if isinstance(self.value, numbers.Number):
            return "number"
        if isinstance(self.value, str):
            return "string"
        return "unknown"

    def __str__(self):
        return (
            'ObservatoryMetadata(metadata_id={9}, obstory_id={0}, obstory_name={1}, obstory_lat={2}, obstory_lng={3}, '
            'key={4}, value={5}, '
            'metadata_time={6}, time_created={7}, user_created={8}'.format(
                self.obstory_id,
                self.obstory_name,
                self.obstory_lat,
                self.obstory_lng,
                self.key,
                self.value,
                self.time,
                self.time_created,
                self.user_created,
                self.metadata_id))

    def as_dict(self):
        d = {}
        _add_string(d, 'id', self.id)
        _add_string(d, 'obstory_id', self.obstory_id)
        _add_string(d, 'obstory_name', self.obstory_name)
        _add_value(d, 'obstory_lat', self.obstory_lat)
        _add_value(d, 'obstory_lng', self.obstory_lng)
        _add_string(d, 'key', self.key)
        _add_value(d, 'time', self.time)
        _add_value(d, 'time_created', self.time_created)
        _add_string(d, 'user_created', self.user_created)
        _add_string(d, 'metadata_id', self.metadata_id)

        meta_type = self.type()
        _add_string(d, "type", meta_type)
        if meta_type == "number":
            _add_value(d, "value", self.value)
        elif meta_type == "string":
            _add_string(d, "value", self.value)
        return d

    @staticmethod
    def from_dict(d):
        if d['type'] == "string":
            v = _string_from_dict(d, "value")
        elif d['type'] == "number":
            v = _value_from_dict(d, "value")
        else:
            raise ValueError("Unknown meta value type")
        return ObservatoryMetadata(
            obstory_id=_string_from_dict(d, 'obstory_id'),
            obstory_name=_string_from_dict(d, 'obstory_name'),
            obstory_lat=_value_from_dict(d, 'obstory_lat'),
            obstory_lng=_value_from_dict(d, 'obstory_lng'),
            key=_string_from_dict(d, 'key'),
            value=v,
            metadata_time=_value_from_dict(d, 'time'),
            time_created=_value_from_dict(d, 'time_created'),
            user_created=_string_from_dict(d, 'user_created'),
            metadata_id=_string_from_dict(d, 'metadata_id')
        )


class Meta(ModelEqualityMixin):
    """
    A single piece of metadata pertaining to a FileRecord or an Observation.

    :ivar string key:
        Name of this metadata property, specified as an NSString
    :ivar object value:
        Value of this property, this can be a Number or string
    """

    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __str__(self):
        return '(key={0}, val={1})'.format(
            self.key,
            self.value)

    def type(self):
        """Returns 'number', 'string', 'date' or 'unknown' based on the type of the value"""
        if isinstance(self.value, numbers.Number):
            return "number"
        if isinstance(self.value, str):
            return "string"
        return "unknown"

    def string_value(self):
        if isinstance(self.value, str):
            return self.value
        return None

    def float_value(self):
        if isinstance(self.value, numbers.Number):
            return self.value
        return None

    def as_dict(self):
        d = {}
        meta_type = self.type()
        _add_string(d, "type", meta_type)
        _add_string(d, "key", self.key)
        if meta_type == "number":
            _add_value(d, "value", self.value)
        elif meta_type == "string":
            _add_string(d, "value", self.value)
        return d

    @staticmethod
    def from_dict(d):
        key = d['key']
        if d['type'] == "string":
            return Meta(key=key, value=_string_from_dict(d, "value"))
        elif d['type'] == "number":
            return Meta(key=key, value=_value_from_dict(d, "value"))
        else:
            raise ValueError("Unknown meta value type")


class ExportConfiguration(ModelEqualityMixin):
    """
    Defines an export configuration, comprising an :class:`obsarchive_model.ObservationSearch` or
    :class:`obsarchive_model.FileRecordSearch` defining a set of :class:`obsarchive_model.Observation` or
    :class:`obsarchive_model.FileRecord` objects respectively which should be exported, and the necessary information
    about the target, including its URL, user and password. Also carries a descriptive name and long description for
    management and a UUID for the configuration itself.

    :ivar string config_id:
        The external ID for this export configuration
    :ivar string target_url:
        The root URL of the importing API to which data should be pushed
    :ivar string user_id:
        The user ID that should be supplied as an auth header when pushing data to the importing API
    :ivar string password:
        The password that should be supplied as an auth header when pushing data to the importing API
    :ivar ObservationSearch|FileRecordSearch search:
        An class:`obsarchive_model.ObservationSearch` or class:`obsarchive_model.FileRecordSearch` which defines the
        :class:`obsarchive_model.Observation` or :class:`obsarchive_model.FileRecord` instances to export. Note
        that there are some properties of the search which will be overridden by the export system, most particularly
        searches will have exclude_incomplete and exclude_export_to set to True and the ID of this configuration so we
        don't create duplicate export jobs for any given target.
    :ivar string name:
        Short name for this export configuration
    :ivar string description:
        A longer free text description for this configuration
    :ivar Boolean enabled:
        True if this export configuration is enabled, False otherwise.
    :ivar string type:
        Set based on the type of the supplied search object, either to 'file' or 'observation' or 'metadata'.
    """

    def __init__(self, target_url, user_id, password, search, name, description, enabled=False, config_id=None):
        if search is None:
            raise ValueError("Search must not be None")

        self.id = self.config_id = config_id
        self.target_url = target_url
        self.user_id = user_id
        self.password = password
        self.search = search
        self.name = name
        self.description = description
        self.enabled = enabled
        if isinstance(self.search, FileRecordSearch):
            self.type = "file"
        elif isinstance(self.search, ObservationSearch):
            self.type = "observation"
        elif isinstance(self.search, ObservatoryMetadataSearch):
            self.type = "metadata"

    def as_dict(self):
        d = {}
        _add_string(d, 'id', self.id)
        _add_string(d, "type", self.type)
        _add_string(d, "config_id", self.config_id)
        _add_string(d, "target_url", self.target_url)
        _add_string(d, "user_id", self.user_id)
        _add_string(d, "password", self.password)
        d["search"] = self.search.as_dict()
        _add_string(d, "config_name", self.name)
        _add_string(d, "config_description", self.description)
        _add_boolean(d, "enabled", self.enabled, True)
        return d

    @staticmethod
    def from_dict(d):
        config_id = _string_from_dict(d, "config_id")
        target_url = _value_from_dict(d, "target_url")
        user_id = _value_from_dict(d, "user_id")
        password = _value_from_dict(d, "password")
        obj_type = _value_from_dict(d, "type")
        if obj_type == "file":
            search = FileRecordSearch.from_dict(d["search"])
        elif obj_type == "observation":
            search = ObservationSearch.from_dict(d["search"])
        elif obj_type == "metadata":
            search = ObservatoryMetadataSearch.from_dict(d["search"])
        else:
            raise ValueError("Unknown search type!")
        name = _value_from_dict(d, "config_name")
        description = _value_from_dict(d, "config_description")
        enabled = _boolean_from_dict(d, "enabled")
        return ExportConfiguration(config_id=config_id, target_url=target_url, user_id=user_id, password=password,
                                   search=search, name=name, description=description, enabled=enabled)


class ObservationGroup(ModelEqualityMixin):
    """
    Represents a group of observations with associated metadata.

    :ivar int group_id:
        the ID of this observation group.
    :ivar list[Observation] obs_records:
        a list of zero or more :class:`obsarchive_model.Observation` objects.
    :ivar list[Meta] meta:
        a list of zero or more :class:`obsarchive_model.Meta` objects. Meta objects are used to provide arbitrary extra,
        searchable, information about the group.
    """

    def __init__(self, group_id, title, obs_time, set_time, user_id, semantic_type,
                 obs_records=None, subgroups=None, meta=None):
        """
        Constructor function.

        :param int group_id: Camera ID which is responsible for this observation group
        :param list[Observation] obs_records:
            A list of :class:`obsarchive_model.Observation`, or None to specify no observations.
        :param list[ObservationGroup] subgroups:
            A list of :class:`obsarchive_model.ObservationGroup`, or None to specify no observations.
        :param list[Meta] meta:
            A list of :class:`obsarchive_model.Meta`, or None to specify an empty list, which provide additional
            information about the group.
        """
        self.id = self.group_id = group_id
        self.title = title
        self.obs_time = obs_time
        self.set_time = set_time
        self.user_id = user_id
        self.semantic_type = semantic_type

        # Sequence of Observations
        if obs_records is None:
            self.obs_records = []
        else:
            self.obs_records = obs_records

        # Sequence of subgroups
        if subgroups is None:
            self.group_records = []
        else:
            self.group_records = subgroups

        # Group metadata
        if meta is None:
            self.meta = []
        else:
            self.meta = meta

    def __str__(self):
        return 'ObservationGroup(group_id={0}, title={1}, obs_time={2}, set_time={3})'.format(self.group_id,
                                                                                              self.title,
                                                                                              self.obs_time,
                                                                                              self.set_time)

    def as_dict(self):
        return {'group_id': self.group_id,
                'id': self.id,
                'title': self.title,
                'obs_time': self.obs_time,
                'set_time': self.set_time,
                'user_id': self.user_id,
                'semantic_type': self.semantic_type,
                'observations': list(obs.as_dict() for obs in self.obs_records),
                'subgroups': list(group.as_dict() for group in self.group_records),
                'meta': list(fm.as_dict() for fm in self.meta)}

    @staticmethod
    def from_dict(d):
        return ObservationGroup(group_id=_string_from_dict(d, 'group_id'),
                                title=_string_from_dict(d, 'title'),
                                obs_time=_value_from_dict(d, 'obs_time'),
                                set_time=_value_from_dict(d, 'set_time'),
                                user_id=_value_from_dict(d, 'user_id'),
                                semantic_type=_string_from_dict(d, 'semantic_type'),
                                obs_records=list(Observation.from_dict(obs) for obs in d['observations']),
                                subgroups=list(ObservationGroup.from_dict(group) for group in d['subgroups']),
                                meta=list((Meta.from_dict(m) for m in d['meta'])))
