"""
Thai Date Parser & Dual Era (พ.ศ. / ค.ศ.) Formatter
Supports:
- Thai full month names & abbreviations (มีนาคม, มี.ค.)
- Buddhist Era (พ.ศ.) <-> Christian Era (ค.ศ.) conversion
- Relative words: วันนี้, พรุ่งนี้, มะรืนนี้, เมื่อวาน
- Numeric date formats: YYYY-MM-DD, DD/MM/YYYY, DD/MM/YY
"""

import re
import datetime
from typing import Optional, Tuple, Dict, Any

THAI_MONTHS = [
    "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
]

THAI_MONTHS_SHORT = [
    "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
    "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."
]

THAI_MONTH_LOOKUP: Dict[str, int] = {}
for idx, name in enumerate(THAI_MONTHS, start=1):
    THAI_MONTH_LOOKUP[name] = idx
    # variations without periods for short names
for idx, short in enumerate(THAI_MONTHS_SHORT, start=1):
    THAI_MONTH_LOOKUP[short] = idx
    clean_short = short.replace(".", "")
    THAI_MONTH_LOOKUP[clean_short] = idx
    THAI_MONTH_LOOKUP[clean_short + "."] = idx

# English months
ENG_MONTHS = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december"
]
ENG_MONTHS_SHORT = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
for idx, name in enumerate(ENG_MONTHS, start=1):
    THAI_MONTH_LOOKUP[name] = idx
for idx, short in enumerate(ENG_MONTHS_SHORT, start=1):
    THAI_MONTH_LOOKUP[short] = idx

THAI_WEEKDAYS = [
    "วันจันทร์", "วันอังคาร", "วันพุธ", "วันพฤหัสบดี", "วันศุกร์", "วันเสาร์", "วันอาทิตย์"
]


def convert_to_ce(year: int) -> int:
    """
    Converts input year to Christian Era (ค.ศ.).
    - If year >= 2400: assumes Buddhist Era (พ.ศ.), subtracts 543.
    - If 40 <= year < 100: assumes 2-digit พ.ศ. (e.g. 65 -> 2565 -> 2022).
    - If 0 <= year < 40: assumes 2-digit ค.ศ. (e.g. 26 -> 2026).
    - Otherwise returns year as is (already ค.ศ.).
    """
    if year >= 2400:
        return year - 543
    elif 40 <= year < 100:
        return (2500 + year) - 543
    elif 0 <= year < 40:
        return 2000 + year
    return year


def convert_ce_to_be(year_ce: int) -> int:
    """Converts Christian Era (ค.ศ.) to Buddhist Era (พ.ศ.)."""
    return year_ce + 543


def format_date_thai(
    year_ce: int,
    month: int,
    day: int,
    include_weekday: bool = True,
    include_ce: bool = True
) -> str:
    """
    Formats date with day of week, Thai month, and both พ.ศ. and ค.ศ.
    Example: 'วันอาทิตย์ที่ 27 มีนาคม พ.ศ. 2565 (ค.ศ. 2022)'
    """
    dt = datetime.date(year_ce, month, day)
    weekday_str = f"{THAI_WEEKDAYS[dt.weekday()]}ที่ " if include_weekday else ""
    month_str = THAI_MONTHS[month - 1]
    year_be = convert_ce_to_be(year_ce)
    ce_suffix = f" (ค.ศ. {year_ce})" if include_ce else ""
    return f"{weekday_str}{day} {month_str} พ.ศ. {year_be}{ce_suffix}"


def parse_thai_date(
    text: str,
    reference_date: Optional[datetime.date] = None
) -> Tuple[datetime.date, str]:
    """
    Parses date from arbitrary text.
    Returns (datetime.date, matched_token_or_source).
    If no date found in text, defaults to reference_date (or today).
    """
    ref = reference_date or datetime.date.today()
    t = text.strip().lower()

    # 1. Relative Thai date words
    if "มะรืน" in t:
        d = ref + datetime.timedelta(days=2)
        return d, "มะรืนนี้"
    elif "พรุ่งนี้" in t:
        d = ref + datetime.timedelta(days=1)
        return d, "วันพรุ่งนี้"
    elif "เมื่อวาน" in t:
        d = ref - datetime.timedelta(days=1)
        return d, "เมื่อวานนี้"
    elif "วันนี้" in t:
        return ref, "วันนี้"

    # 2. Text month pattern: e.g. "27 มีนาคม 2565", "27 มี.ค. 65", "27 มีนาคม"
    # Build regex from all month names and abbreviations
    month_keys = sorted(THAI_MONTH_LOOKUP.keys(), key=lambda x: len(x), reverse=True)
    # Escape dots for regex
    escaped_keys = [re.escape(k) for k in month_keys]
    month_regex = "|".join(escaped_keys)

    pattern_text_month = rf'(?:วันที่\s*)?(\d{{1,2}})\s*(?:เดือน\s*)?({month_regex})\s*(?:พ\.?ศ\.?|ค\.?ศ\.?)?\s*(\d{{2,4}})?'
    match_tm = re.search(pattern_text_month, t)
    if match_tm:
        day = int(match_tm.group(1))
        m_str = match_tm.group(2)
        month = THAI_MONTH_LOOKUP.get(m_str) or 1
        y_str = match_tm.group(3)
        if y_str:
            raw_year = int(y_str)
            year_ce = convert_to_ce(raw_year)
        else:
            year_ce = ref.year
        try:
            parsed_date = datetime.date(year_ce, month, day)
            return parsed_date, match_tm.group(0)
        except ValueError:
            pass

    # 3. Numeric ISO date: YYYY-MM-DD
    match_iso = re.search(r'\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b', t)
    if match_iso:
        raw_y = int(match_iso.group(1))
        m = int(match_iso.group(2))
        d = int(match_iso.group(3))
        year_ce = convert_to_ce(raw_y)
        try:
            parsed_date = datetime.date(year_ce, m, d)
            return parsed_date, match_iso.group(0)
        except ValueError:
            pass

    # 4. Numeric DD/MM/YYYY or DD-MM-YYYY
    match_dmy = re.search(r'\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})\b', t)
    if match_dmy:
        d = int(match_dmy.group(1))
        m = int(match_dmy.group(2))
        raw_y = int(match_dmy.group(3))
        year_ce = convert_to_ce(raw_y)
        try:
            parsed_date = datetime.date(year_ce, m, d)
            return parsed_date, match_dmy.group(0)
        except ValueError:
            pass

    # Default fallback: reference date (today)
    return ref, "วันนี้ (ค่าเริ่มต้น)"
