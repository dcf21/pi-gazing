# MeteorPi API module

class EventSearch:
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
        self.camera_ids = camera_ids
        self.lat_min = lat_min
        self.lat_max = lat_max
        self.long_min = long_min
        self.long_max = long_max
        self.after = after
        self.before = before


class Bezier:
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


class Event:
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


class FileRecord:
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
            'FileRecord(fileID={0} cameraID={1} mime={2} '
            'ns={3} stype={4} time={5} size={6} meta={7}'.format(
                self.file_id.hex,
                self.camera_id,
                self.mime_type,
                self.namespace,
                self.semantic_type,
                self.file_time,
                self.file_size,
                str([str(obj) for obj in self.meta])))


class FileMeta:
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


class Location:
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


class Orientation:
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


class CameraStatus:
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
