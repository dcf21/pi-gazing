from unittest import TestCase
from datetime import datetime

import meteorpi_model as model


class TestModel(TestCase):
    def __init__(self, *args, **kwargs):
        super(TestModel, self).__init__(*args, **kwargs)
        # Do other setup stuff if needed

    def test_search_serialisation(self):
        search1 = model.EventSearch(camera_ids=['aabbccddeeff', '001122334455'], lat_min=50, lat_max=51, long_min=10,
                                    long_max=11, after=datetime.now())
        print search1.as_dict()
        self.assertEqual(
            str(model.EventSearch.from_dict(search1.as_dict()).__dict__),
            str(search1.__dict__))

    def test_bezier_serialisation(self):
        bez = model.Bezier(0, 1, 2, 3, 4, 5, 6, 7)
        print bez.as_dict()
        self.assertEqual(
            str(model.Bezier.from_dict(bez.as_dict()).__dict__),
            str(bez.__dict__))