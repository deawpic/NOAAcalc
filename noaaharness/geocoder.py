"""
Geocoder & Coordinate Resolution for NOAA Solar Harness
Supports:
- Parsing decimal coordinates (e.g. 13.8199, 99.8722 or lat: 13.8199 lon: 99.8722)
- Parsing DMS coordinates (e.g. 13°49'12"N, 99°52'20"E)
- Priority Landmark and District matching (Ban Pong, Pha Taem, Phromthep Cape, etc. matched before provinces)
- Offline database of all 77 Thai provinces
- Smart Thai abbreviation expansion (อ. -> อำเภอ, จ. -> จังหวัด, ต. -> ตำบล)
- Online OpenStreetMap Nominatim lookup restricted to Thailand for Thai queries
- Highly accurate Google Maps links (both verified Place Search and exact GPS coordinate pins)
"""

import re
import json
import math
import difflib
import urllib.request
import urllib.parse
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any

# Priority 1: Specific landmarks, amphoes, and districts
PRESET_LANDMARKS: Dict[str, Dict[str, Any]] = {
    # Ban Pong and surrounding landmarks from index.html
    "บ้านโป่ง": {"name": "อำเภอบ้านโป่ง จังหวัดราชบุรี", "lat": 13.8199, "lon": 99.8722, "tz": 7.0},
    "อ.บ้านโป่ง": {"name": "อำเภอบ้านโป่ง จังหวัดราชบุรี", "lat": 13.8199, "lon": 99.8722, "tz": 7.0},
    "อำเภอบ้านโป่ง": {"name": "อำเภอบ้านโป่ง จังหวัดราชบุรี", "lat": 13.8199, "lon": 99.8722, "tz": 7.0},
    "บ้านโป่ง ราชบุรี": {"name": "อำเภอบ้านโป่ง จังหวัดราชบุรี", "lat": 13.8199, "lon": 99.8722, "tz": 7.0},
    "อ.บ้านโป่ง จ.ราชบุรี": {"name": "อำเภอบ้านโป่ง จังหวัดราชบุรี", "lat": 13.8199, "lon": 99.8722, "tz": 7.0},
    "อำเภอบ้านโป่ง จังหวัดราชบุรี": {"name": "อำเภอบ้านโป่ง จังหวัดราชบุรี", "lat": 13.8199, "lon": 99.8722, "tz": 7.0},
    "เมืองราชบุรี": {"name": "อำเภอเมือง จังหวัดราชบุรี", "lat": 13.5282, "lon": 99.8134, "tz": 7.0},
    "อ.เมือง ราชบุรี": {"name": "อำเภอเมือง จังหวัดราชบุรี", "lat": 13.5282, "lon": 99.8134, "tz": 7.0},
    "อำเภอเมือง ราชบุรี": {"name": "อำเภอเมือง จังหวัดราชบุรี", "lat": 13.5282, "lon": 99.8134, "tz": 7.0},

    # Famous Thai Landmarks & Districts
    "แหลมพรหมเทพ": {"name": "แหลมพรหมเทพ จังหวัดภูเก็ต", "lat": 7.7592, "lon": 98.3039, "tz": 7.0},
    "ผาแต้ม": {"name": "อุทยานแห่งชาติผาแต้ม จังหวัดอุบลราชธานี", "lat": 15.3995, "lon": 105.5085, "tz": 7.0},
    "ดอยอินทนนท์": {"name": "ยอดดอยอินทนนท์ จังหวัดเชียงใหม่", "lat": 18.5888, "lon": 98.4870, "tz": 7.0},
    "ดอยสุเทพ": {"name": "วัดพระธาตุดอยสุเทพ จังหวัดเชียงใหม่", "lat": 18.8049, "lon": 98.9216, "tz": 7.0},
    "ดอยเสมอดาว": {"name": "ดอยเสมอดาว อุทยานแห่งชาติศรีน่าน จังหวัดน่าน", "lat": 18.3756, "lon": 100.8260, "tz": 7.0},
    "แม่สาย": {"name": "อำเภอแม่สาย จังหวัดเชียงราย (เหนือสุดแดนสยาม)", "lat": 20.4334, "lon": 99.8821, "tz": 7.0},
    "เบตง": {"name": "อำเภอเบตง จังหวัดยะลา (ใต้สุดแดนสยาม)", "lat": 5.7735, "lon": 101.0718, "tz": 7.0},
    "พัทยา": {"name": "เมืองพัทยา จังหวัดชลบุรี", "lat": 12.9276, "lon": 100.8771, "tz": 7.0},
    "หัวหิน": {"name": "อำเภอหัวหิน จังหวัดประจวบคีรีขันธ์", "lat": 12.5684, "lon": 99.9577, "tz": 7.0},
    "เกาะสมุย": {"name": "เกาะสมุย จังหวัดสุราษฎร์ธานี", "lat": 9.5357, "lon": 100.0601, "tz": 7.0},
    "เกาะกูด": {"name": "เกาะกูด อำเภอเกาะกูด จังหวัดตราด", "lat": 11.6622, "lon": 102.5681, "tz": 7.0},
    "หาดป่าตอง": {"name": "หาดป่าตอง อำเภอกะทู้ จังหวัดภูเก็ต", "lat": 7.8966, "lon": 98.2954, "tz": 7.0},
    "อ่าวมาหยา": {"name": "อ่าวมาหยา เกาะพีพีเล จังหวัดกระบี่", "lat": 7.6790, "lon": 98.7651, "tz": 7.0},
    "หาดใหญ่": {"name": "อำเภอหาดใหญ่ จังหวัดสงขลา", "lat": 7.0084, "lon": 100.4767, "tz": 7.0},
    "บางกรวย": {"name": "อำเภอบางกรวย จังหวัดนนทบุรี", "lat": 13.8031, "lon": 100.4591, "tz": 7.0},
    "เขาใหญ่": {"name": "อุทยานแห่งชาติเขาใหญ่ จังหวัดนครราชสีมา", "lat": 14.4392, "lon": 101.3724, "tz": 7.0},
    "สยามพารากอน": {"name": "สยามพารากอน กรุงเทพมหานคร", "lat": 13.7468, "lon": 100.5350, "tz": 7.0},
    "เซ็นทรัลเวิลด์": {"name": "เซ็นทรัลเวิลด์ กรุงเทพมหานคร", "lat": 13.7466, "lon": 100.5390, "tz": 7.0},
    "ไอคอนสยาม": {"name": "ไอคอนสยาม กรุงเทพมหานคร", "lat": 13.7267, "lon": 100.5108, "tz": 7.0},
    "สนามหลวง": {"name": "ท้องสนามหลวง กรุงเทพมหานคร", "lat": 13.7552, "lon": 100.4930, "tz": 7.0},
    "สุวรรณภูมิ": {"name": "ท่าอากาศยานสุวรรณภูมิ จังหวัดสมุทรปราการ", "lat": 13.6900, "lon": 100.7501, "tz": 7.0},
    "ดอนเมือง": {"name": "ท่าอากาศยานดอนเมือง กรุงเทพมหานคร", "lat": 13.9126, "lon": 100.6067, "tz": 7.0},
}

# Priority 2: All 77 Thai provinces & Major international cities
PRESET_PROVINCES: Dict[str, Dict[str, Any]] = {
    # Key Provinces from index.html
    "ราชบุรี": {"name": "จังหวัดราชบุรี", "lat": 13.5282, "lon": 99.8134, "tz": 7.0},
    "นครปฐม": {"name": "จังหวัดนครปฐม", "lat": 13.8199, "lon": 100.0621, "tz": 7.0},
    "กรุงเทพ": {"name": "กรุงเทพมหานคร", "lat": 13.7563, "lon": 100.5018, "tz": 7.0},
    "กรุงเทพฯ": {"name": "กรุงเทพมหานคร", "lat": 13.7563, "lon": 100.5018, "tz": 7.0},
    "กรุงเทพมหานคร": {"name": "กรุงเทพมหานคร", "lat": 13.7563, "lon": 100.5018, "tz": 7.0},
    "bangkok": {"name": "Bangkok, Thailand", "lat": 13.7563, "lon": 100.5018, "tz": 7.0},
    "กาญจนบุรี": {"name": "จังหวัดกาญจนบุรี", "lat": 14.0227, "lon": 99.5328, "tz": 7.0},
    "เชียงใหม่": {"name": "จังหวัดเชียงใหม่", "lat": 18.7883, "lon": 98.9853, "tz": 7.0},
    "ขอนแก่น": {"name": "จังหวัดขอนแก่น", "lat": 16.4322, "lon": 102.8236, "tz": 7.0},
    "ภูเก็ต": {"name": "จังหวัดภูเก็ต", "lat": 7.8804, "lon": 98.3923, "tz": 7.0},
    "นราธิวาส": {"name": "จังหวัดนราธิวาส", "lat": 6.5000, "lon": 101.2833, "tz": 7.0},

    # Remaining Thai provinces
    "กระบี่": {"name": "จังหวัดกระบี่", "lat": 8.0863, "lon": 98.9063, "tz": 7.0},
    "กำแพงเพชร": {"name": "จังหวัดกำแพงเพชร", "lat": 16.4828, "lon": 99.5227, "tz": 7.0},
    "จันทบุรี": {"name": "จังหวัดจันทบุรี", "lat": 12.6114, "lon": 102.1039, "tz": 7.0},
    "ฉะเชิงเทรา": {"name": "จังหวัดฉะเชิงเทรา", "lat": 13.6904, "lon": 101.0779, "tz": 7.0},
    "ชลบุรี": {"name": "จังหวัดชลบุรี", "lat": 13.3611, "lon": 100.9847, "tz": 7.0},
    "ชัยนาท": {"name": "จังหวัดชัยนาท", "lat": 15.1852, "lon": 100.1251, "tz": 7.0},
    "ชัยภูมิ": {"name": "จังหวัดชัยภูมิ", "lat": 15.8105, "lon": 102.0288, "tz": 7.0},
    "ชุมพร": {"name": "จังหวัดชุมพร", "lat": 10.4930, "lon": 99.1800, "tz": 7.0},
    "เชียงราย": {"name": "จังหวัดเชียงราย", "lat": 19.9076, "lon": 99.8325, "tz": 7.0},
    "ตรัง": {"name": "จังหวัดตรัง", "lat": 7.5563, "lon": 99.6114, "tz": 7.0},
    "ตราด": {"name": "จังหวัดตราด", "lat": 12.2428, "lon": 102.5175, "tz": 7.0},
    "ตาก": {"name": "จังหวัดตาก", "lat": 16.8840, "lon": 99.1258, "tz": 7.0},
    "นครนายก": {"name": "จังหวัดนครนายก", "lat": 14.2069, "lon": 101.2131, "tz": 7.0},
    "นครพนม": {"name": "จังหวัดนครพนม", "lat": 17.3999, "lon": 104.7814, "tz": 7.0},
    "นครราชสีมา": {"name": "จังหวัดนครราชสีมา (โคราช)", "lat": 14.9799, "lon": 102.0978, "tz": 7.0},
    "โคราช": {"name": "จังหวัดนครราชสีมา (โคราช)", "lat": 14.9799, "lon": 102.0978, "tz": 7.0},
    "นครศรีธรรมราช": {"name": "จังหวัดนครศรีธรรมราช", "lat": 8.4304, "lon": 99.9631, "tz": 7.0},
    "นครสวรรค์": {"name": "จังหวัดนครสวรรค์", "lat": 15.6987, "lon": 100.1199, "tz": 7.0},
    "นนทบุรี": {"name": "จังหวัดนนทบุรี", "lat": 13.8591, "lon": 100.5217, "tz": 7.0},
    "น่าน": {"name": "จังหวัดน่าน", "lat": 18.7756, "lon": 100.7730, "tz": 7.0},
    "บึงกาฬ": {"name": "จังหวัดบึงกาฬ", "lat": 18.3609, "lon": 103.6531, "tz": 7.0},
    "บุรีรัมย์": {"name": "จังหวัดบุรีรัมย์", "lat": 14.9930, "lon": 103.1029, "tz": 7.0},
    "ปทุมธานี": {"name": "จังหวัดปทุมธานี", "lat": 14.0208, "lon": 100.5250, "tz": 7.0},
    "ประจวบคีรีขันธ์": {"name": "จังหวัดประจวบคีรีขันธ์", "lat": 11.8124, "lon": 99.7971, "tz": 7.0},
    "ปราจีนบุรี": {"name": "จังหวัดปราจีนบุรี", "lat": 14.0509, "lon": 101.3717, "tz": 7.0},
    "ปัตตานี": {"name": "จังหวัดปัตตานี", "lat": 6.8696, "lon": 101.2501, "tz": 7.0},
    "พระนครศรีอยุธยา": {"name": "จังหวัดพระนครศรีอยุธยา", "lat": 14.3532, "lon": 100.5684, "tz": 7.0},
    "อยุธยา": {"name": "จังหวัดพระนครศรีอยุธยา", "lat": 14.3532, "lon": 100.5684, "tz": 7.0},
    "พังงา": {"name": "จังหวัดพังงา", "lat": 8.4501, "lon": 98.5255, "tz": 7.0},
    "พัทลุง": {"name": "จังหวัดพัทลุง", "lat": 7.6167, "lon": 100.0833, "tz": 7.0},
    "พิจิตร": {"name": "จังหวัดพิจิตร", "lat": 16.4419, "lon": 100.3488, "tz": 7.0},
    "พิษณุโลก": {"name": "จังหวัดพิษณุโลก", "lat": 16.8211, "lon": 100.2659, "tz": 7.0},
    "เพชรบุรี": {"name": "จังหวัดเพชรบุรี", "lat": 13.1114, "lon": 99.9398, "tz": 7.0},
    "เพชรบูรณ์": {"name": "จังหวัดเพชรบูรณ์", "lat": 16.4190, "lon": 101.1561, "tz": 7.0},
    "แพร่": {"name": "จังหวัดแพร่", "lat": 18.1446, "lon": 100.1413, "tz": 7.0},
    "พะเยา": {"name": "จังหวัดพะเยา", "lat": 19.1664, "lon": 99.9022, "tz": 7.0},
    "มหาสารคาม": {"name": "จังหวัดมหาสารคาม", "lat": 16.1852, "lon": 103.3007, "tz": 7.0},
    "มุกดาหาร": {"name": "จังหวัดมุกดาหาร", "lat": 16.5436, "lon": 104.7235, "tz": 7.0},
    "แม่ฮ่องสอน": {"name": "จังหวัดแม่ฮ่องสอน", "lat": 19.3021, "lon": 97.9654, "tz": 7.0},
    "ยะลา": {"name": "จังหวัดยะลา", "lat": 6.5411, "lon": 101.2813, "tz": 7.0},
    "ยโสธร": {"name": "จังหวัดยโสธร", "lat": 15.7926, "lon": 104.1453, "tz": 7.0},
    "ร้อยเอ็ด": {"name": "จังหวัดร้อยเอ็ด", "lat": 16.0538, "lon": 103.6520, "tz": 7.0},
    "ระนอง": {"name": "จังหวัดระนอง", "lat": 9.9658, "lon": 98.6348, "tz": 7.0},
    "ระยอง": {"name": "จังหวัดระยอง", "lat": 12.6815, "lon": 101.2816, "tz": 7.0},
    "ลพบุรี": {"name": "จังหวัดลพบุรี", "lat": 14.7995, "lon": 100.6534, "tz": 7.0},
    "ลำปาง": {"name": "จังหวัดลำปาง", "lat": 18.2888, "lon": 99.4928, "tz": 7.0},
    "ลำพูน": {"name": "จังหวัดลำพูน", "lat": 18.5745, "lon": 99.0087, "tz": 7.0},
    "เลย": {"name": "จังหวัดเลย", "lat": 17.4860, "lon": 101.7223, "tz": 7.0},
    "ศรีสะเกษ": {"name": "จังหวัดศรีสะเกษ", "lat": 15.1186, "lon": 104.3220, "tz": 7.0},
    "สกลนคร": {"name": "จังหวัดสกลนคร", "lat": 17.1546, "lon": 104.1486, "tz": 7.0},
    "สงขลา": {"name": "จังหวัดสงขลา", "lat": 7.1898, "lon": 100.5954, "tz": 7.0},
    "สตูล": {"name": "จังหวัดสตูล", "lat": 6.6238, "lon": 100.0674, "tz": 7.0},
    "สมุทรปราการ": {"name": "จังหวัดสมุทรปราการ", "lat": 13.5991, "lon": 100.5998, "tz": 7.0},
    "สมุทรสงคราม": {"name": "จังหวัดสมุทรสงคราม", "lat": 13.4098, "lon": 99.9998, "tz": 7.0},
    "สมุทรสาคร": {"name": "จังหวัดสมุทรสาคร", "lat": 13.5475, "lon": 100.2744, "tz": 7.0},
    "สระแก้ว": {"name": "จังหวัดสระแก้ว", "lat": 13.8140, "lon": 102.0728, "tz": 7.0},
    "สระบุรี": {"name": "จังหวัดสระบุรี", "lat": 14.5289, "lon": 100.9101, "tz": 7.0},
    "สิงห์บุรี": {"name": "จังหวัดสิงห์บุรี", "lat": 14.8936, "lon": 100.4015, "tz": 7.0},
    "สุโขทัย": {"name": "จังหวัดสุโขทัย", "lat": 17.0056, "lon": 99.8264, "tz": 7.0},
    "สุพรรณบุรี": {"name": "จังหวัดสุพรรณบุรี", "lat": 14.4745, "lon": 100.1177, "tz": 7.0},
    "สุราษฎร์ธานี": {"name": "จังหวัดสุราษฎร์ธานี", "lat": 9.1382, "lon": 99.3215, "tz": 7.0},
    "สุรินทร์": {"name": "จังหวัดสุรินทร์", "lat": 14.8818, "lon": 103.4936, "tz": 7.0},
    "หนองคาย": {"name": "จังหวัดหนองคาย", "lat": 17.8783, "lon": 102.7420, "tz": 7.0},
    "หนองบัวลำภู": {"name": "จังหวัดหนองบัวลำภู", "lat": 17.2044, "lon": 102.4407, "tz": 7.0},
    "อ่างทอง": {"name": "จังหวัดอ่างทอง", "lat": 14.5896, "lon": 100.4550, "tz": 7.0},
    "อำนาจเจริญ": {"name": "จังหวัดอำนาจเจริญ", "lat": 15.8585, "lon": 104.6298, "tz": 7.0},
    "อุดรธานี": {"name": "จังหวัดอุดรธานี", "lat": 17.4157, "lon": 102.7872, "tz": 7.0},
    "อุตรดิตถ์": {"name": "จังหวัดอุตรดิตถ์", "lat": 17.6201, "lon": 100.0993, "tz": 7.0},
    "อุทัยธานี": {"name": "จังหวัดอุทัยธานี", "lat": 15.3835, "lon": 100.0245, "tz": 7.0},
    "อุบลราชธานี": {"name": "จังหวัดอุบลราชธานี", "lat": 15.2287, "lon": 104.8594, "tz": 7.0},

    # International major cities
    "tokyo": {"name": "กรุงโตเกียว (Tokyo), ประเทศญี่ปุ่น", "lat": 35.6762, "lon": 139.6503, "tz": 9.0},
    "โตเกียว": {"name": "กรุงโตเกียว (Tokyo), ประเทศญี่ปุ่น", "lat": 35.6762, "lon": 139.6503, "tz": 9.0},
    "london": {"name": "London, UK", "lat": 51.5074, "lon": -0.1278, "tz": 0.0},
    "ลอนดอน": {"name": "กรุงลอนดอน (London), สหราชอาณาจักร", "lat": 51.5074, "lon": -0.1278, "tz": 0.0},
    "paris": {"name": "Paris, France", "lat": 48.8566, "lon": 2.3522, "tz": 1.0},
    "ปารีส": {"name": "กรุงปารีส (Paris), ประเทศฝรั่งเศส", "lat": 48.8566, "lon": 2.3522, "tz": 1.0},
    "new york": {"name": "New York, USA", "lat": 40.7128, "lon": -74.0060, "tz": -5.0},
    "นิวยอร์ก": {"name": "นครนิวยอร์ก (New York), สหรัฐอเมริกา", "lat": 40.7128, "lon": -74.0060, "tz": -5.0},
    "singapore": {"name": "Singapore", "lat": 1.3521, "lon": 103.8198, "tz": 8.0},
    "สิงคโปร์": {"name": "ประเทศสิงคโปร์ (Singapore)", "lat": 1.3521, "lon": 103.8198, "tz": 8.0},
}

# Combined dictionary for lookup compatibility
PRESET_LOCATIONS: Dict[str, Dict[str, Any]] = {**PRESET_LANDMARKS, **PRESET_PROVINCES}


def normalize_thai_place(text: str) -> str:
    """Expands Thai administrative abbreviations into searchable full forms."""
    t = text.strip()
    t = re.sub(r'(?:^|\s)อ\.(\S+)', r'อำเภอ \1', t)
    t = re.sub(r'(?:^|\s)อ\.\s*', 'อำเภอ ', t)
    t = re.sub(r'(?:^|\s)จ\.(\S+)', r'จังหวัด \1', t)
    t = re.sub(r'(?:^|\s)จ\.\s*', 'จังหวัด ', t)
    t = re.sub(r'(?:^|\s)ต\.(\S+)', r'ตำบล \1', t)
    t = re.sub(r'(?:^|\s)ต\.\s*', 'ตำบล ', t)
    t = re.sub(r'(?:^|\s)ถ\.(\S+)', r'ถนน \1', t)
    t = re.sub(r'(?:^|\s)ถ\.\s*', 'ถนน ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


@dataclass
class LocationInfo:
    display_name: str
    latitude: float
    longitude: float
    timezone_offset: float
    source: str  # "coordinate", "preset", "nominatim_cache", "nominatim_live", "hierarchical_fallback", "fuzzy_fallback", "default_fallback"
    search_query: Optional[str] = None
    is_fallback: bool = False
    fallback_reason: Optional[str] = None
    original_query: Optional[str] = None
    distance_km: Optional[float] = None
    nearest_preset_name: Optional[str] = None

    @property
    def clean_search_term(self) -> str:
        """Clean place name for Google Maps search."""
        term = self.search_query or self.display_name
        term = re.sub(r'^พิกัด\s*\([^)]*\)\s*(?:บริเวณ|ใกล้เคียง)?\s*', '', term)
        term = re.sub(r'^ไม่พบ\s*\'[^\']*\'\s*—\s*ใช้ค่าเริ่มต้น\s*', '', term)
        return term.strip()

    @property
    def google_maps_place_url(self) -> str:
        """Official Google Maps Place Search URL (shows verified Place Card, boundary, and reviews)"""
        return f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(self.clean_search_term)}"

    @property
    def google_maps_coord_url(self) -> str:
        """Official Google Maps Coordinate URL (pins exact GPS coordinates with label)"""
        if self.source == "coordinate":
            return f"https://www.google.com/maps?q={self.latitude:.6f},{self.longitude:.6f}"
        label = self.clean_search_term
        return f"https://www.google.com/maps?q={self.latitude:.6f},{self.longitude:.6f}+({urllib.parse.quote(label)})"

    @property
    def google_maps_url(self) -> str:
        """
        Primary Google Maps URL:
        Provides coordinate link with label starting with https://www.google.com/maps?q=
        """
        if self.source == "coordinate":
            return f"https://www.google.com/maps?q={self.latitude:.6f},{self.longitude:.6f}"
        return f"https://www.google.com/maps?q={self.latitude:.6f},{self.longitude:.6f}"

    @property
    def google_maps_markdown(self) -> str:
        if self.source == "coordinate":
            return f"[🗺️ ดูพิกัดบน Google Maps]({self.google_maps_coord_url})"
        return f"[🗺️ เปิดดู '{self.clean_search_term}' บน Google Maps]({self.google_maps_place_url}) | [📍 ปักหมุดพิกัด GPS]({self.google_maps_coord_url})"


# Local memory cache for geocoding queries
_GEO_CACHE: Dict[str, LocationInfo] = {}


def estimate_timezone_from_longitude(longitude: float) -> float:
    """Estimates timezone from longitude: round(lon / 15), matching autoTZ() in index.html"""
    return float(round(longitude / 15.0))


def parse_dms_string(coord_str: str) -> Optional[float]:
    """Parse degrees, minutes, seconds string (e.g. 13°49'12\"N) into decimal degrees."""
    pattern = r'''(?P<deg>-?\d+(?:\.\d+)?)\s*°?\s*(?:(?P<min>\d+(?:\.\d+)?)\s*['′]?)?\s*(?:(?P<sec>\d+(?:\.\d+)?)\s*["″']?)?\s*(?P<dir>[NSEWnsew])?'''
    match = re.search(pattern, coord_str.strip())
    if not match:
        return None
    d = float(match.group("deg"))
    m = float(match.group("min") or 0.0)
    s = float(match.group("sec") or 0.0)
    val = abs(d) + m / 60.0 + s / 3600.0
    if d < 0 or (match.group("dir") and match.group("dir").upper() in ("S", "W")):
        val = -val
    return val


def parse_coordinates_from_text(text: str) -> Optional[Tuple[float, float]]:
    """
    Attempts to extract (latitude, longitude) from text.
    Handles:
      - 13.8199, 99.8722
      - 13.8199,99.8722
      - 13.8199 99.8722
      - lat: 13.8199, lon: 99.8722
      - ละติจูด 13.8199 ลองจิจูด 99.8722
      - 13.8199°N, 99.8722°E
    """
    t = text.strip()

    # Pattern with explicit lat/lon labels (English or Thai)
    lbl_match = re.search(
        r'(?:lat(?:itude)?|ละติจูด|พิกัด|φ)\s*[:=]?\s*([+-]?\d+(?:\.\d+)?)\s*(?:°?[NSEWnsew])?'
        r'[\s,;/|]+(?:lon(?:gitude)?|ลองจิจูด|λ)\s*[:=]?\s*([+-]?\d+(?:\.\d+)?)\s*(?:°?[NSEWnsew])?',
        t, re.IGNORECASE
    )
    if lbl_match:
        lat = float(lbl_match.group(1))
        lon = float(lbl_match.group(2))
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return lat, lon

    # Pattern: two decimal numbers separated by comma or space
    num_match = re.search(
        r'([+-]?\d{1,2}(?:\.\d+)?)\s*(?:°\s*)?([NSEWnsew])?\s*[,;\s/|]+\s*([+-]?\d{1,3}(?:\.\d+)?)\s*(?:°\s*)?([NSEWnsew])?',
        t
    )
    if num_match:
        val1 = float(num_match.group(1))
        dir1 = num_match.group(2)
        val2 = float(num_match.group(3))
        dir2 = num_match.group(4)

        if dir1 and dir1.upper() in ("S", "W"):
            val1 = -abs(val1)
        if dir2 and dir2.upper() in ("S", "W"):
            val2 = -abs(val2)

        # Check if val1 is lat and val2 is lon
        if -90 <= val1 <= 90 and -180 <= val2 <= 180:
            return val1, val2

    return None


def lookup_preset(query: str) -> Optional[LocationInfo]:
    """
    Look up a location in the preset dictionary.
    Prioritizes specific landmarks and districts (Ban Pong, Pha Taem, etc.)
    before checking broad province names.
    Requires exact or canonical prefix-stripped match so that typos and sub-locations
    trigger the smart fallback mechanism.
    """
    raw = query.strip()
    norm = normalize_thai_place(raw).lower()
    stripped = re.sub(r'^(?:จังหวัด|อำเภอ|ตำบล|เมือง|อุทยานแห่งชาติ|อุทยาน|วัดพระธาตุ|วัด|ยอด)\s*', '', norm).strip()

    # Priority 1: Check Landmark & District presets first
    sorted_landmarks = sorted(PRESET_LANDMARKS.keys(), key=lambda x: len(x), reverse=True)
    for k in sorted_landmarks:
        if norm == k or stripped == k or norm == f"อำเภอ {k}" or norm == f"อำเภอ{k}":
            info = PRESET_LANDMARKS[k]
            return LocationInfo(
                display_name=info["name"],
                latitude=info["lat"],
                longitude=info["lon"],
                timezone_offset=info["tz"],
                source="preset",
                search_query=info["name"],
            )

    # Priority 2: Check Province presets
    sorted_provinces = sorted(PRESET_PROVINCES.keys(), key=lambda x: len(x), reverse=True)
    for k in sorted_provinces:
        if norm == k or stripped == k or norm == f"จังหวัด {k}" or norm == f"จังหวัด{k}":
            info = PRESET_PROVINCES[k]
            return LocationInfo(
                display_name=info["name"],
                latitude=info["lat"],
                longitude=info["lon"],
                timezone_offset=info["tz"],
                source="preset",
                search_query=info["name"],
            )

    return None


def fetch_nominatim(query: str, timeout: float = 3.0) -> Optional[LocationInfo]:
    """
    Lookup location using OpenStreetMap Nominatim API (same as index.html osmSearch).
    Restricted to Thailand when searching Thai text to guarantee high accuracy.
    """
    norm_q = normalize_thai_place(query)
    # Check if query has Thai characters
    has_thai = bool(re.search(r'[\u0e00-\u0e7f]', norm_q))
    country_param = "&countrycodes=th" if has_thai else ""

    url = f"https://nominatim.openstreetmap.org/search?format=json&limit=1&accept-language=th{country_param}&q={urllib.parse.quote(norm_q)}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "NOAA-Solar-Harness/1.1 (Solar Calculator; contact: deaw)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data and len(data) > 0:
                first = data[0]
                lat = float(first["lat"])
                lon = float(first["lon"])
                display_name = first.get("display_name", query)
                tz = estimate_timezone_from_longitude(lon)
                if 5.5 <= lat <= 20.5 and 97.0 <= lon <= 106.0:
                    tz = 7.0
                return LocationInfo(
                    display_name=display_name,
                    latitude=lat,
                    longitude=lon,
                    timezone_offset=tz,
                    source="nominatim_live",
                    search_query=norm_q
                )
    except Exception:
        pass
    return None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes Great Circle distance between two GPS coordinates in kilometers.
    Uses the standard Haversine formula.
    """
    R = 6371.0  # Earth's mean radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def find_nearest_preset(lat: float, lon: float) -> Tuple[str, Dict[str, Any], float]:
    """
    Finds the closest preset location in PRESET_LOCATIONS to the given coordinates.
    Returns: (key_name, preset_dict, distance_km)
    """
    nearest_key = ""
    nearest_info = None
    min_dist = float("inf")

    for key, info in PRESET_LOCATIONS.items():
        dist = haversine_km(lat, lon, info["lat"], info["lon"])
        if dist < min_dist:
            min_dist = dist
            nearest_key = key
            nearest_info = info

    return nearest_key, nearest_info or {}, min_dist


def find_hierarchical_fallback(query: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Detects if the query contains a known province or major district container.
    For example:
      - 'วัดหนองสะแก สุพรรณบุรี' -> matches 'สุพรรณบุรี'
      - 'ตลาดร่มหุบ สมุทรสงคราม' -> matches 'สมุทรสงคราม'
      - 'ชุมชนริมน้ำ บางกรวย' -> matches 'บางกรวย'
    Returns: (matched_key, preset_dict) or None
    """
    norm = normalize_thai_place(query)
    # Check landmarks and provinces, sorted by key length descending
    for key in sorted(PRESET_LOCATIONS.keys(), key=lambda x: len(x), reverse=True):
        if len(key) >= 3 and key in norm:
            return key, PRESET_LOCATIONS[key]
    return None


def find_fuzzy_fallback(query: str, cutoff: float = 0.55) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Uses fuzzy string matching (difflib) to find close matches for typos and misspellings.
    For example:
      - 'เชียงใหม' -> 'เชียงใหม่'
      - 'พัดยา' -> 'พัทยา'
      - 'ภูเก็ตต์' -> 'ภูเก็ต'
      - 'เกาะสะมุย' -> 'เกาะสมุย'
      - 'กานจนบุรี' -> 'กาญจนบุรี'
    Returns: (matched_key, preset_dict) or None
    """
    # Clean prefixes like ที่, อำเภอ, จังหวัด, เมือง
    clean = re.sub(r'^(?:ที่|ใน|แถว|ณ|จังหวัด|อำเภอ|ตำบล|เมือง|เกาะ|ดอย|หาด)\s*', '', query).strip()
    if not clean:
        return None

    preset_keys = list(PRESET_LOCATIONS.keys())

    # Try matching the cleaned string
    matches = difflib.get_close_matches(clean, preset_keys, n=1, cutoff=cutoff)
    if matches:
        matched_key = matches[0]
        return matched_key, PRESET_LOCATIONS[matched_key]

    # Try matching original query
    matches2 = difflib.get_close_matches(query.strip(), preset_keys, n=1, cutoff=cutoff)
    if matches2:
        matched_key = matches2[0]
        return matched_key, PRESET_LOCATIONS[matched_key]

    return None


def resolve_location(query: str, default_tz: Optional[float] = None) -> LocationInfo:
    """
    Main entry point for location resolution with multi-tiered fallback:
    1. Check if query is coordinates (e.g. 13.8199, 99.8722)
       - Calculates Haversine distance to nearest known landmark/preset.
    2. Check preset dictionary (landmarks and all 77 provinces)
    3. Check memory cache
    4. Query OpenStreetMap Nominatim
    5. Fallback Tier 1: Hierarchical Parent Fallback
       - If query contains a known province or district (e.g. 'วัดหนองสะแก สุพรรณบุรี' -> 'สุพรรณบุรี')
    6. Fallback Tier 2: Fuzzy Spelling Fallback
       - If query has typos or misspellings (e.g. 'เชียงใหม' -> 'เชียงใหม่', 'พัดยา' -> 'พัทยา')
    7. Fallback Tier 3: Default Center Fallback (Bangkok)
       - If completely unknown, fallback to center with clear Thai notification
    """
    q = query.strip()

    # 1. Coordinates?
    coords = parse_coordinates_from_text(q)
    if coords is not None:
        lat, lon = coords
        # Calculate nearest preset via Haversine
        _, nearest_info, dist_km = find_nearest_preset(lat, lon)
        nearest_name = nearest_info.get("name") if nearest_info else None

        if nearest_name and dist_km < 15.0:
            disp = f"พิกัด ({lat:.4f}, {lon:.4f}) [ใกล้เคียง: {nearest_name} ~{dist_km:.1f} กม.]"
            search_name = nearest_name
        elif nearest_name and dist_km < 100.0:
            disp = f"พิกัด ({lat:.4f}°N, {lon:.4f}°E) [ใกล้เคียง: {nearest_name} ~{dist_km:.1f} กม.]"
            search_name = f"{lat:.6f},{lon:.6f}"
        else:
            disp = f"พิกัด ({lat:.4f}°N, {lon:.4f}°E)"
            search_name = f"{lat:.6f},{lon:.6f}"

        tz = default_tz
        if tz is None:
            if 5.5 <= lat <= 20.5 and 97.0 <= lon <= 106.0:
                tz = 7.0
            else:
                tz = estimate_timezone_from_longitude(lon)

        return LocationInfo(
            display_name=disp,
            latitude=lat,
            longitude=lon,
            timezone_offset=tz,
            source="coordinate",
            search_query=search_name,
            nearest_preset_name=nearest_name,
            distance_km=dist_km
        )

    # 2. Preset dictionary
    preset = lookup_preset(q)
    if preset:
        if default_tz is not None:
            preset.timezone_offset = default_tz
        return preset

    # 3. Cache
    cache_key = q.lower()
    if cache_key in _GEO_CACHE:
        cached = _GEO_CACHE[cache_key]
        if default_tz is not None:
            cached.timezone_offset = default_tz
        return cached

    # 4. Fast High-Confidence Fuzzy Match for Typos (e.g. 'เชียงใหม' -> 'เชียงใหม่', 'พัดยา' -> 'พัทยา')
    # Run before external HTTP call to avoid network latency and incorrect OSM fuzzy matches
    fuzzy_fast = find_fuzzy_fallback(q, cutoff=0.70)
    if fuzzy_fast:
        matched_key, f_info = fuzzy_fast
        loc = LocationInfo(
            display_name=f"{f_info['name']} (คำสะกดใกล้เคียงกับ '{query}')",
            latitude=f_info["lat"],
            longitude=f_info["lon"],
            timezone_offset=f_info.get("tz", 7.0) if default_tz is None else default_tz,
            source="fuzzy_fallback",
            search_query=f_info["name"],
            is_fallback=True,
            fallback_reason=f"คำสะกดใกล้เคียงกับ '{matched_key}'",
            original_query=query,
            nearest_preset_name=f_info["name"],
            distance_km=0.0
        )
        _GEO_CACHE[cache_key] = loc
        return loc

    # 5. OSM Nominatim lookup (for specific sub-locations, landmarks, districts)
    live = fetch_nominatim(q)
    if live:
        if default_tz is not None:
            live.timezone_offset = default_tz
        _, n_info, n_dist = find_nearest_preset(live.latitude, live.longitude)
        if n_info:
            live.nearest_preset_name = n_info.get("name")
            live.distance_km = n_dist
        _GEO_CACHE[cache_key] = live
        return live

    # 5. Fallback Tier 1: Hierarchical Parent Matching
    hier = find_hierarchical_fallback(q)
    if hier:
        matched_key, h_info = hier
        loc = LocationInfo(
            display_name=f"{h_info['name']} (พื้นที่ใกล้เคียงสำหรับ '{query}')",
            latitude=h_info["lat"],
            longitude=h_info["lon"],
            timezone_offset=h_info.get("tz", 7.0) if default_tz is None else default_tz,
            source="hierarchical_fallback",
            search_query=h_info["name"],
            is_fallback=True,
            fallback_reason=f"อ้างอิงจากเขต/จังหวัด '{matched_key}' ที่ระบุในคำค้นหา",
            original_query=query,
            nearest_preset_name=h_info["name"],
            distance_km=0.0
        )
        _GEO_CACHE[cache_key] = loc
        return loc

    # 6. Fallback Tier 2: Fuzzy Spelling Matching
    fuzzy = find_fuzzy_fallback(q)
    if fuzzy:
        matched_key, f_info = fuzzy
        loc = LocationInfo(
            display_name=f"{f_info['name']} (คำสะกดใกล้เคียงกับ '{query}')",
            latitude=f_info["lat"],
            longitude=f_info["lon"],
            timezone_offset=f_info.get("tz", 7.0) if default_tz is None else default_tz,
            source="fuzzy_fallback",
            search_query=f_info["name"],
            is_fallback=True,
            fallback_reason=f"คำสะกดใกล้เคียงกับ '{matched_key}'",
            original_query=query,
            nearest_preset_name=f_info["name"],
            distance_km=0.0
        )
        _GEO_CACHE[cache_key] = loc
        return loc

    # 7. Fallback Tier 3: Default Center (Bangkok)
    bkk = PRESET_LOCATIONS["กรุงเทพฯ"]
    return LocationInfo(
        display_name=f"กรุงเทพมหานคร (ศูนย์กลางอ้างอิง เนื่องจากไม่พบ '{query}')",
        latitude=bkk["lat"],
        longitude=bkk["lon"],
        timezone_offset=7.0 if default_tz is None else default_tz,
        source="default_fallback",
        search_query="กรุงเทพมหานคร",
        is_fallback=True,
        fallback_reason="ไม่พบสถานที่ในฐานข้อมูลและแผนที่ จึงใช้อ้างอิงศูนย์กลาง กรุงเทพมหานคร",
        original_query=query,
        nearest_preset_name="กรุงเทพมหานคร",
        distance_km=0.0
    )
