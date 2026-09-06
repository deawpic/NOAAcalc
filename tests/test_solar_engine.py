"""
Unit tests for solar_engine.py
Verifies exact compliance with index.html and README.md
"""

import unittest
from noaaharness.solar_engine import (
    calculate_solar,
    julian_day,
    minutes_to_hms,
    minutes_to_hm,
    minutes_to_duration_th
)


class TestSolarEngine(unittest.TestCase):

    def test_ban_pong_2022_03_27(self):
        """
        Baseline test case from README.md & index.html:
        Location: Ban Pong, Ratchaburi (lat: 13.8199, lon: 99.8722, tz: 7)
        Date: 2022-03-27 (27 มีนาคม 2565)
        Expected from index.html:
          - Solar Noon: 12:25:57 (745.94 min)
          - Sunrise: 06:19:58 (379.96 min)
          - Sunset: 18:31:55 / 18:31:56 (1111.92 min)
          - Day Length: 12 ชม. 12 นาที (731.96 min)
          - Civil Twilight: 05:58:38 - 18:53:15
        """
        lat = 13.8199
        lon = 99.8722
        tz = 7.0
        y = 2022
        m = 3
        d = 27

        res = calculate_solar(lat, lon, tz, y, m, d)

        # Julian Day test
        # JD at noon: 2459665.5 + (12 - 7)/24 = 2459665.708333...
        self.assertAlmostEqual(res.julian_day_noon, 2459665.708333, places=4)

        # Check Solar Noon
        self.assertAlmostEqual(res.solar_noon_min, 745.942, delta=0.01)
        self.assertEqual(minutes_to_hms(res.solar_noon_min), "12:25:57")
        self.assertEqual(minutes_to_hm(res.solar_noon_min), "12:25")

        # Check Sunrise
        self.assertAlmostEqual(res.sunrise_min, 379.962, delta=0.01)
        self.assertEqual(minutes_to_hms(res.sunrise_min), "06:19:58")
        self.assertEqual(minutes_to_hm(res.sunrise_min), "06:19")

        # Check Sunset
        self.assertAlmostEqual(res.sunset_min, 1111.922, delta=0.02)
        self.assertIn(minutes_to_hms(res.sunset_min), ["18:31:55", "18:31:56"])
        self.assertEqual(minutes_to_hm(res.sunset_min), "18:31")

        # Check Day length
        self.assertAlmostEqual(res.day_length_min, 731.96, delta=0.02)
        self.assertEqual(minutes_to_duration_th(res.day_length_min), "12 ชั่วโมง 12 นาที")

        # Check Twilights
        self.assertEqual(minutes_to_hms(res.civil_twilight_morning_min), "05:58:38")
        self.assertEqual(minutes_to_hms(res.civil_twilight_evening_min), "18:53:15")
        self.assertEqual(minutes_to_hms(res.nautical_twilight_morning_min), "05:33:50")
        self.assertEqual(minutes_to_hms(res.nautical_twilight_evening_min), "19:18:03")
        self.assertEqual(minutes_to_hms(res.astronomical_twilight_morning_min), "05:08:57")
        self.assertEqual(minutes_to_hms(res.astronomical_twilight_evening_min), "19:42:56")

        # Check Azimuth
        self.assertAlmostEqual(res.azimuth_rise_deg, 87.21, delta=0.1)
        self.assertAlmostEqual(res.azimuth_set_deg, 272.79, delta=0.1)

    def test_bangkok_preset(self):
        """Bangkok (13.7563, 100.5018, tz 7) test"""
        res = calculate_solar(13.7563, 100.5018, 7.0, 2022, 3, 27)
        # In README table 3: Bangkok is ~3 mins earlier than Ban Pong
        self.assertEqual(minutes_to_hm(res.sunrise_min), "06:17")
        self.assertEqual(minutes_to_hm(res.sunset_min), "18:29")
        self.assertEqual(minutes_to_hm(res.solar_noon_min), "12:23")

    def test_polar_day_and_night(self):
        """Test polar latitude where sun does not set or rise"""
        # North Pole in June (Midnight sun)
        res_summer = calculate_solar(85.0, 0.0, 0.0, 2022, 6, 21)
        self.assertTrue(res_summer.is_polar_day)
        self.assertIsNone(res_summer.sunrise_min)
        self.assertIsNone(res_summer.sunset_min)

        # North Pole in December (Polar night)
        res_winter = calculate_solar(85.0, 0.0, 0.0, 2022, 12, 21)
        self.assertTrue(res_winter.is_polar_night)
        self.assertIsNone(res_winter.sunrise_min)
        self.assertIsNone(res_winter.sunset_min)


if __name__ == "__main__":
    unittest.main()
