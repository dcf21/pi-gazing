from unittest import TestCase
from datetime import datetime
import uuid

import meteorpi_model as model


class TestModel(TestCase):
    def __init__(self, *args, **kwargs):
        super(TestModel, self).__init__(*args, **kwargs)
        # Simple camera status
        self._status1 = model.CameraStatus(
            lens='a_lens',
            sensor='a_sensor',
            inst_url='http://foo.bar.com',
            inst_name='test installation',
            orientation=model.Orientation(
                altitude=0.5,
                azimuth=0.6,
                certainty=0.7),
            location=model.Location(
                latitude=20.0,
                longitude=30.0,
                gps=True,
                certainty=1.0))
        self._status1.add_region([0, 0, 100, 0, 0, 100])
        self._status1.add_region([100, 100, 100, 0, 0, 100])
        # File 1
        self._file1 = model.FileRecord(
            camera_id='aabbccddeeff',
            mime_type='foo/bar',
            namespace='meteorpi',
            semantic_type='test_file_1'
        )
        self._file1.file_size = 12345
        self._file1.file_time = datetime.now()
        self._file1.file_id = uuid.uuid4()
        self._file1.meta.append(model.FileMeta('meta_ns1', 'meta_key1', 'meta_value1'))
        self._file1.meta.append(model.FileMeta('meta_ns2', 'meta_key2', 'meta_value2'))
        # File 2
        self._file2 = model.FileRecord(
            camera_id='aabbccddeeff',
            mime_type='foo/bar',
            namespace='meteorpi',
            semantic_type='test_file_2'
        )
        self._file2.file_size = 67890
        self._file2.file_time = datetime.now()
        self._file2.file_id = uuid.uuid4()
        self._file2.meta.append(model.FileMeta('meta2_ns1', 'meta2_key1', 'meta2_value1'))
        self._file2.meta.append(model.FileMeta('meta2_ns2', 'meta2_key2', 'meta2_value2'))


    def test_search_serialisation(self):
        search1 = model.EventSearch(camera_ids=['aabbccddeeff', '001122334455'], lat_min=50, lat_max=51, long_min=10,
                                    long_max=11, after=datetime.now())
        self.assertDictEqual(
            search1.as_dict(),
            model.EventSearch.from_dict(search1.as_dict()).as_dict())

    def test_bezier_serialisation(self):
        bez = model.Bezier(0, 1, 2, 3, 4, 5, 6, 7)
        self.assertDictEqual(
            bez.as_dict(),
            model.Bezier.from_dict(bez.as_dict()).as_dict())

    def test_file_serialisation(self):
        self.assertDictEqual(
            self._file1.as_dict(),
            model.FileRecord.from_dict(self._file1.as_dict()).as_dict())

    def test_event_serialisation(self):
        e = model.Event(camera_id='aabbccddeeff',
                        event_id=uuid.uuid4(),
                        event_time=datetime.now(),
                        intensity=0.5,
                        bezier=model.Bezier(0, 1, 2, 3, 4, 5, 6, 7),
                        file_records=[self._file1, self._file2])
        self.assertDictEqual(e.as_dict(), model.Event.from_dict(e.as_dict()).as_dict())