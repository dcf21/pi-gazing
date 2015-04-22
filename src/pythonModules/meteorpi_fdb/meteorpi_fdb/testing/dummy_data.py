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


def add_dummy_file(db, camera, time, meta):
    """Add a dummy file to the specified DB"""
    tf = tempfile.mkstemp(suffix='.tmp', prefix='meteor_pi_test_')
    tf_path = tf[1]
    return db.register_file(camera_id=camera,
                            file_path=tf_path,
                            mime_type='text/plain',
                            namespace='meteor_pi',
                            semantic_type='test_file',
                            file_time=make_time(time),
                            file_metas=list(
                                model.FileMeta(namespace='meteor_pi_meta_{0}'.format(x),
                                               key='meta_key_{0}'.format(x),
                                               string_value='meta_value_{0}'.format(x)) for x
                                in range(meta)))


def add_dummy_event(db, camera, time, intensity, file_records=None, file_count=None):
    """Add a dummy event to the specified DB"""
    if file_records is None:
        file_records = []
        if file_count is not None:
            file_records = list(add_dummy_file(db=db, camera=camera, time=time, meta=x + 1) for x in range(file_count))
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
                     location_certainty=1.0,
                     altitude=0.5,
                     azimuth=0.6,
                     orientation_certainty=0.7):
    s = model.CameraStatus(lens='a_lens',
                           sensor='a_sensor',
                           inst_url='http://foo.bar.com',
                           inst_name='test installation',
                           orientation=model.Orientation(altitude=altitude, azimuth=azimuth,
                                                         certainty=orientation_certainty),
                           location=model.Location(latitude=latitude,
                                                   longitude=longitude,
                                                   gps=gps,
                                                   certainty=location_certainty))
    s.regions = [[{"x": 0, "y": 0}, {"x": region_size, "y": 0}, {"x": 0, "y": region_size}], [
        {"x": region_size, "y": region_size}, {"x": region_size, "y": 0}, {"x": 0, "y": region_size}]]
    db.update_camera_status(ns=s, time=make_time(time), camera_id=camera)


def setup_dummy_data(db, clear=False):
    if clear:
        db.clear_database()
    # Set up camera 1, available from time=1 onwards, location more certain at time=10
    add_dummy_status(db=db, camera=CAMERA_1, time=1, longitude=10, latitude=10, location_certainty=0.8)
    add_dummy_status(db=db, camera=CAMERA_1, time=10, longitude=10, latitude=10, location_certainty=1.0)
    # Add some events, one detected at time=6 and another at time=30
    add_dummy_event(db=db, camera=CAMERA_1, time=6, intensity=.5, file_count=2)
    add_dummy_event(db=db, camera=CAMERA_1, time=30, intensity=.9, file_count=4)
    # Add some other files, not associated to events. One at time=8 and another at time=21
    add_dummy_file(db=db, camera=CAMERA_1, time=8, meta=3)
    add_dummy_file(db=db, camera=CAMERA_1, time=21, meta=1)
    # Set up camera 2, available from time=10 onwards, location more certain at time=15
    add_dummy_status(db=db, camera=CAMERA_2, time=10, longitude=20, latitude=11, location_certainty=0.9)
    add_dummy_status(db=db, camera=CAMERA_2, time=10, longitude=20, latitude=11, location_certainty=1.0)
    # Add another few events for camera 2 at times 12, 15 and 40
    add_dummy_event(db=db, camera=CAMERA_2, time=12, intensity=.2, file_count=2)
    add_dummy_event(db=db, camera=CAMERA_2, time=15, intensity=.3, file_count=3)
    add_dummy_event(db=db, camera=CAMERA_2, time=40, intensity=.4, file_count=6)