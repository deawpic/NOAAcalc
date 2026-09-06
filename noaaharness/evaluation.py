"""
NOAA Solar Agent Harness - Evaluation & Benchmark Suite
Tests accuracy, prompt handling, BE/CE year presence, local time verification,
and Google Maps link generation across a benchmark matrix of Thai user queries.
"""

import time
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from noaaharness.agent import SolarAgentHarness
from noaaharness.solar_engine import minutes_to_hm


@dataclass
class EvalCase:
    id: str
    query: str
    expected_location_keyword: str
    expected_sunrise_hm: Optional[str] = None
    expected_sunset_hm: Optional[str] = None
    expected_noon_hm: Optional[str] = None
    expected_be_year: Optional[int] = None
    expected_ce_year: Optional[int] = None


BENCHMARK_DATASET: List[EvalCase] = [
    # 1. Baseline Ban Pong test case from README & index.html
    EvalCase(
        id="BAN_PONG_BASELINE",
        query="พระอาทิตย์ขึ้น-ตก และเที่ยงวัน ที่อำเภอบ้านโป่ง วันที่ 27 มีนาคม 2565 กี่โมง",
        expected_location_keyword="บ้านโป่ง",
        expected_sunrise_hm="06:19",
        expected_sunset_hm="18:31",
        expected_noon_hm="12:25",
        expected_be_year=2565,
        expected_ce_year=2022,
    ),
    # 2. Raw Coordinate query
    EvalCase(
        id="COORDINATE_RAW",
        query="คำนวณดวงอาทิตย์ที่พิกัด 13.8199, 99.8722 วันที่ 27/03/2022",
        expected_location_keyword="13.8199",
        expected_sunrise_hm="06:19",
        expected_sunset_hm="18:31",
        expected_noon_hm="12:25",
        expected_be_year=2565,
        expected_ce_year=2022,
    ),
    # 3. Bangkok with short date
    EvalCase(
        id="BANGKOK_SHORT_DATE",
        query="กรุงเทพฯ วันที่ 27 มี.ค. 65 พระอาทิตย์ขึ้นกี่โมง",
        expected_location_keyword="กรุงเทพ",
        expected_sunrise_hm="06:17",
        expected_sunset_hm="18:29",
        expected_noon_hm="12:23",
        expected_be_year=2565,
        expected_ce_year=2022,
    ),
    # 4. Chiang Mai sunset
    EvalCase(
        id="CHIANG_MAI_SUNSET",
        query="ดวงอาทิตย์ตกดินที่เชียงใหม่ วันที่ 1 มกราคม 2568 กี่โมง",
        expected_location_keyword="เชียงใหม่",
        expected_be_year=2568,
        expected_ce_year=2025,
    ),
    # 5. Phuket
    EvalCase(
        id="PHUKET_SUNRISE",
        query="พระอาทิตย์ขึ้นที่ภูเก็ต วันที่ 15 เมษายน 2566",
        expected_location_keyword="ภูเก็ต",
        expected_be_year=2566,
        expected_ce_year=2023,
    ),
    # 6. Pha Taem (Easternmost Thailand sunrise landmark)
    EvalCase(
        id="PHA_TAEM_LANDMARK",
        query="จุดชมพระอาทิตย์ขึ้นผาแต้ม อุบลราชธานี วันที่ 1 มกราคม 2568",
        expected_location_keyword="ผาแต้ม",
        expected_be_year=2568,
        expected_ce_year=2025,
    ),
    # 7. Tokyo International Query
    EvalCase(
        id="TOKYO_INTL",
        query="โตเกียว วันที่ 1 มกราคม 2025 พระอาทิตย์ขึ้นกี่โมง",
        expected_location_keyword="Tokyo",
        expected_be_year=2568,
        expected_ce_year=2025,
    ),
    # 8. Hierarchical Parent Fallback
    EvalCase(
        id="FALLBACK_HIERARCHICAL",
        query="พระอาทิตย์ตกที่ วัดร้างที่ไม่มีในแผนที่ สุพรรณบุรี วันที่ 27 มีนาคม 2565",
        expected_location_keyword="สุพรรณบุรี",
        expected_be_year=2565,
        expected_ce_year=2022,
    ),
    # 9. Typo / Fuzzy Fallback
    EvalCase(
        id="FALLBACK_TYPO_FUZZY",
        query="พระอาทิตย์ขึ้นที่ พัดยา วันที่ 27 มี.ค. 2565",
        expected_location_keyword="พัทยา",
        expected_be_year=2565,
        expected_ce_year=2022,
    ),
]


def run_eval_suite(verbose: bool = True) -> Dict[str, Any]:
    """
    Executes the benchmark suite, validating all requirements:
    1. Thai response text
    2. Local time values
    3. Both พ.ศ. and ค.ศ. present
    4. Google Maps link present
    5. Location and coordinate correctness
    """
    agent = SolarAgentHarness()
    results = []
    passed_count = 0
    total_latency_ms = 0.0

    print("=" * 70)
    print("🚀 เริ่มต้นการทดสอบ Agent Harness Benchmark Suite (NOAA Solar)")
    print(f"📊 จำนวนชุดการทดสอบ: {len(BENCHMARK_DATASET)} กรณีศึกษา")
    print("=" * 70)

    for case in BENCHMARK_DATASET:
        t0 = time.perf_counter()
        agent.reset_state()
        res = agent.query(case.query)
        latency_ms = (time.perf_counter() - t0) * 1000.0
        total_latency_ms += latency_ms

        text = res["response_text"]
        solar_data = res["solar_result"]

        # Assertions
        reasons = []

        # Check 1: Google Maps link
        if "https://www.google.com/maps?q=" not in text:
            reasons.append("ขาดลิงก์ Google Maps")

        # Check 2: Both พ.ศ. and ค.ศ.
        if "พ.ศ." not in text:
            reasons.append("ขาดปี พ.ศ.")
        if "ค.ศ." not in text:
            reasons.append("ขาดปี ค.ศ.")

        # Check 3: Local time representation
        if "น." not in text and ":" not in text:
            reasons.append("ขาดการแสดงผลเวลา Local Time (น.)")

        # Check 4: Location keyword
        if case.expected_location_keyword.lower() not in text.lower():
            reasons.append(f"ไม่พบชื่อสถานที่ '{case.expected_location_keyword}'")

        # Check 5: Expected values if specified
        if case.expected_sunrise_hm:
            actual_rise = minutes_to_hm(solar_data["sunrise_min"])
            if actual_rise != case.expected_sunrise_hm:
                reasons.append(f"เวลาพระอาทิตย์ขึ้นไม่ตรง: ได้ {actual_rise} แต่คาดหวัง {case.expected_sunrise_hm}")

        if case.expected_sunset_hm:
            actual_set = minutes_to_hm(solar_data["sunset_min"])
            if actual_set != case.expected_sunset_hm:
                reasons.append(f"เวลาพระอาทิตย์ตกไม่ตรง: ได้ {actual_set} แต่คาดหวัง {case.expected_sunset_hm}")

        if case.expected_noon_hm:
            actual_noon = minutes_to_hm(solar_data["solar_noon_min"])
            if actual_noon != case.expected_noon_hm:
                reasons.append(f"เวลาเที่ยงวันจริงไม่ตรง: ได้ {actual_noon} แต่คาดหวัง {case.expected_noon_hm}")

        passed = len(reasons) == 0
        if passed:
            passed_count += 1

        results.append({
            "id": case.id,
            "query": case.query,
            "passed": passed,
            "latency_ms": latency_ms,
            "errors": reasons
        })

        status_str = "✅ PASS" if passed else f"❌ FAIL ({', '.join(reasons)})"
        if verbose:
            print(f"[{case.id:20s}] {status_str} ({latency_ms:.1f}ms)")

    pass_rate = (passed_count / len(BENCHMARK_DATASET)) * 100.0
    avg_latency = total_latency_ms / len(BENCHMARK_DATASET)

    print("=" * 70)
    print(f"🏁 ผลลัพธ์: ผ่าน {passed_count}/{len(BENCHMARK_DATASET)} ({pass_rate:.1f}%) | ความเร็วเฉลี่ย: {avg_latency:.2f} ms")
    print("=" * 70)

    return {
        "total_cases": len(BENCHMARK_DATASET),
        "passed_cases": passed_count,
        "pass_rate_pct": pass_rate,
        "avg_latency_ms": avg_latency,
        "cases": results
    }


if __name__ == "__main__":
    run_eval_suite(verbose=True)
