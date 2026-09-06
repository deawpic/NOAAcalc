"""
NOAA Solar Agent Harness
Handles Thai Natural Language Q&A, Intent Extraction, Multi-turn Context,
and Generates Detailed Solar Analysis with Google Maps links and BE/CE years.
"""

import os
import re
import json
import datetime
from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict, Any

from noaaharness.solar_engine import calculate_solar, SolarCalculationResult
from noaaharness.geocoder import resolve_location, parse_coordinates_from_text, LocationInfo
from noaaharness.date_parser import parse_thai_date, format_date_thai
from noaaharness.formatter import format_solar_response_thai, format_short_answer_thai

REPORTS_DIR = "reports"


def get_report_filepath(
    filename: Optional[str] = None,
    default_stem: str = "solar_report",
    ext: str = "md",
    reports_dir: str = REPORTS_DIR
) -> str:
    """
    Constructs a safe filepath inside the 'reports/' directory, ensuring the folder exists.
    Extracts the basename so all outputs stay strictly inside reports_dir.
    """
    os.makedirs(reports_dir, exist_ok=True)
    if not filename or filename == "AUTO":
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_stem = re.sub(r'[^\w\u0e00-\u0e7f]+', '_', default_stem).strip('_') or "solar_report"
        filename = f"{clean_stem}_{timestamp}.{ext}"
    else:
        base = os.path.basename(filename.strip())
        if not base:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            base = f"{default_stem}_{timestamp}.{ext}"
        filename = base
    return os.path.join(reports_dir, filename)


def save_report_file(
    content: str,
    filename: Optional[str] = None,
    default_stem: str = "solar_report",
    reports_dir: str = REPORTS_DIR
) -> str:
    """
    Saves markdown or text report to 'reports/' directory using UTF-8 encoding.
    """
    filepath = get_report_filepath(filename, default_stem=default_stem, ext="md", reports_dir=reports_dir)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath


def save_json_file(
    data: Dict[str, Any],
    filename: Optional[str] = None,
    default_stem: str = "solar_report",
    reports_dir: str = REPORTS_DIR
) -> str:
    """
    Saves structured JSON data to 'reports/' directory using UTF-8 encoding.
    """
    filepath = get_report_filepath(filename, default_stem=default_stem, ext="json", reports_dir=reports_dir)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filepath


@dataclass
class ConversationState:
    """Retains context across multi-turn interactions in the harness session"""
    current_location: Optional[LocationInfo] = None
    current_date: Optional[datetime.date] = None
    timezone_override: Optional[float] = None
    query_history: list = field(default_factory=list)


class SolarAgentHarness:
    """
    Main Agent Harness for NOAA Solar Calculations:
    - Accepts Thai and English queries
    - Resolves coordinates or location names
    - Resolves dates with Buddhist Era (พ.ศ.) and Christian Era (ค.ศ.)
    - Computes Jean Meeus NOAA 12-step solar algorithms
    - Formulates responses in Thai with Local Time and Google Maps link
    - Saves reports to 'reports/' directory using UTF-8 encoding
    """

    def __init__(self, default_tz: float = 7.0, reports_dir: str = REPORTS_DIR):
        self.default_tz = default_tz
        self.reports_dir = reports_dir
        self.state = ConversationState()

    def reset_state(self):
        """Reset conversation session state."""
        self.state = ConversationState()

    def save_report(self, content: str, filename: Optional[str] = None) -> str:
        """Saves report content to 'reports/' directory using UTF-8 encoding."""
        loc_name = "solar_report"
        if self.state.current_location:
            loc_name = f"solar_{self.state.current_location.clean_search_term}"
        return save_report_file(content, filename=filename, default_stem=loc_name, reports_dir=self.reports_dir)

    def save_json_report(self, data: Dict[str, Any], filename: Optional[str] = None) -> str:
        """Saves structured data as JSON to 'reports/' directory using UTF-8 encoding."""
        loc_name = "solar_report"
        if self.state.current_location:
            loc_name = f"solar_{self.state.current_location.clean_search_term}"
        return save_json_file(data, filename=filename, default_stem=loc_name, reports_dir=self.reports_dir)

    def extract_intent(self, query: str) -> str:
        """
        Determines what the user is asking for:
        - 'sunrise' (พระอาทิตย์ขึ้น, ตะวันขึ้น, รุ่งอรุณ)
        - 'sunset' (พระอาทิตย์ตก, ตะวันตก, ตกดิน, พลบค่ำ)
        - 'noon' (เที่ยงวัน, เที่ยงตรง, เที่ยงจริง, solar noon)
        - 'twilight' (แสงสนธยา, ทไวไลท์)
        - 'daylength' (ความยาววัน, กลางวันยาว)
        - 'all' (ภาพรวม / ทั่วไป)
        """
        q = query.lower()

        # Sunrise check
        has_sunrise = any(w in q for w in ["ขึ้น", "sunrise", "รุ่งอรุณ", "เช้า", "สว่าง"])
        has_sunset = any(w in q for w in ["ตก", "sunset", "พลบค่ำ", "ค่ำ", "มืด", "ตกดิน"])
        has_noon = any(w in q for w in ["เที่ยง", "noon", "เที่ยงวัน", "เที่ยงจริง", "สูงสุด"])

        # If user mentions both or neither, return 'all'
        if has_sunrise and has_sunset:
            return "all"
        if has_sunrise:
            return "sunrise"
        if has_sunset:
            return "sunset"
        if has_noon:
            return "noon"
        if "สนธยา" in q or "twilight" in q:
            return "twilight"
        if "ความยาว" in q or "ยาวกี่" in q or "day length" in q:
            return "daylength"

        return "all"

    def extract_location_text(self, query: str) -> Optional[str]:
        """
        Extracts location name or coordinate string from query text.
        Strips away date expressions, questions, and conversational particles.
        """
        # 1. Coordinates first
        coords = parse_coordinates_from_text(query)
        if coords:
            return f"{coords[0]}, {coords[1]}"

        # 2. Check for specific landmarks and districts first (highest specificity)
        LANDMARK_AMPHOE_KEYS = [
            "ผาแต้ม", "แหลมพรหมเทพ", "ดอยอินทนนท์", "แม่สาย", "เบตง", "บ้านโป่ง",
            "อ.บ้านโป่ง", "อำเภอบ้านโป่ง", "เมืองราชบุรี", "พัทยา", "หัวหิน", "เกาะสมุย",
            "หาดใหญ่", "เกาะกูด", "หาดป่าตอง", "ดอยเสมอดาว", "อ่าวมาหยา", "บางกรวย"
        ]
        for lk in LANDMARK_AMPHOE_KEYS:
            if lk in query:
                # If district is followed by province (e.g. "บ้านโป่ง ราชบุรี" or "บางกรวย นนทบุรี")
                m_prov = re.search(rf'{lk}\s*(?:จ\.|จังหวัด)?\s*([^\s,;?!]+)', query)
                if m_prov and m_prov.group(1):
                    cand_prov = m_prov.group(1).strip()
                    # ensure cand_prov is not a date or question word
                    if not any(w in cand_prov for w in ["วัน", "เมื่อ", "เดือน", "ปี", "กี่โมง", "เท่า"]):
                        return f"{lk} {cand_prov}"
                return lk

        # 3. Extract after location prepositions: ที่, ใน, แถว, ณ, แห่ง, พิกัด
        patterns = [
            r'(?<!เ)(?<!ทิต)(?<!สถาน)(?<!แผน)(?<!พื้น)(?<!หน้า)(?:ที่|ใน|แถว|ณ|แห่ง)\s*([^\s,;?!\d]+(?:\s+[^\s,;?!\d]+)?)',
            r'(?:อำเภอ|อ\.)\s*([^\s,;?!]+(?:\s+[^\s,;?!]+)?)',
            r'(?:จังหวัด|จ\.)\s*([^\s,;?!]+)',
            r'(?:พิกัด|ละติจูด|latitude)\s*([^\s,;?!]+(?:\s+[^\s,;?!]+)?)',
        ]
        for pat in patterns:
            match = re.search(pat, query)
            if match:
                cand = match.group(1).strip()
                # Clean filler words & date terms:
                cand = re.sub(
                    r'(?:\s+)?(?:วัน(?:ที่|นี้|พรุ่งนี้|เสาร์|อาทิตย์|จันทร์|อังคาร|พุธ|พฤหัส|ศุกร์)?|พรุ่งนี้|เมื่อวาน|เดือน|ปี|พ\.?ศ\.?|ค\.?ศ\.?|ครับ|ค่ะ|หน่อย|บ้าง|นะ|กี่โมง|เท่าไหร่|เวลา).*$',
                    '', cand, flags=re.IGNORECASE
                ).strip()
                if cand and len(cand) >= 2:
                    return cand

        # 4. Check for any preset location mention directly in query
        from noaaharness.geocoder import PRESET_LOCATIONS
        sorted_keys = sorted(PRESET_LOCATIONS.keys(), key=lambda x: len(x), reverse=True)
        for key in sorted_keys:
            if key in query:
                return key

        return None

    def query(
        self,
        user_input: str,
        short_answer: bool = False,
        verbose: bool = False,
        save_output: bool = False,
        output_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processes a user question and returns structured result + formatted Thai response.
        Supports saving output to 'reports/' directory in UTF-8 encoding.
        """
        q = user_input.strip()
        if not q:
            return {
                "error": "กรุณาใส่คำถามหรือข้อความที่ต้องการค้นหา",
                "response_text": "กรุณาใส่คำถาม เช่น 'พระอาทิตย์ขึ้นกี่โมงที่บ้านโป่ง วันที่ 27 มี.ค. 2565' หรือระบุพิกัด '13.8199, 99.8722'"
            }

        # 1. Detect Intent
        intent = self.extract_intent(q)

        # 2. Detect Date
        parsed_date, date_token = parse_thai_date(q, reference_date=self.state.current_date)
        self.state.current_date = parsed_date

        # 3. Detect Location
        loc_str = self.extract_location_text(q)
        if loc_str:
            resolved_loc = resolve_location(loc_str, default_tz=self.default_tz)
            self.state.current_location = resolved_loc
        elif self.state.current_location is None:
            # Check if query itself is a location or coordinate
            resolved_loc = resolve_location(q, default_tz=self.default_tz)
            self.state.current_location = resolved_loc

        loc = self.state.current_location

        # 4. Perform NOAA Solar Calculation
        res = calculate_solar(
            latitude=loc.latitude,
            longitude=loc.longitude,
            timezone_offset=loc.timezone_offset,
            year=parsed_date.year,
            month=parsed_date.month,
            day=parsed_date.day
        )

        # 5. Format Thai Response with Local Time, BE & CE, and Google Maps link
        if short_answer and intent in ["sunrise", "sunset", "noon"]:
            text_response = format_short_answer_thai(loc, res, intent)
        else:
            text_response = format_solar_response_thai(
                loc=loc,
                res=res,
                focus_event=intent if intent != "all" else None,
                verbose=verbose
            )

        # 6. Check if user wants to save output to reports/ directory (UTF-8)
        save_keywords = [
            "บันทึกไฟล์", "เซฟไฟล์", "บันทึกรายงาน", "เซฟรายงาน",
            "บันทึกลงไฟล์", "เซฟลงไฟล์", "save report", "save file",
            "save to file", "export report", "บันทึกผล", "เซฟผล"
        ]
        wants_save = save_output or any(k in q.lower() for k in save_keywords)
        target_filename = output_filename
        if not target_filename:
            m_file = re.search(
                r'(?:ไฟล์|ชื่อ|เป็น|filename|to)\s*[:=]?\s*([a-zA-Z0-9_\-\u0e00-\u0e7f]+\.(?:md|txt|json|html))',
                q, re.IGNORECASE
            )
            if m_file:
                target_filename = m_file.group(1).strip()

        saved_file_path = None
        if wants_save:
            loc_stem = f"solar_{loc.clean_search_term}" if loc else "solar_report"
            is_json_target = bool(target_filename and target_filename.lower().endswith(".json")) or ("json" in q.lower() and "บันทึก" in q)
            if is_json_target:
                full_data = {
                    "query": q,
                    "location": {
                        "name": loc.display_name,
                        "latitude": loc.latitude,
                        "longitude": loc.longitude,
                        "timezone_offset": loc.timezone_offset,
                        "google_maps_url": loc.google_maps_url,
                        "source": loc.source,
                    },
                    "date": {
                        "year_ce": parsed_date.year,
                        "year_be": parsed_date.year + 543,
                        "month": parsed_date.month,
                        "day": parsed_date.day,
                        "formatted_thai": format_date_thai(parsed_date.year, parsed_date.month, parsed_date.day),
                    },
                    "solar_result": res.to_dict(),
                    "response_text": text_response
                }
                saved_file_path = save_json_file(full_data, filename=target_filename, default_stem=loc_stem, reports_dir=self.reports_dir)
            else:
                saved_file_path = save_report_file(text_response, filename=target_filename, default_stem=loc_stem, reports_dir=self.reports_dir)

            text_response += f"\n\n💾 **บันทึกรายงานเรียบร้อยแล้ว**: `{saved_file_path}` *(การเข้ารหัส UTF-8 ในโฟลเดอร์ reports/)*"

        # Save to history
        self.state.query_history.append({
            "query": q,
            "intent": intent,
            "location": loc.display_name,
            "coordinates": [loc.latitude, loc.longitude],
            "date": parsed_date.isoformat(),
            "google_maps_url": loc.google_maps_url,
            "saved_file": saved_file_path
        })

        return {
            "query": q,
            "intent": intent,
            "location": {
                "name": loc.display_name,
                "latitude": loc.latitude,
                "longitude": loc.longitude,
                "timezone_offset": loc.timezone_offset,
                "google_maps_url": loc.google_maps_url,
                "source": loc.source,
                "is_fallback": loc.is_fallback,
                "fallback_reason": loc.fallback_reason,
                "nearest_preset": loc.nearest_preset_name,
                "distance_km": loc.distance_km,
            },
            "date": {
                "year_ce": parsed_date.year,
                "year_be": parsed_date.year + 543,
                "month": parsed_date.month,
                "day": parsed_date.day,
                "formatted_thai": format_date_thai(parsed_date.year, parsed_date.month, parsed_date.day),
            },
            "solar_result": res.to_dict(),
            "saved_file": saved_file_path,
            "response_text": text_response
        }
