#!/usr/bin/env python3
"""
NOAA Solar Calculator Harness
Main entrypoint for Thai Q&A, Solar Calculations, and Evaluation Benchmark.

Usage Examples:
  # 1. Interactive Q&A in Thai:
  python harness.py

  # 2. Single-shot Thai query:
  python harness.py "พระอาทิตย์ขึ้นที่อำเภอบ้านโป่ง วันที่ 27 มีนาคม 2565 กี่โมง"
  python harness.py "พิกัด 13.8199, 99.8722 พระอาทิตย์ตกกี่โมง"
  python harness.py "พรุ่งนี้เที่ยงวันจริงที่เชียงใหม่เวลาเท่าไหร่"

  # 3. Parametric query:
  python harness.py --location "เชียงใหม่" --date "2026-09-07"
  python harness.py --lat 13.8199 --lon 99.8722 --date "27 มี.ค. 2565" --json

  # 4. Generate Monthly Table (similar to index.html monthTable):
  python harness.py --location "บ้านโป่ง" --month-table

  # 5. Run Evaluation Benchmark:
  python harness.py --eval

  # 6. Launch Web Server & Thai Chat UI:
  python harness.py --serve --port 8080
"""

import sys
import json
import argparse
import datetime

from noaaharness.agent import SolarAgentHarness
from noaaharness.solar_engine import (
    calculate_solar,
    minutes_to_hm,
    minutes_to_hms,
    minutes_to_duration_th
)
from noaaharness.geocoder import resolve_location
from noaaharness.date_parser import parse_thai_date, format_date_thai, THAI_MONTHS, THAI_WEEKDAYS
from noaaharness.formatter import format_solar_response_thai
from noaaharness.evaluation import run_eval_suite
from noaaharness.web_server import start_server


def interactive_mode():
    """Starts interactive Thai Q&A REPL session."""
    agent = SolarAgentHarness()
    print("=" * 72)
    print("☀️  NOAA Solar Calculator Harness — ระบบถาม-ตอบภาษาไทย")
    print("    อ้างอิงอัลกอริทึม Jean Meeus NOAA Solar Calculator (±1 นาที)")
    print("    แสดงผล: Local Time | พ.ศ. และ ค.ศ. | ลิงก์ Google Maps")
    print("=" * 72)
    print("💡 ตัวอย่างคำถาม:")
    print("  • 'พระอาทิตย์ขึ้นที่อำเภอบ้านโป่ง วันที่ 27 มีนาคม 2565 กี่โมง'")
    print("  • 'คำนวณดวงอาทิตย์ที่พิกัด 13.8199, 99.8722'")
    print("  • 'พรุ่งนี้พระอาทิตย์ตกที่เชียงใหม่กี่โมง'")
    print("  • 'เที่ยงวันจริงที่กรุงเทพฯ วันนี้'")
    print("  • 'ผาแต้ม อุบลราชธานี วันนี้'")
    print("  • พิมพ์ 'exit', 'quit', หรือ 'ออก' เพื่อจบการทำงาน")
    print("-" * 72)

    last_result = None
    while True:
        try:
            user_input = input("\n👤 ถาม: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q", "ออก", "บาย"):
                print("👋 ลาก่อนครับ ขอให้มีวันที่สดใสและแสงแดดอบอุ่น!")
                break
            if user_input.lower() in ("help", "ช่วยเหลือ", "?"):
                print("💡 คุณสามารถพิมพ์ชื่อสถานที่ (เช่น 'เชียงใหม่', 'ภูเก็ต'), พิกัด (เช่น '13.8199, 99.8722'), หรือวันที่ (เช่น '27 มี.ค. 2565') ได้ทันทีครับ")
                print("💡 พิมพ์ 'save' หรือ 'บันทึก' เพื่อเซฟผลลัพธ์ล่าสุดลงโฟลเดอร์ reports/ (UTF-8)")
                continue

            # Command to save the last result directly
            if user_input.lower() in ("save", "เซฟ", "บันทึก", "save report", "เซฟไฟล์", "บันทึกไฟล์"):
                if last_result and "response_text" in last_result:
                    saved_path = agent.save_report(last_result["response_text"])
                    print(f"\n💾 บันทึกผลการคำนวณล่าสุดเรียบร้อยแล้วที่: {saved_path} (UTF-8)")
                    print("-" * 72)
                    continue
                else:
                    print("\n⚠️ ยังไม่มีผลการคำนวณล่าสุดให้บันทึก กรุณาถามคำถามก่อนครับ")
                    print("-" * 72)
                    continue

            result = agent.query(user_input)
            last_result = result
            print("\n" + result["response_text"])
            print("-" * 72)

        except (KeyboardInterrupt, EOFError):
            print("\n👋 จบการทำงาน")
            break


def print_month_table(location_str: str, year: int, month: int, output_file: Optional[str] = None):
    """Prints full month solar calendar matching monthTable() in index.html, optionally saving to reports/."""
    loc = resolve_location(location_str)
    # Get days in month
    import calendar
    _, num_days = calendar.monthrange(year, month)

    date_title = f"เดือน {THAI_MONTHS[month - 1]} พ.ศ. {year + 543} (ค.ศ. {year})"
    lines = []
    lines.append(f"📊 ตารางเวลาดวงอาทิตย์ทั้งเดือน — {loc.display_name}")
    lines.append(f"📅 {date_title} | ละติจูด {loc.latitude:.4f}°, ลองจิจูด {loc.longitude:.4f}° | UTC+{loc.timezone_offset:g}")
    lines.append(f"🗺️ Google Maps: {loc.google_maps_url}\n")

    header = f"| วันที่ | วัน | ขึ้น (Rise) | ตก (Set) | เที่ยงจริง (Noon) | ความยาววัน | เดคลิเนชัน (δ) | EoT (นาที) |"
    sep = f"| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    lines.append(header)
    lines.append(sep)

    TH_SHORT_DAY = ["จันทร์", "อังคาร", "พุธ", "พฤหัส", "ศุกร์", "เสาร์", "อาทิตย์"]
    for d in range(1, num_days + 1):
        dt = datetime.date(year, month, d)
        wday = TH_SHORT_DAY[dt.weekday()]
        res = calculate_solar(loc.latitude, loc.longitude, loc.timezone_offset, year, month, d)
        rise_str = minutes_to_hm(res.sunrise_min)
        set_str = minutes_to_hm(res.sunset_min)
        noon_str = minutes_to_hm(res.solar_noon_min)
        len_str = minutes_to_duration_th(res.day_length_min)
        dec_str = f"{res.solar_declination:+.2f}°"
        eot_str = f"{res.equation_of_time:+.2f}"
        lines.append(f"| {d:02d} | {wday:^7s} | {rise_str} น. | {set_str} น. | {noon_str} น. | {len_str} | {dec_str} | {eot_str} |")

    table_text = "\n".join(lines)
    print("\n" + table_text + "\n")

    if output_file:
        from noaaharness.agent import save_report_file
        stem = f"month_table_{loc.clean_search_term}_{year}_{month:02d}"
        target = None if output_file == "AUTO" else output_file
        saved_path = save_report_file(table_text, filename=target, default_stem=stem, reports_dir="reports")
        print(f"💾 บันทึกตารางดวงอาทิตย์ทั้งเดือนเรียบร้อยแล้ว: {saved_path} (UTF-8)\n")


def main():
    parser = argparse.ArgumentParser(
        description="NOAA Solar Calculator Harness (Jean Meeus algorithm) - Thai Q&A, Local Time, BE/CE, Google Maps"
    )
    parser.add_argument("query", nargs="?", help="ข้อความคำถามภาษาไทย เช่น 'พระอาทิตย์ขึ้นที่บ้านโป่ง วันที่ 27 มี.ค. 2565'")
    parser.add_argument("-i", "--interactive", action="store_true", help="เปิดโหมดถาม-ตอบแบบโต้ตอบ (Interactive REPL)")
    parser.add_argument("-l", "--location", help="ระบุชื่อสถานที่หรือพิกัด เช่น 'บ้านโป่ง' หรือ '13.8199, 99.8722'")
    parser.add_argument("--lat", type=float, help="ระบุละติจูด (องศาเหนือ +)")
    parser.add_argument("--lon", type=float, help="ระบุลองจิจูด (องศาตะวันออก +)")
    parser.add_argument("-d", "--date", help="ระบุวันที่ เช่น '2022-03-27' หรือ '27 มีนาคม 2565'")
    parser.add_argument("--tz", type=float, default=7.0, help="เขตเวลา UTC offset (ค่าเริ่มต้น +7 สำหรับไทย)")
    parser.add_argument("--json", action="store_true", help="ส่งออกผลลัพธ์เป็นโครงสร้าง JSON")
    parser.add_argument("--short", action="store_true", help="ตอบแบบสรุปสั้น 1 ประโยค")
    parser.add_argument("--verbose", action="store_true", help="แสดงผลตัวแปรทางดาราศาสตร์ 12 ขั้นตอน")
    parser.add_argument("--month-table", action="store_true", help="สร้างตารางเวลาดวงอาทิตย์ทั้งเดือน")
    parser.add_argument("-o", "--output", "--save", nargs="?", const="AUTO", help="บันทึกผลลัพธ์ลงไฟล์ในโฟลเดอร์ reports/ (เข้ารหัส UTF-8 เสมอ)")
    parser.add_argument("--eval", action="store_true", help="รันชุดทดสอบ Agent Evaluation Benchmark Suite")
    parser.add_argument("--serve", "--web", action="store_true", help="เปิด Local Web Server และเว็บแชท UI")
    parser.add_argument("--port", type=int, default=8080, help="พอร์ตสำหรับ Web Server (ค่าเริ่มต้น 8080)")

    args = parser.parse_args()

    # 1. Run Evaluation Benchmark
    if args.eval:
        run_eval_suite(verbose=True)
        return

    # 2. Launch Web Server
    if args.serve:
        start_server(port=args.port)
        return

    # 3. Monthly Table
    if args.month_table:
        loc_str = args.location or (f"{args.lat},{args.lon}" if args.lat is not None and args.lon is not None else "บ้านโป่ง")
        if args.date:
            dt, _ = parse_thai_date(args.date)
        else:
            dt = datetime.date.today()
        print_month_table(loc_str, dt.year, dt.month, output_file=args.output)
        return

    # 4. Parametric inputs (lat/lon or location + date)
    if args.lat is not None and args.lon is not None:
        if args.date:
            dt, _ = parse_thai_date(args.date)
        else:
            dt = datetime.date.today()
        loc = resolve_location(f"{args.lat}, {args.lon}", default_tz=args.tz)
        res = calculate_solar(args.lat, args.lon, loc.timezone_offset, dt.year, dt.month, dt.day)

        if args.json:
            out = {
                "location": {"name": loc.display_name, "latitude": loc.latitude, "longitude": loc.longitude, "google_maps_url": loc.google_maps_url},
                "date": {"year_ce": dt.year, "year_be": dt.year + 543, "month": dt.month, "day": dt.day, "formatted": format_date_thai(dt.year, dt.month, dt.day)},
                "solar_result": res.to_dict()
            }
            if args.output:
                from noaaharness.agent import save_json_file
                stem = f"solar_coord_{args.lat:.4f}_{args.lon:.4f}_{dt.year}{dt.month:02d}{dt.day:02d}"
                target = None if args.output == "AUTO" else args.output
                saved = save_json_file(out, filename=target, default_stem=stem, reports_dir="reports")
                out["saved_file"] = saved
            print(json.dumps(out, ensure_ascii=False, indent=2))
        else:
            resp_text = format_solar_response_thai(loc, res, verbose=args.verbose)
            if args.output:
                from noaaharness.agent import save_report_file
                stem = f"solar_coord_{args.lat:.4f}_{args.lon:.4f}_{dt.year}{dt.month:02d}{dt.day:02d}"
                target = None if args.output == "AUTO" else args.output
                saved = save_report_file(resp_text, filename=target, default_stem=stem, reports_dir="reports")
                resp_text += f"\n\n💾 **บันทึกรายงานเรียบร้อยแล้ว**: `{saved}` *(การเข้ารหัส UTF-8 ในโฟลเดอร์ reports/)*"
            print(resp_text)
        return

    # 5. Single Question Query via command line
    if args.query:
        agent = SolarAgentHarness(default_tz=args.tz)
        result = agent.query(
            args.query,
            short_answer=args.short,
            verbose=args.verbose,
            save_output=bool(args.output),
            output_filename=args.output if args.output != "AUTO" else None
        )
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result["response_text"])
        return

    # 6. Specific location argument
    if args.location:
        agent = SolarAgentHarness(default_tz=args.tz)
        q_str = f"คำนวณเวลาดวงอาทิตย์ที่ {args.location}"
        if args.date:
            q_str += f" วันที่ {args.date}"
        result = agent.query(
            q_str,
            short_answer=args.short,
            verbose=args.verbose,
            save_output=bool(args.output),
            output_filename=args.output if args.output != "AUTO" else None
        )
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result["response_text"])
        return

    # 7. No arguments or --interactive -> Start Interactive REPL
    interactive_mode()


if __name__ == "__main__":
    main()
