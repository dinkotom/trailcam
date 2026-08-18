import unittest
import datetime
from zoneinfo import ZoneInfo
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import utils

class TestTrailcamUtils(unittest.TestCase):
    def setUp(self):
        self.cet = ZoneInfo('Europe/Prague')

    def test_location_mapping(self):
        self.assertEqual(utils.get_location_from_subject("NOVA detected"), "Nová")
        self.assertEqual(utils.get_location_from_subject("Motion at CHECHLUVKA"), "Chechlůvka")
        self.assertEqual(utils.get_location_from_subject("Random Subject"), "Neznámá lokace")
        self.assertEqual(utils.get_location_from_subject("motion DUB 123"), "Dub")

    def test_service_date_before_noon(self):
        # 19th Dec 11:59 CET -> still part of the 18th Dec logical shift
        dt = datetime.datetime(2025, 12, 19, 11, 59, 0, tzinfo=self.cet)
        service_date = utils.get_service_date(dt)
        self.assertEqual(service_date, "2025-12-18")

    def test_service_date_at_noon(self):
        # 19th Dec 12:00 CET -> starts the 19th Dec logical shift
        dt = datetime.datetime(2025, 12, 19, 12, 0, 0, tzinfo=self.cet)
        service_date = utils.get_service_date(dt)
        self.assertEqual(service_date, "2025-12-19")

    def test_service_date_afternoon(self):
        # 19th Dec 14:00 CET -> 19th Dec logical shift
        dt = datetime.datetime(2025, 12, 19, 14, 0, 0, tzinfo=self.cet)
        service_date = utils.get_service_date(dt)
        self.assertEqual(service_date, "2025-12-19")

    def test_service_date_late_evening(self):
        # 19th Dec 23:59 CET -> 19th Dec logical shift
        dt = datetime.datetime(2025, 12, 19, 23, 59, 0, tzinfo=self.cet)
        service_date = utils.get_service_date(dt)
        self.assertEqual(service_date, "2025-12-19")

    def test_service_date_next_day_early(self):
        # 20th Dec 02:00 CET -> still part of the 19th Dec logical shift (until 11:59)
        dt = datetime.datetime(2025, 12, 20, 2, 0, 0, tzinfo=self.cet)
        service_date = utils.get_service_date(dt)
        self.assertEqual(service_date, "2025-12-19")

if __name__ == '__main__':
    unittest.main()
