"""
Thai Response Formatter for NOAA Solar Harness
Formats output with:
- Dual calendar years: พ.ศ. and ค.ศ.
- Local time representations (HH:MM น. and HH:MM:SS น.)
- Location name & coordinates
- Google Maps link
- Astronomical twilights and NOAA 12-step diagnostics
"""

from typing import Optional
from noaaharness.solar_engine import (
    SolarCalculationResult,
    minutes_to_hms,
    minutes_to_hm,
    minutes_to_duration_th
)
from noaaharness.geocoder import LocationInfo
from noaaharness.date_parser import format_date_thai


def format_solar_response_thai(
    loc: LocationInfo,
    res: SolarCalculationResult,
    focus_event: Optional[str] = None,  # "sunrise", "sunset", "noon", or None (all)
    verbose: bool = False
) -> str:
    """
    Generate comprehensive, polite Thai response adhering to all user requirements:
    - Answers in Thai
    - Displays Local Time
    - Displays both Buddhist Era (พ.ศ.) and Christian Era (ค.ศ.)
    - Includes clickable Google Maps link
    """
    date_header = format_date_thai(res.year, res.month, res.day, include_weekday=True, include_ce=True)
    tz_str = f"UTC{'+' if res.timezone_offset >= 0 else ''}{res.timezone_offset:g}"

    lines = []
    if loc.is_fallback:
        lines.append(f"> ⚠️ **การค้นหาสถานที่ใกล้เคียง (Fallback Location)**")
        lines.append(f"> ไม่พบพิกัดที่แน่ชัดของ: **\"{loc.original_query}\"**")
        lines.append(f"> 📍 ระบบคำนวณโดยใช้พิกัดของสถานที่ใกล้เคียง: **{loc.display_name}**")
        if loc.fallback_reason:
            lines.append(f"> *(เหตุผล: {loc.fallback_reason})*")
        lines.append("")

    lines.append(f"☀️ **ผลการคำนวณเวลาดวงอาทิตย์ (NOAA Solar Calculator)**")
    lines.append(f"📅 **วันที่**: {date_header}")
    lines.append(f"📍 **สถานที่**: {loc.display_name}")
    if loc.nearest_preset_name and loc.distance_km is not None and loc.distance_km > 0.05 and loc.source == "coordinate":
        lines.append(f"🏘️ **จุดสังเกตใกล้เคียง**: {loc.nearest_preset_name} (ห่างประมาณ {loc.distance_km:.1f} กม.)")
    lines.append(f"🌐 **พิกัด**: ละติจูด {res.latitude:.4f}°N, ลองจิจูด {res.longitude:.4f}°E ({tz_str})")
    lines.append(f"🗺️ **Google Maps**: [เปิดดูพิกัดบน Google Maps]({loc.google_maps_url})")
    if loc.source != "coordinate":
        lines.append(f"📍 **ค้นหาสถานที่**: [เปิดดู '{loc.clean_search_term}' บน Google Maps]({loc.google_maps_place_url})")
    lines.append("")

    # If Polar Day or Night
    if res.is_polar_day:
        lines.append("⚠️ **ปรากฏการณ์พระอาทิตย์เที่ยงคืน (Polar Day)**: ดวงอาทิตย์อยู่เหนือขอบฟ้าตลอด 24 ชั่วโมง (ไม่มีเวลาขึ้น-ตก)")
        lines.append(f"• เที่ยงวันจริง (Solar Noon): **{minutes_to_hms(res.solar_noon_min)} น.** (เวลาท้องถิ่น)")
        return "\n".join(lines)
    elif res.is_polar_night:
        lines.append("⚠️ **ปรากฏการณ์คืนขั้วโลก (Polar Night)**: ดวงอาทิตย์อยู่ใต้ขอบฟ้าตลอด 24 ชั่วโมง (ไม่มีเวลาขึ้น-ตก)")
        lines.append(f"• เที่ยงวันจริง (Solar Noon): **{minutes_to_hms(res.solar_noon_min)} น.** (เวลาท้องถิ่น)")
        return "\n".join(lines)

    # If user focused on a specific event, highlight it at top
    if focus_event == "sunrise":
        lines.append(f"🌅 **เวลาพระอาทิตย์ขึ้น**: **{minutes_to_hm(res.sunrise_min)} น.** ({minutes_to_hms(res.sunrise_min)} น. เวลาท้องถิ่น)")
        lines.append(f"   (ทิศอะซิมุทขึ้น: {res.azimuth_rise_deg:.2f}°)")
    elif focus_event == "sunset":
        lines.append(f"🌇 **เวลาพระอาทิตย์ตก**: **{minutes_to_hm(res.sunset_min)} น.** ({minutes_to_hms(res.sunset_min)} น. เวลาท้องถิ่น)")
        lines.append(f"   (ทิศอะซิมุทตก: {res.azimuth_set_deg:.2f}°)")
    elif focus_event == "noon":
        lines.append(f"☀️ **เวลาเที่ยงวันจริง (Solar Noon)**: **{minutes_to_hm(res.solar_noon_min)} น.** ({minutes_to_hms(res.solar_noon_min)} น. เวลาท้องถิ่น)")
        lines.append(f"   (ดวงอาทิตย์อยู่จุดสูงสุดบนท้องฟ้า)")

    # Main Summary Table / Cards
    lines.append("### ⏱️ เวลาเหตุการณ์หลัก (เวลาท้องถิ่น Local Time)")
    lines.append(f"| เหตุการณ์ | เวลา (นาที:วินาที) | เวลาโดยประมาณ |")
    lines.append(f"| :--- | :---: | :---: |")
    lines.append(f"| 🌅 **ดวงอาทิตย์ขึ้น (Sunrise)** | **{minutes_to_hms(res.sunrise_min)} น.** | {minutes_to_hm(res.sunrise_min)} น. |")
    lines.append(f"| ☀️ **เที่ยงวันจริง (Solar Noon)** | **{minutes_to_hms(res.solar_noon_min)} น.** | {minutes_to_hm(res.solar_noon_min)} น. |")
    lines.append(f"| 🌇 **ดวงอาทิตย์ตก (Sunset)** | **{minutes_to_hms(res.sunset_min)} น.** | {minutes_to_hm(res.sunset_min)} น. |")
    lines.append(f"| ⏳ **ความยาวกลางวัน** | **{minutes_to_duration_th(res.day_length_min)}** | ({res.day_length_min:.1f} นาที) |")
    lines.append("")

    # Twilights & Directions
    lines.append("### 🌄 ช่วงแสงสนธยา (Twilight) และทิศทาง")
    lines.append(f"| ประเภทแสงสนธยา | ช่วงเช้า (รุ่งอรุณ) | ช่วงเย็น (พลบค่ำ) | มุมเซนิท |")
    lines.append(f"| :--- | :---: | :---: | :---: |")
    lines.append(f"| **สนธยาพลเรือน (Civil)** | {minutes_to_hms(res.civil_twilight_morning_min)} น. | {minutes_to_hms(res.civil_twilight_evening_min)} น. | 96° |")
    lines.append(f"| **สนธยาเดินเรือ (Nautical)** | {minutes_to_hms(res.nautical_twilight_morning_min)} น. | {minutes_to_hms(res.nautical_twilight_evening_min)} น. | 102° |")
    lines.append(f"| **สนธยาดาราศาสตร์ (Astronomical)** | {minutes_to_hms(res.astronomical_twilight_morning_min)} น. | {minutes_to_hms(res.astronomical_twilight_evening_min)} น. | 108° |")
    lines.append("")
    lines.append(f"• **ทิศทางดวงอาทิตย์ขึ้น**: {res.azimuth_rise_deg:.2f}° (0° = เหนือ, 90° = ตะวันออก)")
    lines.append(f"• **ทิศทางดวงอาทิตย์ตก**: {res.azimuth_set_deg:.2f}° (270° = ตะวันตก)")
    lines.append("")

    if verbose:
        lines.append("### 🧮 ตัวแปรดาราศาสตร์ 12 ขั้นตอน (Jean Meeus / NOAA)")
        lines.append(f"• Julian Day ณ เที่ยงวัน: `{res.julian_day_noon:.6f}`")
        lines.append(f"• Julian Century ($T$): `{res.julian_century:.9f}`")
        lines.append(f"• Solar Declination ($\\delta$): `{res.solar_declination:.4f}°`")
        lines.append(f"• Equation of Time ($EoT$): `{res.equation_of_time:.4f}` นาที")
        lines.append(f"• Hour Angle ($H$): `{res.hour_angle_deg:.4f}°`" if res.hour_angle_deg else "• Hour Angle: None")
        lines.append("")

    lines.append(f"🔗 ลิงก์แผนที่ Google Maps: {loc.google_maps_url}")
    if loc.source != "coordinate":
        lines.append(f"📍 ลิงก์ค้นหาสถานที่ Google Maps: {loc.google_maps_place_url}")
    return "\n".join(lines)


def format_short_answer_thai(
    loc: LocationInfo,
    res: SolarCalculationResult,
    event: str  # "sunrise", "sunset", "noon", "all"
) -> str:
    """A concise natural Thai answer for quick chatting."""
    date_header = format_date_thai(res.year, res.month, res.day, include_weekday=False, include_ce=True)
    fallback_note = ""
    if loc.is_fallback:
        fallback_note = f"⚠️ [หมายเหตุ: ไม่พบพิกัดเจาะจงของ \"{loc.original_query}\" จึงคำนวณโดยอิงจากสถานที่ใกล้เคียง: {loc.display_name}]\n"

    if event == "sunrise":
        return (
            f"{fallback_note}🌅 ในวันที่ {date_header} ที่ {loc.display_name} "
            f"พระอาทิตย์ขึ้นเวลา **{minutes_to_hm(res.sunrise_min)} น.** "
            f"(เวลาละเอียด {minutes_to_hms(res.sunrise_min)} น. local time)\n"
            f"🗺️ พิกัด Google Maps: {loc.google_maps_url}"
        )
    elif event == "sunset":
        return (
            f"{fallback_note}🌇 ในวันที่ {date_header} ที่ {loc.display_name} "
            f"พระอาทิตย์ตกเวลา **{minutes_to_hm(res.sunset_min)} น.** "
            f"(เวลาละเอียด {minutes_to_hms(res.sunset_min)} น. local time)\n"
            f"🗺️ พิกัด Google Maps: {loc.google_maps_url}"
        )
    elif event == "noon":
        return (
            f"{fallback_note}☀️ ในวันที่ {date_header} ที่ {loc.display_name} "
            f"เที่ยงวันจริง (Solar Noon) ตรงกับเวลา **{minutes_to_hm(res.solar_noon_min)} น.** "
            f"(เวลาละเอียด {minutes_to_hms(res.solar_noon_min)} น. local time)\n"
            f"🗺️ พิกัด Google Maps: {loc.google_maps_url}"
        )
    else:
        return format_solar_response_thai(loc, res)
