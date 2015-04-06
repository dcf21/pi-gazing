# MeteorPi API module
from datetime import datetime


class FileRecord:

    """A piece of binary data with associated metadata, typically used to store
    an image or video from the camera."""

    def __init__(self, cameraID, mimeType, namespace, semanticType):
        self.cameraID = cameraID
        self.mimeType = mimeType
        self.namespace = namespace
        self.semanticType = semanticType
        self.meta = []

    def __str__(self):
        return(
            'FileRecord(fileID={0} cameraID={1} mime={2} '
            'ns={3} stype={4} time={5} size={6} meta={7}'.format(
                self.fileID.hex,
                self.cameraID,
                self.mimeType,
                self.namespace,
                self.semanticType,
                self.fileTime,
                self.fileSize,
                str([str(obj) for obj in self.meta])))


class FileMeta:

    """A single piece of metadata pertaining to a File."""

    def __init__(self, namespace, key, stringValue):
        self.namespace = namespace
        self.key = key
        self.stringValue = stringValue

    def __str__(self):
        return '(ns={0}, key={1}, val={2})'.format(
            self.namespace,
            self.key,
            self.stringValue)


class Location:

    """A location fix, consisting of latitude and longitude, and a boolean to
    indicate whether the fix had a GPS lock or not."""

    def __init__(self, latitude=0.0, longitude=0.0, gps=False):
        self.latitude = latitude
        self.longitude = longitude
        self.gps = gps

    def __str__(self):
        return '(lat={0}, long={1}, gps={2})'.format(
            self.latitude,
            self.longitude,
            self.gps)


class Orientation:

    """
    An orientation fix, consisting of altitude, azimuth and certainty.

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

    """
    Represents the status of a single camera for a range of times.

    The status is valid from the given validFrom datetime (inclusively),
    and up until before the given validTo datetime; if this is None then
    the status is current.
    """

    def __init__(self, lens, sensor, instURL, instName, orientation, location):
        self.lens = lens
        self.sensor = sensor
        self.instURL = instURL
        self.instName = instName
        self.orientation = orientation
        self.location = location
        self.softwareVersion = 1
        self.validFrom = None
        self.validTo = None
        self.regions = []

    def __str__(self):
        return (
            'CameraStatus(location={0}, orientation={1}, validFrom={2},'
            'validTo={3}, version={4}, lens={5}, sensor={6}, regions={7})'.format(
                self.location,
                self.orientation,
                self.validFrom,
                self.validTo,
                self.softwareVersion,
                self.lens,
                self.sensor,
                self.regions))
