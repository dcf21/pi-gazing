from datetime import datetime
import tempfile

import meteorpi_model as model


CAMERA_1 = 'aabbccddeeff'
CAMERA_2 = '001122334455'
CAMERA_3 = '667788990011'


def make_time(t):
    """Make a datetime from an integer, where 0 will be at 00:00,
       and other values will be the specified number of minutes in
       advance of that time"""
    return datetime(year=2015, month=4, day=1, hour=t / 60, minute=t % 60)


def add_dummy_file(db, camera, time, meta, semantic_type=model.NSString('test_file')):
    """Add a dummy file to the specified DB"""
    tf = tempfile.mkstemp(suffix='.tmp', prefix='meteor_pi_test_')
    tf_path = tf[1]
    db.set_high_water_mark(camera_id=camera, time=make_time(time), allow_rollback=False)
    return db.register_file(camera_id=camera,
                            file_path=tf_path,
                            mime_type='text/plain',
                            semantic_type=semantic_type,
                            file_time=make_time(time),
                            file_metas=list(
                                model.FileMeta(key=model.NSString('meta_key_{0}'.format(x)),
                                               string_value='meta_value_{0}'.format(x)) for x
                                in range(meta)))


def add_dummy_event(db, camera, time, intensity, file_records=None, file_count=None):
    """Add a dummy event to the specified DB"""
    if file_records is None:
        file_records = []
        if file_count is not None:
            file_records = list(add_dummy_file(db=db, camera=camera, time=time, meta=x + 1,
                                               semantic_type=model.NSString('event_test_file')) for x in
                                range(file_count))
    db.set_high_water_mark(camera_id=camera, time=make_time(time), allow_rollback=False)
    return db.register_event(camera_id=camera,
                             event_time=make_time(time),
                             intensity=intensity,
                             bezier=model.Bezier(0, 1, 2, 3, 4, 5, 6, 7),
                             file_records=file_records)


def add_dummy_status(db, camera, time,
                     region_size=100,
                     longitude=20,
                     latitude=30,
                     gps=True,
                     location_error=1.0,
                     altitude=0.5,
                     azimuth=0.6,
                     orientation_error=0.7,
                     orientation_rotation=1.0,
                     width_of_field=80.0):
    s = model.CameraStatus(lens='a_lens',
                           sensor='a_sensor',
                           inst_url='http://foo.bar.com',
                           inst_name='test installation',
                           orientation=model.Orientation(altitude=altitude, azimuth=azimuth,
                                                         error=orientation_error,
                                                         rotation=orientation_rotation,
                                                         width_of_field=width_of_field),
                           location=model.Location(latitude=latitude,
                                                   longitude=longitude,
                                                   gps=gps,
                                                   error=location_error))
    s.regions = [[{"x": 0, "y": 0}, {"x": region_size, "y": 0}, {"x": 0, "y": region_size}], [
        {"x": region_size, "y": region_size}, {"x": region_size, "y": 0}, {"x": 0, "y": region_size}]]
    db.update_camera_status(ns=s, time=make_time(time), camera_id=camera)
    return s


class DummyDataHelper():
    """Helper to resolve IDs for files and events back to names defined when setting up dummy data,
    used to allow for tests to verify that particular items are being returned even though object IDs
    will be different"""

    def __init__(self):
        self.files = {}
        self.events = {}

    def add_event(self, e, name=None):
        if name is None:
            name = 'e{0}'.format(len(self.events))
        self.events[e.event_id.hex] = name
        for index, file_record in enumerate(e.file_records):
            self.add_file(file_record, name=name + ':f{0}'.format(index))

    def add_file(self, f, name=None):
        if name is None:
            name = 'f{0}'.format(len(self.files))
        self.files[f.file_id.hex] = name

    def seq_to_string(self, s):
        if isinstance(s, basestring):
            s = [s]

        def _get_name(item):
            if isinstance(item, model.Event) and item.event_id.hex in self.events:
                return self.events[item.event_id.hex]
            elif isinstance(item, model.FileRecord) and item.file_id.hex in self.files:
                return self.files[item.file_id.hex]
            else:
                return 'UNKNOWN'

        sorted_strings = sorted(list(_get_name(x) for x in s))
        return ','.join(sorted_strings)


def setup_dummy_data(db, clear=False):
    h = DummyDataHelper()
    if clear:
        db.clear_database()
    # Set up camera 1, available from time=1 onwards, location more certain at time=10
    add_dummy_status(db=db, camera=CAMERA_1, time=1, longitude=10, latitude=10, location_error=12.8)
    add_dummy_status(db=db, camera=CAMERA_1, time=10, longitude=10, latitude=10, location_error=1.0)
    # Add some events, one detected at time=6 and another at time=30
    h.add_event(add_dummy_event(db=db, camera=CAMERA_1, time=6, intensity=.5, file_count=2))
    h.add_event(add_dummy_event(db=db, camera=CAMERA_1, time=30, intensity=.9, file_count=4))
    # Add some other files, not associated to events. One at time=8 and another at time=21
    h.add_file(add_dummy_file(db=db, camera=CAMERA_1, time=8, meta=3))
    h.add_file(add_dummy_file(db=db, camera=CAMERA_1, time=21, meta=1))
    # Set up camera 2, available from time=10 onwards, location more certain at time=15
    add_dummy_status(db=db, camera=CAMERA_2, time=10, longitude=20, latitude=11, location_error=3.9)
    add_dummy_status(db=db, camera=CAMERA_2, time=10, longitude=20, latitude=11, location_error=1.0)
    # Add another few events for camera 2 at times 12, 15 and 40
    h.add_event(add_dummy_event(db=db, camera=CAMERA_2, time=12, intensity=.2, file_count=2))
    h.add_event(add_dummy_event(db=db, camera=CAMERA_2, time=15, intensity=.3, file_count=3))
    h.add_event(add_dummy_event(db=db, camera=CAMERA_2, time=40, intensity=.4, file_count=6))
    return h