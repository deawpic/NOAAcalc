"""
Unit tests for date_parser.py
"""

import unittest
import datetime
from noaaharness.date_parser import (
    convert_to_ce,
    convert_ce_to_be,
    format_date_thai,
    parse_thai_date
)


class TestDateParser(unittest.TestCase):

    def test_convert_years(self):
        # BE to CE
        self.assertEqual(convert_to_ce(2565), 2022)
        self.assertEqual(convert_to_ce(2568), 2025)
        # 2-digit BE
        self.assertEqual(convert_to_ce(65), 2022)
        # Already CE
        self.assertEqual(convert_to_ce(2022), 2022)
        # CE to BE
        self.assertEqual(convert_ce_to_be(2022), 2565)

    def test_parse_thai_full_date(self):
        # 27 มีนาคม 2565
        dt, token = parse_thai_date("ขอเวลาดวงอาทิตย์วันที่ 27 มีนาคม 2565 ที่บ้านโป่ง")
        self.assertEqual(dt.year, 2022)
        self.assertEqual(dt.month, 3)
        self.assertEqual(dt.day, 27)

        # 27 มี.ค. 65
        dt2, token2 = parse_thai_date("27 มี.ค. 65")
        self.assertEqual(dt2.year, 2022)
        self.assertEqual(dt2.month, 3)
        self.assertEqual(dt2.day, 27)

    def test_parse_relative_dates(self):
        ref = datetime.date(2026, 9, 6)
        dt_today, _ = parse_thai_date("พระอาทิตย์ขึ้นวันนี้กี่โมง", reference_date=ref)
        self.assertEqual(dt_today, ref)

        dt_tmr, _ = parse_thai_date("พรุ่งนี้เชียงใหม่", reference_date=ref)
        self.assertEqual(dt_tmr, datetime.date(2026, 9, 7))

        dt_after, _ = parse_thai_date("มะรืนนี้ภูเก็ต", reference_date=ref)
        self.assertEqual(dt_after, datetime.date(2026, 9, 8))

    def test_format_date_thai(self):
        text = format_date_thai(2022, 3, 27)
        self.assertIn("27 มีนาคม", text)
        self.assertIn("พ.ศ. 2565", text)
        self.assertIn("ค.ศ. 2022", text)
        self.assertIn("วันอาทิตย์", text)


if __name__ == "__main__":
    unittest.main()
