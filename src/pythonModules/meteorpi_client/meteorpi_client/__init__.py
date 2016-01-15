import json

import urllib

from yaml import safe_load

import types
import requests
import meteorpi_model as model


def _to_encoded_string(o):
    """
    Build an encoded string suitable for use as a URL component. This includes double-escaping the string to
    avoid issues with escaped backslash characters being automatically converted by WSGI or, in some cases
    such as default Apache servers, blocked entirely.

    :param o: an object of any kind, if it has an as_dict() method this will be used, otherwise uses __dict__
    :return: an encoded string suitable for use as a URL component
    :internal:
    """
    _dict = o.__dict__
    if o.as_dict:
        _dict = o.as_dict()
    return urllib.quote_plus(urllib.quote_plus(json.dumps(obj=_dict, separators=(',', ':'))))


class MeteorClient(object):
    """Client for the Meteor Pi HTTP API. Use this to access a camera or central server."""

    def __init__(self, base_url):
        """
        Create a new Meteor Pi client, use this to access the data in your Meteor Pi server.

        :param base_url:
            the URL for the API. For a camera this will be the address of the camera with '/api/' added, so for example
            if your camera website is at 'https://myhost.com/camera' you'd use 'https://myhost.com/camera/api/' here.
            You might see a '#' symbol in your web browser address bar, ignore it and just use the bits of the URL
            before that point.
        :return: a configured instance of the Meteor Pi client
        """
        self.base_url = base_url

    def list_cameras(self):
        """
        Get the IDs of all cameras on this server with currently active status.

        :return: a sequence of strings containing camera IDs
        """
        response = requests.get(self.base_url + '/cameras').text
        return safe_load(response)['cameras']

    def get_camera_status(self, camera_id, status_time=None):
        """
        Get details of the specified camera's status

        :param string camera_id:
            a cameraID, as returned by list_cameras()
        :param datetime.datetime status_time:
            optional, if specified attempts to get the status for the given camera at a particular point in time
            specified as a datetime instance. This is useful if you want to retrieve the status of the camera at the
            time a given event or file was produced. If this is None or not specified the time is 'now'.
        :return:
            a :class:`meteorpi_model.CameraStatus` object, or None if there was either no camera found or the camera
            didn't have an active status at the specified time.
        """
        if status_time is None:
            response = requests.get(
                self.base_url + '/cameras/{0}/status'.format(camera_id))
        else:
            response = requests.get(
                self.base_url + '/cameras/{0}/status/{1}'.format(camera_id,
                                                                 str(model.utc_datetime_to_milliseconds(status_time))))
        if response.status_code == 200:
            d = safe_load(response.text)
            if 'status' in d:
                return model.CameraStatus.from_dict(d['status'])
        return None

    def search_events(self, search=None):
        """
        Search for files, returning a Event for each result. FileRecords within result Events have two additional
        methods patched into them, get_url() and download_to(file_name), which will retrieve the URL for the file
        content and download that content to a named file on disk, respectively.

        :param search:
            an instance of EventSearch - see the model docs for details on how to construct this
        :return:
            an object containing 'count' and 'events'. 'events' is a sequence of Event objects containing the results of
            the search, and 'count' is the total number of results which would be returned if no result limit was in
            place (i.e. if the number of Events in the 'events' part is less than 'count' you have more records which
            weren't returned because of a query limit. Note that the default query limit is 100).
        """
        if search is None:
            search = model.EventSearch()
        search_string = _to_encoded_string(search)
        response = requests.get(self.base_url + '/events/{0}'.format(search_string))
        response_object = safe_load(response.text)
        event_dicts = response_object['events']
        event_count = response_object['count']
        return {'count': event_count,
                'events': list((self._augment_event_files(e) for e in (model.Event.from_dict(d) for d in event_dicts)))}

    def search_files(self, search=None):
        """
        Search for files, returning a FileRecord for each result. FileRecords have two additional
        methods patched into them, get_url() and download_to(file_name), which will retrieve the URL for the file
        content and download that content to a named file on disk, respectively.

        :param FileRecordSearch search:
            an instance of :class:`meteorpi_model.FileRecordSearch` - see the model docs for details on how to construct
            this
        :return:
            an object containing 'count' and 'files'. 'files' is a sequence of FileRecord objects containing the
            results of the search, and 'count' is the total number of results which would be returned if no result limit
            was in place (i.e. if the number of FileRecords in the 'files' part is less than 'count' you have more
            records which weren't returned because of a query limit. Note that the default query limit is 100).
        """
        if search is None:
            search = model.FileRecordSearch()
        search_string = _to_encoded_string(search)
        response = requests.get(self.base_url + '/files/{0}'.format(search_string))
        response_object = safe_load(response.text)
        file_dicts = response_object['files']
        file_count = response_object['count']
        return {'count': file_count,
                'files': list((self._augment_file(f) for f in (model.FileRecord.from_dict(d) for d in file_dicts)))}

    def _augment_file(self, f):
        """
        Augment a FileRecord with methods to get the data URL and to download, returning the updated file for use
        in generator functions
        :internal:
        """

        def get_url(target):
            if target.file_size is None:
                return None
            if target.file_name is not None:
                return self.base_url + '/files/content/{0}/{1}'.format(target.file_id.hex, target.file_name)
            else:
                return self.base_url + '/files/content/{0}'.format(target.file_id.hex, )

        f.get_url = types.MethodType(get_url, f)

        def download_to(target, file_name):
            url = target.get_url()
            r = requests.get(url, stream=True)
            with open(file_name, 'wb') as file_to_write:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:  # filter out keep-alive new chunks
                        file_to_write.write(chunk)
                        file_to_write.flush()
            return file_name

        f.download_to = types.MethodType(download_to, f)
        return f

    def _augment_event_files(self, e):
        """
        Augment all the file records in an event
        :internal:
        """
        e.file_records = list(self._augment_file(f) for f in e.file_records)
        return e
