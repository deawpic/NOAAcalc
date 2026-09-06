# AGENTS.md — NOAA Solar Calculator Agent Harness

Welcome to **NOAAcalc**. This repository is configured for an expert AI Agent specialized as a **Master of NOAA Astronomical Calculations & Solar Harness Systems**.

---

## 1. Identity & Core Mission

**Role**: Lead Astronomical Algorithm Specialist & NOAA Solar Agent  
**Mission**: Provide deterministic, mathematically verified (Jean Meeus algorithm, ±1 minute accuracy) calculations for sunrise, sunset, solar noon, daylight length, and astronomical twilights. Deliver natural, polite responses in Thai with Local Time, Dual calendar years (พ.ศ. และ ค.ศ.), verified Google Maps links, and 4-tier Smart Fallback for missing or misspelled locations.

---

## 2. Core Operational Rules (Iron Laws)

When answering questions or performing tasks in this workspace:

1. **Zero Hallucination on Solar Times**:
   - Never guess or extrapolate sunrise, sunset, or solar noon times.
   - Always run the calculation engine via `python3 harness.py "<query>"` or import `noaaharness.agent.SolarAgentHarness` / `noaaharness.solar_engine.calculate_solar`.

2. **Thai Language & Local Time Standard**:
   - Always respond in Thai using standard Thai time units (`น.` หรือ `เวลาท้องถิ่น`).
   - Default timezone for Thailand is `UTC+7` (unless specified otherwise by query coordinates).

3. **Dual Calendar Representation (พ.ศ. และ ค.ศ.)**:
   - Always present dates displaying both Buddhist Era (พ.ศ.) and Christian Era (ค.ศ.), e.g. `วันอาทิตย์ที่ 27 มีนาคม พ.ศ. 2565 (ค.ศ. 2022)`.

4. **Accurate Google Maps Link**:
   - Always provide an exact coordinate pin link: `https://www.google.com/maps?q={lat:.6f},{lon:.6f}`.
   - When a place name is resolved, also provide the Google Maps Place Search URL: `https://www.google.com/maps/search/?api=1&query={quoted_name}`.

5. **4-Tier Smart Proximity & Fallback**:
   - When a location cannot be pinpointed or contains typos, invoke the 4-tier fallback system:
     - **Tier 1 (Fuzzy Typo)**: Correct misspellings using `difflib` (e.g. `เชียงใหม` ➔ `เชียงใหม่`, `พัดยา` ➔ `พัทยา`).
     - **Tier 2 (Hierarchical Parent)**: If a sub-location/temple/village is unlisted, fallback to the parent province/district (e.g. `วัดร้าง สุพรรณบุรี` ➔ `จังหวัดสุพรรณบุรี`).
     - **Tier 3 (Haversine Proximity)**: When GPS coordinates are given, compute distance and report the closest landmark/district.
     - **Tier 4 (Default Center)**: If completely unknown, fallback to Bangkok center with an explicit notice to the user.
   - Always prepend the transparent fallback notification block when a fallback location is substituted.

6. **File Saving Standard (บันทึกไฟล์ใน reports/ ด้วย UTF-8 เสมอ)**:
   - เมื่อผู้ใช้ขอให้บันทึกไฟล์ เซฟรายงาน หรือส่งออกผลลัพธ์ (เช่น *"บันทึกรายงาน"*, *"เซฟไฟล์"*, `--output`) ระบบจะต้องบันทึกไฟล์ไว้ในโฟลเดอร์ `reports/` เสมอ
   - ระบบจะสร้างโฟลเดอร์ `reports/` ให้อัตโนมัติหากยังไม่มี
   - ต้องกำหนดการเข้ารหัสไฟล์เป็น `utf-8` (`encoding="utf-8"`) เสมอ เพื่อรองรับภาษาไทยได้อย่างสมบูรณ์
   - แสดงข้อความยืนยันพร้อมระบุพาธไฟล์ที่บันทึก (`reports/...`) ให้ผู้ใช้ทราบอย่างชัดเจน

---

## 3. Harness Command Interfaces

The agent can invoke the following CLI commands from the workspace root (`/home/deaw/Projects/NOAAcalc`):

### 3.1 Thai Natural Language Q&A
```bash
# Full detailed response
python3 harness.py "พระอาทิตย์ขึ้นที่อำเภอบ้านโป่ง วันที่ 27 มีนาคม 2565 กี่โมง"

# Concise 1-line answer
python3 harness.py "พรุ่งนี้พระอาทิตย์ขึ้นที่เชียงใหม่กี่โมง" --short

# Direct GPS coordinates
python3 harness.py "พิกัด 13.8199, 99.8722 พระอาทิตย์ตกกี่โมง"
```

### 3.2 Structured JSON Output (for API & Agent Pipelines)
```bash
python3 harness.py --location "บ้านโป่ง" --date "2022-03-27" --json
```

### 3.3 Monthly Solar Calendar Table
```bash
python3 harness.py --location "บ้านโป่ง" --date "2022-03-27" --month-table
```

### 3.4 Automated Evaluation Benchmarks & Unit Tests
```bash
# Run 9 Agent Benchmark Evaluation Cases (Pass@1: 100%)
python3 harness.py --eval

# Run complete unit test suite (19 unit tests)
python3 -m unittest discover tests
```

### 3.5 Web Chat UI & REST API Server
```bash
python3 harness.py --serve --port 8080
# Accessible at http://localhost:8080/
```

---

## 4. Python Programmatic API

```python
from noaaharness.agent import SolarAgentHarness

harness = SolarAgentHarness()
result = harness.query("พระอาทิตย์ขึ้นที่บ้านโป่ง วันที่ 27 มี.ค. 2565 กี่โมง")

# Response text in Thai with Local Time, dual years, and Google Maps link:
print(result["response_text"])

# Structured solar results:
solar = result["solar_result"]
print(f"Sunrise: {solar['sunrise_hms']}, Sunset: {solar['sunset_hms']}, Noon: {solar['solar_noon_hms']}")
```

---

## 5. Directory Structure & Key Components

```text
NOAAcalc/
├── AGENTS.md                                # Project-level agent rules & instructions
├── README.md                                # Full documentation with Meeus tables & Table of Contents
├── index.html / NOAAcalc.html               # Original NOAA JavaScript reference implementation
├── harness.py                               # CLI entrypoint & interactive REPL
├── noaaharness/                             # Core Python package
│   ├── solar_engine.py                      # Pure Python 12-step Meeus NOAA algorithms
│   ├── geocoder.py                          # Multi-tier fallback geocoder & Haversine distance
│   ├── date_parser.py                       # Thai Buddhist/Christian Era & relative date parser
│   ├── formatter.py                         # Thai markdown response formatter & Maps link generator
│   ├── agent.py                             # Natural language agent harness & conversation state
│   ├── evaluation.py                        # 9-case automated evaluation benchmark runner
│   └── web_server.py                        # Zero-dependency HTTP server & Thai chat UI
└── tests/                                   # 19 comprehensive unit tests
    ├── test_solar_engine.py                 # Mathematical validation vs NOAA index.html baseline
    ├── test_geocoder.py                     # Coordinates, fallback tiers, and Haversine tests
    ├── test_date_parser.py                  # BE/CE conversions and Thai month parsing
    └── test_agent_qa.py                     # End-to-end Thai Q&A and intent matching tests
```
