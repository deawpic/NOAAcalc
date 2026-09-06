"""
Unit tests for agent.py (Thai Q&A, BE/CE, Local Time, Google Maps link)
"""

import unittest
from noaaharness.agent import SolarAgentHarness


class TestAgentQA(unittest.TestCase):

    def setUp(self):
        self.agent = SolarAgentHarness()

    def test_qa_ban_pong_specific_date(self):
        """
        Test question: พระอาทิตย์ขึ้นกี่โมงที่ อำเภอบ้านโป่ง วันที่ 27 มีนาคม 2565
        """
        res = self.agent.query("พระอาทิตย์ขึ้นกี่โมงที่ อำเภอบ้านโป่ง วันที่ 27 มีนาคม 2565")
        text = res["response_text"]

        # 1. Thai language check
        self.assertIn("ดวงอาทิตย์ขึ้น", text)
        self.assertIn("ผลการคำนวณเวลาดวงอาทิตย์", text)

        # 2. Local time check
        self.assertIn("06:19:58", text)
        self.assertIn("06:19", text)

        # 3. Dual Era (พ.ศ. and ค.ศ.) check
        self.assertIn("พ.ศ. 2565", text)
        self.assertIn("ค.ศ. 2022", text)

        # 4. Location check
        self.assertIn("บ้านโป่ง", text)

        # 5. Google Maps link check
        self.assertIn("https://www.google.com/maps?q=13.819900,99.872200", text)
        self.assertIn("[เปิดดูพิกัดบน Google Maps]", text)

    def test_qa_coordinate_query(self):
        """
        Test question with raw coordinates:
        "คำนวณเวลาพระอาทิตย์ขึ้น ตก ที่พิกัด 13.8199, 99.8722 วันที่ 27/03/2022"
        """
        res = self.agent.query("คำนวณเวลาพระอาทิตย์ขึ้น ตก ที่พิกัด 13.8199, 99.8722 วันที่ 27/03/2022")
        text = res["response_text"]

        self.assertIn("13.8199", text)
        self.assertIn("99.8722", text)
        self.assertIn("https://www.google.com/maps?q=13.819900,99.872200", text)
        self.assertIn("พ.ศ. 2565", text)
        self.assertIn("ค.ศ. 2022", text)
        self.assertIn("18:31", text)
        self.assertIn("06:19", text)

    def test_qa_solar_noon(self):
        """
        Test query for solar noon: เที่ยงวันจริงที่กรุงเทพฯ วันที่ 27 มีนาคม 2565 กี่โมง
        """
        res = self.agent.query("เที่ยงวันจริงที่กรุงเทพฯ วันที่ 27 มีนาคม 2565 กี่โมง")
        text = res["response_text"]

        self.assertIn("เที่ยงวันจริง", text)
        self.assertIn("12:23", text)
        self.assertIn("https://www.google.com/maps?q=13.756300,100.501800", text)
        self.assertIn("พ.ศ. 2565", text)
        self.assertIn("ค.ศ. 2022", text)

    def test_qa_short_answer(self):
        res = self.agent.query("พระอาทิตย์ตกที่เชียงใหม่ วันที่ 1 มกราคม 2568 กี่โมง", short_answer=True)
        text = res["response_text"]
        self.assertIn("เชียงใหม่", text)
        self.assertIn("พระอาทิตย์ตก", text)
        self.assertIn("พ.ศ. 2568", text)
        self.assertIn("ค.ศ. 2025", text)
        self.assertIn("https://www.google.com/maps?q=", text)

    def test_qa_save_report_utf8(self):
        import os
        # Query with explicit save command and filename
        res = self.agent.query("พระอาทิตย์ขึ้นที่อำเภอบ้านโป่ง วันที่ 27 มีนาคม 2565 กี่โมง บันทึกไฟล์ชื่อ test_unit_save.md")
        saved_path = res.get("saved_file")
        self.assertIsNotNone(saved_path)
        self.assertTrue(saved_path.startswith("reports/"))
        self.assertTrue(os.path.exists(saved_path))

        # Check content is readable as UTF-8
        with open(saved_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("บ้านโป่ง", content)
        self.assertIn("06:19:58", content)
        self.assertIn("พ.ศ. 2565", content)

        # Clean up test file
        if os.path.exists(saved_path):
            os.remove(saved_path)


if __name__ == "__main__":
    unittest.main()
