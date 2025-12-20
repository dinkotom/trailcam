import unittest
import datetime
import pytz
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import utils

class TestTrailcamUtils(unittest.TestCase):
    def setUp(self):
        self.cet = pytz.timezone('Europe/Prague')

    def test_location_mapping(self):
        self.assertEqual(utils.get_location_from_subject("NOVA detected"), "Nová")
        self.assertEqual(utils.get_location_from_subject("Motion at CHECHLUVKA"), "Chechlůvka")
        self.assertEqual(utils.get_location_from_subject("Random Subject"), "Neznámá lokace")
        self.assertEqual(utils.get_location_from_subject("motion DUB 123"), "Dub")

    def test_service_date_before_1500(self):
        # 19th Dec 14:00 CET -> Should function as 18th Dec logic shift
        dt = self.cet.localize(datetime.datetime(2025, 12, 19, 14, 0, 0))
        service_date = utils.get_service_date(dt)
        self.assertEqual(service_date, "2025-12-18")

    def test_service_date_at_1500(self):
        # 19th Dec 15:00 CET -> Starts 19th Dec logic shift
        dt = self.cet.localize(datetime.datetime(2025, 12, 19, 15, 0, 0))
        service_date = utils.get_service_date(dt)
        self.assertEqual(service_date, "2025-12-19")

    def test_service_date_after_1500(self):
        # 19th Dec 23:59 CET -> 19th Dec logic shift
        dt = self.cet.localize(datetime.datetime(2025, 12, 19, 23, 59, 0))
        service_date = utils.get_service_date(dt)
        self.assertEqual(service_date, "2025-12-19")

    def test_service_date_next_day_early(self):
        # 20th Dec 02:00 CET -> Still part of 19th Dec logical shift (until 14:59)
        dt = self.cet.localize(datetime.datetime(2025, 12, 20, 2, 0, 0))
        service_date = utils.get_service_date(dt)
        self.assertEqual(service_date, "2025-12-19")

if __name__ == '__main__':
    unittest.main()
