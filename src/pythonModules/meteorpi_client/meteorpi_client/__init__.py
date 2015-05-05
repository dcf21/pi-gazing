import requests
import time

from yaml import safe_load

import meteorpi_model as model


class MeteorClient():
    def __init__(self, base_url):
        self.base_url = base_url

    def list_cameras(self):
        response = requests.get(self.base_url + '/cameras').text
        return safe_load(response)['cameras']

    def get_camera_status(self, camera_id, time=None):
        if time is None:
            response = requests.get(
                self.base_url + '/cameras/{0}/status'.format(camera_id))
        else:
            response = requests.get(
                self.base_url + '/cameras/{0}/status/{1}'.format(camera_id, _datetime_string(time)))
        if response.status_code == 200:
            d = safe_load(response.text)
            if 'status' in d:
                return model.CameraStatus.from_dict(d['status'])
        return None


def _datetime_string(t):
    if t is not None:
        return str(time.mktime((t.year, t.month, t.day,
                                t.hour, t.minute, t.second,
                                -1, -1, -1)) + t.microsecond / 1e6)
    raise ValueError("Time t cannot be None")