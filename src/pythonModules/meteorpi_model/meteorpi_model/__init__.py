# MeteorPi API module
import uuid
import datetime
import time
from itertools import izip
import numbers


def _string_from_dict(d, key):
    if key in d:
        return str(d[key])
    else:
        return None


def _uuid_from_dict(d, key):
    if key in d:
        return uuid.UUID(hex=str(d[key]))
    else:
        return None


def _datetime_from_dict(d, key):
    if key in d:
        return datetime.datetime.fromtimestamp(timestamp=d[key])
    else:
        return None


def _value_from_dict(d, key):
    if key in d:
        return d[key]
    else:
        return None


def _add_string(d, key, value):
    if value is not None:
        d[key] = str(value)


def _add_uuid(d, key, uuid_value):
    if uuid_value is not None:
        d[key] = uuid_value.hex


def _add_datetime(d, key, datetime_value):
    if datetime_value is not None:
        d[key] = time.mktime((datetime_value.year, datetime_value.month, datetime_value.day,
                              datetime_value.hour, datetime_value.minute, datetime_value.second,
                              -1, -1, -1)) + datetime_value.microsecond / 1e6


def _add_value(d, key, value):
    if value is not None:
        d[key] = value


class ModelEqualityMixin():
    """Taken from http://stackoverflow.com/questions/390250/"""

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


class NSString(ModelEqualityMixin):
    """Namespace prefixed string, with the namespace defaulting to 'meteorpi'"""

    def __init__(self, s, ns='meteorpi'):
        """
        Create a new namespaced string
        :param s: The value part of the string object.
        :param ns: The namespace, optional, defaults to 'meteorpi' if not specified.
        :return: the new NSString instance
        """
        if ':' in ns:
            raise ValueError('Namespace part must not contain the : character.')
        if len(s) == 0:
            raise ValueError('String part cannot be empty.')
        if len(ns) == 0:
            raise ValueError('Namespace part cannot be empty.')
        self.s = s
        self.ns = ns

    def __str__(self):
        """Returns the stringified form of the NSString for storage etc, the format will be ns:value"""
        return '{0}:{1}'.format(self.ns, self.s)

    @staticmethod
    def from_string(s):
        """Strings are stored as ns:s in the database, this method parses them back to NSString instances"""
        if s is None:
            return None
        split = s.split(':', 1)
        return NSString(s=split[1], ns=split[0])


class FileRecordSearch(ModelEqualityMixin):
    """Encapsulates the possible parameters which can be used to search for FileRecord instances"""

    def __init__(self, camera_ids=None, lat_min=None, lat_max=None, long_min=None, long_max=None, after=None,
                 before=None, mime_type=None, semantic_type=None, exclude_events=False, latest=False, after_offset=None,
                 before_offset=None, meta_constraints=[]):
        """
        :param camera_ids: Optional - if specified, restricts results to only those the the specified camera IDs. This
            can be specified as an array or a single item (the latter being equivalent to a single item array). Note
            that due to the internal database structure one database query is required per camera ID specified.
        :param lat_min: Optional - if specified, only returns results where the camera status at the time of the file
            had a latitude field of at least the specified value.
        :param lat_max: Optional - if specified, only returns results where the camera status at the time of the file
            had a latitude field of at most the specified value.
        :param long_min: Optional - if specified, only returns results where the camera status at the time of the file
            had a longitude field of at least the specified value.
        :param long_max: Optional - if specified, only returns results where the camera status at the time of the file
            had a longitude field of at most the specified value.
        :param after: Optional - if specified, only returns results where the file time is after the specified value.
        :param before: Optional - if specified, only returns results where the file time is before the specified value.
        :param mime_type: Optional - if specified, only returns results where the MIME type exactly matches the
            specified value.
        :param semantic_type: Optional - if specified, only returns results where the semantic type exactly matches.
            The type of this value should be an instance of NSString
        :param exclude_events: Optional - if True then files associated with an Event will be excluded from the results,
            otherwise files will be included whether they are associated with an Event or not.
        :param latest: Optional - if True then only the latest file will be returned rather than all matching files.
            This complicates the internal querying process, but might be useful when your result set would otherwise
            be unreasonably large and you only actually want the latest (in terms of file time) result.
        :param after_offset: Optional - if specified this defines a lower bound on the time of day of the file time,
            irrespective of the date of the file. This can be used to e.g. only return files which were produced after
            2am on any given day. Specified as seconds since the previous mid-day.
        :param before_offset: Optional - interpreted in a similar manner to after_offset but specifies an upper bound.
            Use both in the same query to filter for a particular range, i.e. 2am to 4am on any day.
        :param meta_constraints: Optional - a list of FileMetaConstraint objects providing restrictions over the file
            record metadata.
        :return:
        """
        if camera_ids is None == False and len(camera_ids) == 0:
            raise ValueError('If camera_ids is specified it must contain at least one ID')
        if lat_min is None == False and lat_max is None == False and lat_max < lat_min:
            raise ValueError('Latitude max cannot be less than latitude minimum')
        if long_min is None == False and long_max is None == False and long_max < long_min:
            raise ValueError('Longitude max cannot be less than longitude minimum')
        if after is None == False and before is None == False and before < after:
            raise ValueError('From time cannot be after before time')
        if after_offset is None == False and before_offset is None == False and before_offset < after_offset:
            raise ValueError('From offset cannot be after before offset')
        if isinstance(camera_ids, basestring):
            camera_ids = [camera_ids]
        self.camera_ids = camera_ids
        self.lat_min = lat_min
        self.lat_max = lat_max
        self.long_min = long_min
        self.long_max = long_max
        self.after = after
        self.before = before
        self.after_offset = after_offset
        self.before_offset = before_offset
        self.mime_type = mime_type
        # NSString here
        self.semantic_type = semantic_type
        # Boolean, set to true to prevent files associated with events from appearing in the results
        self.exclude_events = exclude_events
        # Boolean, set to true to only return the latest file or files matched by the other criteria
        self.latest = latest
        # FileMeta constraints
        self.meta_constraints = meta_constraints

    def __str__(self):
        fields = []
        for field in self.__dict__:
            if self.__dict__[field] is not None:
                fields.append({'name': field, 'value': self.__dict__[field]})
        return '{0}[{1}]'.format(self.__class__.__name__,
                                 ','.join(('{0}=\'{1}\''.format(x['name'], str(x['value'])) for x in fields)))

    def as_dict(self):
        d = {}
        _add_value(d, 'camera_ids', self.camera_ids)
        _add_value(d, 'lat_min', self.lat_min)
        _add_value(d, 'lat_max', self.lat_max)
        _add_value(d, 'long_min', self.long_min)
        _add_value(d, 'long_max', self.long_max)
        _add_datetime(d, 'after', self.after)
        _add_datetime(d, 'before', self.before)
        _add_value(d, 'after_offset', self.after_offset)
        _add_value(d, 'before_offset', self.before_offset)
        _add_string(d, 'mime_type', self.mime_type)
        if self.semantic_type is not None:
            _add_string(d, 'semantic_type', str(self.semantic_type))
        if self.exclude_events:
            d['exclude_events'] = 1
        if self.latest:
            d['latest'] = 1
        d['meta_constraints'] = list((x.as_dict() for x in self.meta_constraints))
        return d

    @staticmethod
    def from_dict(d):
        camera_ids = _value_from_dict(d, 'camera_ids')
        lat_min = _value_from_dict(d, 'lat_min')
        lat_max = _value_from_dict(d, 'lat_max')
        long_min = _value_from_dict(d, 'long_min')
        long_max = _value_from_dict(d, 'long_max')
        after = _datetime_from_dict(d, 'after')
        before = _datetime_from_dict(d, 'before')
        after_offset = _value_from_dict(d, 'after_offset')
        before_offset = _value_from_dict(d, 'before_offset')
        mime_type = _string_from_dict(d, 'mime_type')
        semantic_type = NSString.from_string(_string_from_dict(d, 'semantic_type'))
        if 'meta_constraints' in d:
            meta_constraints = list((FileMetaConstraint.from_dict(x) for x in d['meta_constraints']))
        else:
            meta_constraints = []
        return FileRecordSearch(camera_ids=camera_ids, lat_min=lat_min, lat_max=lat_max, long_min=long_min,
                                long_max=long_max, after=after, before=before, after_offset=after_offset,
                                before_offset=before_offset, mime_type=mime_type,
                                semantic_type=semantic_type,
                                exclude_events='exclude_events' in d and d['exclude_events'],
                                latest='latest' in d and d['latest'],
                                meta_constraints=meta_constraints)


class FileMetaConstraint(ModelEqualityMixin):
    """Defines a constraint over FileMeta"""

    def __init__(self, constraint_type, key, value):
        """
        Constructor
        :param constraint_type: one of 'before', 'after', 'string_equals', 'number_equals', 'less', 'greater'
        :param key: an NSString containing the namespace prefixed string to use as a key
        :param value: the value, for string_equals this is a string, for 'before' and 'after' it's a DateTime and
            for 'less', 'greater' and 'number_equals' a number.
        :return: the instance of FileMetaConstraint
        """
        self.constraint_type = constraint_type
        self.key = key
        self.value = value

    def as_dict(self):
        c_type = self.constraint_type
        d = {'key': str(self.key),
             'type': c_type};
        if c_type == 'after' or c_type == 'before':
            _add_datetime(d, 'value', self.value)
        elif c_type == 'less' or c_type == 'greater' or c_type == 'number_equals':
            _add_value(d, 'value', self.value)
        elif c_type == 'string_equals':
            _add_string(d, 'value', self.value)
        else:
            raise ValueError("Unknown FileMetaConstraint constraint type!")
        return d;

    @staticmethod
    def from_dict(d):
        c_type = _string_from_dict(d, 'type')
        key = NSString.from_string(_string_from_dict(d, 'key'))
        if c_type == 'after' or c_type == 'before':
            return FileMetaConstraint(constraint_type=c_type, key=key, value=_datetime_from_dict(d, 'value'))
        elif c_type == 'less' or c_type == 'greater' or c_type == 'number_equals':
            return FileMetaConstraint(constraint_type=c_type, key=key, value=_value_from_dict(d, 'value'))
        elif c_type == 'string_equals':
            return FileMetaConstraint(constraint_type=c_type, key=key, value=_string_from_dict(d, 'value'))
        else:
            raise ValueError("Unknown FileMetaConstraint constraint type!")


class EventSearch(ModelEqualityMixin):
    """Encapsulates the possible parameters which can be used to search for
    Event instances in the database.

    If parameters are set to None this means they won't be used to
    restrict the possible set of results.
    """

    def __init__(self, camera_ids=None, lat_min=None, lat_max=None, long_min=None, long_max=None, after=None,
                 before=None, after_offset=None, before_offset=None):
        if camera_ids is None == False and len(camera_ids) == 0:
            raise ValueError('If camera_ids is specified it must contain at least one ID')
        if lat_min is None == False and lat_max is None == False and lat_max < lat_min:
            raise ValueError('Latitude max cannot be less than latitude minimum')
        if long_min is None == False and long_max is None == False and long_max < long_min:
            raise ValueError('Longitude max cannot be less than longitude minimum')
        if after is None == False and before is None == False and before < after:
            raise ValueError('From time cannot be after before time')
        if after_offset is None == False and before_offset is None == False and before_offset < after_offset:
            raise ValueError('From offset cannot be after before offset')
        if isinstance(camera_ids, basestring):
            camera_ids = [camera_ids]
        self.camera_ids = camera_ids
        self.lat_min = lat_min
        self.lat_max = lat_max
        self.long_min = long_min
        self.long_max = long_max
        self.after = after
        self.before = before
        self.after_offset = after_offset
        self.before_offset = before_offset

    def __str__(self):
        fields = []
        for field in self.__dict__:
            if self.__dict__[field] is not None:
                fields.append({'name': field, 'value': self.__dict__[field]})
        return '{0}[{1}]'.format(self.__class__.__name__,
                                 ','.join(('{0}=\'{1}\''.format(x['name'], str(x['value'])) for x in fields)))

    def as_dict(self):
        d = {}
        _add_value(d, 'camera_ids', self.camera_ids)
        _add_value(d, 'lat_min', self.lat_min)
        _add_value(d, 'lat_max', self.lat_max)
        _add_value(d, 'long_min', self.long_min)
        _add_value(d, 'long_max', self.long_max)
        _add_datetime(d, 'after', self.after)
        _add_datetime(d, 'before', self.before)
        _add_value(d, 'after_offset', self.after_offset)
        _add_value(d, 'before_offset', self.before_offset)
        return d

    @staticmethod
    def from_dict(d):
        camera_ids = _value_from_dict(d, 'camera_ids')
        lat_min = _value_from_dict(d, 'lat_min')
        lat_max = _value_from_dict(d, 'lat_max')
        long_min = _value_from_dict(d, 'long_min')
        long_max = _value_from_dict(d, 'long_max')
        after = _datetime_from_dict(d, 'after')
        before = _datetime_from_dict(d, 'before')
        after_offset = _value_from_dict(d, 'after_offset')
        before_offset = _value_from_dict(d, 'before_offset')
        return EventSearch(camera_ids=camera_ids, lat_min=lat_min, lat_max=lat_max, long_min=long_min,
                           long_max=long_max, after=after, before=before, after_offset=after_offset,
                           before_offset=before_offset)


class Bezier(ModelEqualityMixin):
    """A four-point two dimensional curve, consisting of four control
    points."""

    def __init__(self, x1, y1, x2, y2, x3, y3, x4, y4):
        self.points = []
        self.points.append({"x": x1, "y": y1})
        self.points.append({"x": x2, "y": y2})
        self.points.append({"x": x3, "y": y3})
        self.points.append({"x": x4, "y": y4})

    def __str__(self):
        return str(self.points)

    def __getitem__(self, index):
        return self.points[index]

    def as_dict(self):
        return {'x1': self.points[0]['x'], 'y1': self.points[0]['y'],
                'x2': self.points[1]['x'], 'y2': self.points[1]['y'],
                'x3': self.points[2]['x'], 'y3': self.points[2]['y'],
                'x4': self.points[3]['x'], 'y4': self.points[3]['y']}

    @staticmethod
    def from_dict(d):
        return Bezier(d['x1'], d['y1'], d['x2'], d['y2'], d['x3'], d['y3'], d['x4'], d['y4'])


class Event(ModelEqualityMixin):
    """A single meteor observation, containing a set of data from the image
    processing tools and zero or more files containing images, video or any
    other appropriate information to support the event."""

    def __init__(
            self,
            camera_id,
            event_time,
            event_id,
            intensity,
            bezier,
            file_records=None):
        self.camera_id = camera_id
        # Will be a uuid.UUID when stored in the database
        self.event_id = event_id
        self.event_time = event_time
        self.intensity = intensity
        self.bezier = bezier
        # Sequence of FileRecord
        if file_records is None:
            self.file_records = []
        else:
            self.file_records = file_records

    def __str__(self):
        return (
            'Event(camera_id={0}, event_id={1}, time={2})'.format(
                self.camera_id,
                self.event_id,
                self.event_time
            )
        )

    def as_dict(self):
        d = {}
        _add_uuid(d, 'event_id', self.event_id)
        _add_value(d, 'camera_id', self.camera_id)
        _add_datetime(d, 'event_time', self.event_time)
        _add_value(d, 'intensity', self.intensity)
        d['bezier'] = self.bezier.as_dict()
        d['files'] = list(fr.as_dict() for fr in self.file_records)
        return d

    @staticmethod
    def from_dict(d):
        return Event(camera_id=_value_from_dict(d, 'camera_id'),
                     event_id=_uuid_from_dict(d, 'event_id'),
                     event_time=_datetime_from_dict(d, 'event_time'),
                     intensity=_value_from_dict(d, 'intensity'),
                     bezier=Bezier.from_dict(d['bezier']),
                     file_records=list(FileRecord.from_dict(frd) for frd in d['files']))


class FileRecord(ModelEqualityMixin):
    """A piece of binary data with associated metadata, typically used to store
    an image or video from the camera."""

    def __init__(self, camera_id, mime_type, semantic_type, file_name=None):
        self.camera_id = camera_id
        self.mime_type = mime_type
        # NSString value
        self.semantic_type = semantic_type
        self.meta = []
        self.file_id = None
        self.file_time = None
        self.file_size = 0
        self.file_name = file_name

    def __str__(self):
        return (
            'FileRecord(file_id={0} camera_id={1} mime={2} '
            'stype={3} time={4} size={5} meta={6}, name={7}'.format(
                self.file_id.hex,
                self.camera_id,
                self.mime_type,
                self.semantic_type,
                self.file_time,
                self.file_size,
                str([str(obj) for obj in self.meta]),
                self.file_name))

    def as_dict(self):
        d = {}
        _add_uuid(d, 'file_id', self.file_id)
        _add_string(d, 'camera_id', self.camera_id)
        _add_string(d, 'mime_type', self.mime_type)
        _add_string(d, 'file_name', self.file_name)
        _add_string(d, 'semantic_type', str(self.semantic_type))
        _add_datetime(d, 'file_time', self.file_time)
        _add_value(d, 'file_size', self.file_size)
        d['meta'] = list(fm.as_dict() for fm in self.meta)
        return d

    @staticmethod
    def from_dict(d):
        fr = FileRecord(
            camera_id=_string_from_dict(d, 'camera_id'),
            mime_type=_string_from_dict(d, 'mime_type'),
            semantic_type=NSString.from_string(_string_from_dict(d, 'semantic_type'))
        )
        fr.file_size = int(_value_from_dict(d, 'file_size'))
        fr.file_time = _datetime_from_dict(d, 'file_time')
        fr.file_id = _uuid_from_dict(d, 'file_id')
        fr.file_name = _string_from_dict(d, 'file_name')
        fr.meta = (FileMeta.from_dict(m) for m in d['meta'])
        return fr


class FileMeta(ModelEqualityMixin):
    """A single piece of metadata pertaining to a File."""

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
        if isinstance(self.value, basestring):
            return "string"
        if isinstance(self.value, datetime.date):
            return "date"
        return "unknown"

    def string_value(self):
        if isinstance(self.value, basestring):
            return self.value;
        return None

    def date_value(self):
        if isinstance(self.value, datetime.date):
            return self.value;
        return None

    def float_value(self):
        if isinstance(self.value, numbers.Number):
            return self.value;
        return None

    def as_dict(self):
        d = {}
        type = self.type()
        _add_string(d, "type", type)
        _add_string(d, "key", self.key)
        if type == "date":
            _add_datetime(d, "value", self.value)
        elif type == "number":
            _add_value(d, "value", self.value)
        elif type == "string":
            _add_string(d, "value", self.value)
        return d;

    @staticmethod
    def from_dict(d):
        key = d['key']
        if d['type'] == "date":
            return FileMeta(key=key, value=_datetime_from_dict(d, "value"))
        elif d['type'] == "string":
            return FileMeta(key=key, value=_string_from_dict(d, "value"))
        elif d['type'] == "number":
            return FileMeta(key=key, value=_value_from_dict(d, "value"))
        else:
            raise ValueError("Unknown filemeta value type")


class Location(ModelEqualityMixin):
    """A location fix, consisting of latitude and longitude, and a boolean to
    indicate whether the fix had a GPS lock or not.

    Instance properties:
        latitude -- Latitude of the camera installation, measured in degrees. Positive angles are north of equator,
            negative angles are south.
        longitude -- Longitude of the camera installation, measured in degrees. Positive angles are east of Greenwich,
            negative angles are west.
        gps -- True if the location was identified by GPS, False otherwise.
        error -- estimate of error in longitude and latitude values, expressed in meters.
    """

    def __init__(self, latitude=0.0, longitude=0.0, gps=False, error=0.0):
        self.latitude = latitude
        self.longitude = longitude
        self.gps = gps
        self.error = error

    def __str__(self):
        return '(lat={0}, long={1}, gps={2}, error={3})'.format(
            self.latitude,
            self.longitude,
            self.gps,
            self.error)


class Orientation(ModelEqualityMixin):
    """An orientation fix, consisting of altitude, azimuth, certainty.

    The angles, including the error, are floating point quantities with degrees as the unit. These values are computed
    from astrometry.net, so use documentation there as supporting material when interpreting instances of this class.

    Instance properties:
        altitude -- Angle above the horizon of the centre of the camera's field of view. 0 means camera is pointing
            horizontally, 90 means camera is pointing vertically upwards.
        azimuth -- Bearing of the centre of the camera's field of view, measured eastwards from north. 0 means camera
            pointing north, 90 east, 180 south, 270 west.
        rotation -- Position angle of camera's field of view (measured at centre of frame). 0 = celestial north up,
            90 = celestial east up, 270 = celestial west up.
        error -- estimate of likely error in altitude, azimuth and rotation values, expressed in degrees.
        width_of_field -- For a frame of dimensions (w,h), the angular distance between the pixels (0,h/2) and
            (w/2,h/2). That is, half the angular *width* of the frame.
    """

    def __init__(self, altitude=0.0, azimuth=0.0, error=0.0, rotation=0.0, width_of_field=0.0):
        self.altitude = altitude
        self.azimuth = azimuth
        self.error = error
        self.rotation = rotation
        self.width_of_field = width_of_field

    def __str__(self):
        return '(alt={0}, az={1}, rot={2}, error={3}, width={4})'.format(
            self.altitude,
            self.azimuth,
            self.rotation,
            self.error,
            self.width_of_field)


class CameraStatus(ModelEqualityMixin):
    """Represents the status of a single camera for a range of times.

    The status is valid from the given validFrom datetime (inclusively),
    and up until before the given validTo datetime; if this is None then
    the status is current.

    Instance properties:
        lens -- Name of the camera lens in use. This must match the name field of an entry in
            <sensorProperties/lenses.xml>
        sensor -- Name of the camera in use. This must match the name field of an entry in
            <sensorProperties/sensors.xml>
        inst_name -- Installation name, e.g. "Cambridge Secondary School, South Camera"
        inst_url -- Web address associated with installation, e.g. the school's website
        orientation -- An instance of class Orientation
        location -- An instance of class Location
        software_version -- ??
        regions -- List of list of dictionaries of the form {'x':x,'y':y}. The points in each list describe a polygon
            within which camera can see the sky.
        valid_from -- datetime object representing the earliest date of observation from which this camera status
            is valid
        valid_to -- datetime object representing the latest date of observation for which this camera status is valid

    """

    def __init__(self, lens, sensor, inst_url, inst_name, orientation, location):
        self.lens = lens
        self.sensor = sensor
        self.inst_url = inst_url
        self.inst_name = inst_name
        self.orientation = orientation
        self.location = location
        self.software_version = 1
        self.valid_from = None
        self.valid_to = None
        self.regions = []

    def __str__(self):
        return (
            'CameraStatus(location={0}, orientation={1}, validFrom={2},'
            'validTo={3}, version={4}, lens={5}, sensor={6}, regions={7})'.format(
                self.location,
                self.orientation,
                self.valid_from,
                self.valid_to,
                self.software_version,
                self.lens,
                self.sensor,
                self.regions))

    def add_region(self, r):
        a = iter(r)
        self.regions.append(list({'x': x, 'y': y} for x, y in izip(a, a)))

    def as_dict(self):
        d = {}
        _add_string(d, 'lens', self.lens)
        _add_string(d, 'sensor', self.sensor)
        _add_string(d, 'inst_url', self.inst_url)
        _add_string(d, 'inst_name', self.inst_name)
        _add_datetime(d, 'valid_from', self.valid_from)
        _add_datetime(d, 'valid_to', self.valid_to)
        _add_value(d, 'software_version', self.software_version)
        d['location'] = {'lat': self.location.latitude,
                         'long': self.location.longitude,
                         'gps': self.location.gps,
                         'error': self.location.error}
        d['orientation'] = {'alt': self.orientation.altitude,
                            'az': self.orientation.azimuth,
                            'error': self.orientation.error,
                            'rot': self.orientation.rotation,
                            'width': self.orientation.width_of_field}
        d['regions'] = self.regions
        return d

    @staticmethod
    def from_dict(d):
        od = d['orientation']
        ld = d['location']
        cs = CameraStatus(lens=_string_from_dict(d, 'lens'),
                          sensor=_string_from_dict(d, 'sensor'),
                          inst_url=_string_from_dict(d, 'inst_url'),
                          inst_name=_string_from_dict(d, 'inst_name'),
                          orientation=Orientation(altitude=_value_from_dict(od, 'alt'),
                                                  azimuth=_value_from_dict(od, 'az'),
                                                  error=_value_from_dict(od, 'error'),
                                                  rotation=_value_from_dict(od, 'rot'),
                                                  width_of_field=_value_from_dict(od, 'width')),
                          location=Location(latitude=_value_from_dict(ld, 'lat'),
                                            longitude=_value_from_dict(ld, 'long'),
                                            gps=_value_from_dict(ld, 'gps'),
                                            error=_value_from_dict(ld, 'error')))
        cs.valid_from = _datetime_from_dict(d, 'valid_from')
        cs.valid_to = _datetime_from_dict(d, 'valid_to')
        cs.software_version = _value_from_dict(d, 'software_version')
        cs.regions = d['regions']
        return cs
