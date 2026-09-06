"""
Unit tests for geocoder.py
"""

import unittest
from noaaharness.geocoder import (
    parse_coordinates_from_text,
    resolve_location,
    LocationInfo,
    PRESET_LOCATIONS
)


class TestGeocoder(unittest.TestCase):

    def test_coordinate_parsing(self):
        # Format 1: 13.8199, 99.8722
        coords = parse_coordinates_from_text("13.8199, 99.8722")
        self.assertIsNotNone(coords)
        self.assertAlmostEqual(coords[0], 13.8199, places=4)
        self.assertAlmostEqual(coords[1], 99.8722, places=4)

        # Format 2: lat: 13.8199 lon: 99.8722
        coords2 = parse_coordinates_from_text("lat: 13.8199, lon: 99.8722")
        self.assertIsNotNone(coords2)
        self.assertAlmostEqual(coords2[0], 13.8199, places=4)
        self.assertAlmostEqual(coords2[1], 99.8722, places=4)

        # Format 3: Thai prefix "พิกัด 13.8199, 99.8722"
        coords3 = parse_coordinates_from_text("พิกัด 13.8199, 99.8722")
        self.assertIsNotNone(coords3)
        self.assertAlmostEqual(coords3[0], 13.8199, places=4)
        self.assertAlmostEqual(coords3[1], 99.8722, places=4)

    def test_preset_lookup(self):
        # Ban Pong
        loc = resolve_location("บ้านโป่ง")
        self.assertAlmostEqual(loc.latitude, 13.8199, places=4)
        self.assertAlmostEqual(loc.longitude, 99.8722, places=4)
        self.assertEqual(loc.timezone_offset, 7.0)

        # Chiang Mai
        loc_cm = resolve_location("เชียงใหม่")
        self.assertAlmostEqual(loc_cm.latitude, 18.7883, places=4)
        self.assertAlmostEqual(loc_cm.longitude, 98.9853, places=4)

    def test_google_maps_url(self):
        loc = resolve_location("บ้านโป่ง")
        expected_url = "https://www.google.com/maps?q=13.819900,99.872200"
        self.assertEqual(loc.google_maps_url, expected_url)
        self.assertIn("https://www.google.com/maps?q=13.819900,99.872200", loc.google_maps_markdown)

    def test_haversine_and_nearest_preset(self):
        # Coordinates near Ban Pong (13.82, 99.87)
        loc = resolve_location("13.82, 99.87")
        self.assertIsNotNone(loc.nearest_preset_name)
        self.assertIn("บ้านโป่ง", loc.nearest_preset_name)
        self.assertIsNotNone(loc.distance_km)
        self.assertLess(loc.distance_km, 5.0)

    def test_hierarchical_fallback(self):
        # A fictional or unlisted sub-location in Suphan Buri
        loc = resolve_location("วัดร้างที่ไม่มีในแผนที่ สุพรรณบุรี")
        self.assertTrue(loc.is_fallback)
        self.assertEqual(loc.source, "hierarchical_fallback")
        self.assertIn("สุพรรณบุรี", loc.display_name)
        self.assertIn("สุพรรณบุรี", loc.fallback_reason)

    def test_fuzzy_fallback_typo(self):
        # Typos: เชียงใหม -> เชียงใหม่
        loc_cm = resolve_location("เชียงใหม")
        self.assertTrue(loc_cm.is_fallback)
        self.assertEqual(loc_cm.source, "fuzzy_fallback")
        self.assertIn("เชียงใหม่", loc_cm.display_name)

        # Typo: พัดยา -> พัทยา
        loc_pty = resolve_location("พัดยา")
        self.assertTrue(loc_pty.is_fallback)
        self.assertEqual(loc_pty.source, "fuzzy_fallback")
        self.assertIn("พัทยา", loc_pty.display_name)

    def test_default_fallback_unknown(self):
        # Completely unknown fictional place
        loc = resolve_location("ดาวอังคารxyz999999")
        self.assertTrue(loc.is_fallback)
        self.assertEqual(loc.source, "default_fallback")
        self.assertIn("กรุงเทพมหานคร", loc.display_name)


if __name__ == "__main__":
    unittest.main()
