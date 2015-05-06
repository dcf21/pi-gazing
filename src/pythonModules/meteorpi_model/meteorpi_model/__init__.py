# MeteorPi API module
import uuid
import datetime
import time
from itertools import izip


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


class EventSearch(ModelEqualityMixin):
    """Encapsulates the possible parameters which can be used to search for
    Event instances in the database.

    If parameters are set to None this means they won't be used to
    restrict the possible set of results.
    """

    def __init__(self, camera_ids=None, lat_min=None, lat_max=None, long_min=None, long_max=None, after=None,
                 before=None):
        if camera_ids is None == False and len(camera_ids) == 0:
            raise ValueError('If camera_ids is specified it must contain at least one ID')
        if lat_min is None == False and lat_max is None == False and lat_max < lat_min:
            raise ValueError('Latitude max cannot be less than latitude minimum')
        if long_min is None == False and long_max is None == False and long_max < long_min:
            raise ValueError('Longitude max cannot be less than longitude minimum')
        if after is None == False and before is None == False and before < after:
            raise ValueError('From time cannot be after before time')
        if isinstance(camera_ids, basestring):
            camera_ids = [camera_ids]
        self.camera_ids = camera_ids
        self.lat_min = lat_min
        self.lat_max = lat_max
        self.long_min = long_min
        self.long_max = long_max
        self.after = after
        self.before = before

    def as_dict(self):
        d = {}
        _add_value(d, 'camera_ids', self.camera_ids)
        _add_value(d, 'lat_min', self.lat_min)
        _add_value(d, 'lat_max', self.lat_max)
        _add_value(d, 'long_min', self.long_min)
        _add_value(d, 'long_max', self.long_max)
        _add_datetime(d, 'after', self.after)
        _add_datetime(d, 'before', self.before)
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
        return EventSearch(camera_ids, lat_min, lat_max, long_min, long_max, after, before)


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
                     file_records=(FileRecord.from_dict(frd) for frd in d['files']))


class FileRecord(ModelEqualityMixin):
    """A piece of binary data with associated metadata, typically used to store
    an image or video from the camera."""

    def __init__(self, camera_id, mime_type, namespace, semantic_type):
        self.camera_id = camera_id
        self.mime_type = mime_type
        self.namespace = namespace
        self.semantic_type = semantic_type
        self.meta = []
        self.file_id = None
        self.file_time = None
        self.file_size = 0

    def __str__(self):
        return (
            'FileRecord(file_id={0} camera_id={1} mime={2} '
            'ns={3} stype={4} time={5} size={6} meta={7}'.format(
                self.file_id.hex,
                self.camera_id,
                self.mime_type,
                self.namespace,
                self.semantic_type,
                self.file_time,
                self.file_size,
                str([str(obj) for obj in self.meta])))

    def as_dict(self):
        d = {}
        _add_uuid(d, 'file_id', self.file_id)
        _add_string(d, 'camera_id', self.camera_id)
        _add_string(d, 'mime_type', self.mime_type)
        _add_string(d, 'namespace', self.namespace)
        _add_datetime(d, 'file_time', self.file_time)
        _add_value(d, 'file_size', self.file_size)
        d['meta'] = list(
            {'namespace': fm.namespace, 'key': fm.key, 'string_value': fm.string_value} for fm in self.meta)
        return d

    @staticmethod
    def from_dict(d):
        fr = FileRecord(
            camera_id=_string_from_dict(d, 'camera_id'),
            mime_type=_string_from_dict(d, 'mime_type'),
            namespace=_string_from_dict(d, 'namespace'),
            semantic_type=_string_from_dict(d, 'semantic_type')
        )
        fr.file_size = int(_value_from_dict(d, 'file_size'))
        fr.file_time = _datetime_from_dict(d, 'file_time')
        fr.file_id = _uuid_from_dict(d, 'file_id')
        fr.meta = (FileMeta(m['namespace'], m['key'], m['string_value']) for m in d['meta'])
        return fr


class FileMeta(ModelEqualityMixin):
    """A single piece of metadata pertaining to a File."""

    def __init__(self, namespace, key, string_value):
        self.namespace = namespace
        self.key = key
        self.string_value = string_value

    def __str__(self):
        return '(ns={0}, key={1}, val={2})'.format(
            self.namespace,
            self.key,
            self.string_value)


class Location(ModelEqualityMixin):
    """A location fix, consisting of latitude and longitude, and a boolean to
    indicate whether the fix had a GPS lock or not."""

    def __init__(self, latitude=0.0, longitude=0.0, gps=False, certainty=0.0):
        self.latitude = latitude
        self.longitude = longitude
        self.gps = gps
        self.certainty = certainty

    def __str__(self):
        return '(lat={0}, long={1}, gps={2}, p={3})'.format(
            self.latitude,
            self.longitude,
            self.gps,
            self.certainty)


class Orientation(ModelEqualityMixin):
    """An orientation fix, consisting of altitude, azimuth and certainty.

    Certainty ranges from 0.0 to 1.0, where 0.0 means we have no idea
    where we're pointing and 1.0 is totally certain

    """

    def __init__(self, altitude=0.0, azimuth=0.0, certainty=0.0):
        self.altitude = altitude
        self.azimuth = azimuth
        self.certainty = certainty

    def __str__(self):
        return '(alt={0}, az={1}, p={2})'.format(
            self.altitude,
            self.azimuth,
            self.certainty)


class CameraStatus(ModelEqualityMixin):
    """Represents the status of a single camera for a range of times.

    The status is valid from the given validFrom datetime (inclusively),
    and up until before the given validTo datetime; if this is None then
    the status is current.

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
                         'certainty': self.location.certainty}
        d['orientation'] = {'alt': self.orientation.altitude,
                            'az': self.orientation.azimuth,
                            'certainty': self.orientation.certainty}
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
                                                  certainty=_value_from_dict(od, 'certainty')),
                          location=Location(latitude=_value_from_dict(ld, 'lat'),
                                            longitude=_value_from_dict(ld, 'long'), gps=_value_from_dict(ld, 'gps'),
                                            certainty=_value_from_dict(ld, 'certainty')))
        cs.valid_from = _datetime_from_dict(d, 'valid_from')
        cs.valid_to = _datetime_from_dict(d, 'valid_to')
        cs.software_version = _value_from_dict(d, 'software_version')
        cs.regions = d['regions']
        return cs
