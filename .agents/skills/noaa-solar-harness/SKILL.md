---
name: noaa-solar-harness
description: >-
  Expert skill for calculating sunrise, sunset, solar noon, daylight duration, and astronomical twilights
  using the NOAA Jean Meeus 12-step algorithm (±1 minute baseline accuracy). Use when answering Thai natural
  language solar queries, resolving Thai places or coordinates, displaying dual years (พ.ศ./ค.ศ.), providing
  exact Google Maps pins, or triggering smart 4-tier fallback for missing or misspelled locations.
---

# NOAA Solar Calculator Harness Skill

This skill equips Antigravity with the capability to accurately calculate and explain solar phenomena (sunrise, sunset, solar noon, daylight length, astronomical twilights) based on the official NOAA / Jean Meeus 12-step astronomical algorithms, strictly maintaining ±1 minute baseline accuracy against `index.html`.

---

## 1. When to Activate This Skill

Activate this skill whenever the user:
- Asks for the time of sunrise, sunset, or solar noon in Thai or English (e.g. *"พระอาทิตย์ขึ้นกี่โมงที่บ้านโป่ง"*, *"พรุ่งนี้พระอาทิตย์ตกที่เชียงใหม่กี่โมง"*).
- Provides a location by name (provinces, districts, landmarks) or GPS coordinates (e.g. `13.8199, 99.8722`).
- Asks about daylight length or twilight times (Civil, Nautical, Astronomical).
- Needs solar time outputs formatted in Local Time with both Buddhist Era (พ.ศ.) and Christian Era (ค.ศ.).
- Requires clickable Google Maps links or smart fallback when locations are misspelled or missing from maps.

---

## 2. Command-Line Execution (CLI)

From the project root (`/home/deaw/Projects/NOAAcalc`):

### 2.1 Natural Language Query
```bash
# Detailed response with summary table and twilight breakdown
python3 harness.py "พระอาทิตย์ขึ้นที่อำเภอบ้านโป่ง วันที่ 27 มีนาคม 2565 กี่โมง"

# Concise single-line answer
python3 harness.py "พรุ่งนี้พระอาทิตย์ขึ้นที่เชียงใหม่กี่โมง" --short

# Direct GPS coordinates
python3 harness.py "พิกัด 13.8199, 99.8722 พระอาทิตย์ตกกี่โมง"
```

### 2.2 Save Reports to 'reports/' Directory (UTF-8)
```bash
# Automatically saves to reports/solar_{location}_{timestamp}.md using UTF-8:
python3 harness.py "พระอาทิตย์ขึ้นที่อำเภอบ้านโป่ง วันที่ 27 มีนาคม 2565 กี่โมง" -o

# Specify a custom filename (always placed safely inside reports/):
python3 harness.py "พระอาทิตย์ขึ้นที่เชียงใหม่ วันนี้" -o chiangmai_today.md

# Natural language trigger without flags:
python3 harness.py "พระอาทิตย์ขึ้นที่บ้านโป่ง วันที่ 27 มี.ค. 2565 และบันทึกรายงานลงไฟล์"
```

### 2.3 Structured JSON Output
```bash
python3 harness.py --location "บ้านโป่ง" --date "2022-03-27" --json
```

### 2.4 Monthly Solar Calendar Table
```bash
python3 harness.py --location "บ้านโป่ง" --date "2022-03-27" --month-table
# Save monthly table to reports/:
python3 harness.py --location "บ้านโป่ง" --date "2022-03-27" --month-table -o
```

### 2.4 Automated Benchmarks & Tests
```bash
# Run 9-case evaluation benchmark (Pass@1: 100%)
python3 harness.py --eval

# Run full unit test suite (19 tests)
python3 -m unittest discover tests
```

### 2.5 Web Server & Thai Chat UI
```bash
python3 harness.py --serve --port 8080
# Open http://localhost:8080/ in a web browser
```

---

## 3. Python API Integration

The harness can be imported directly in Python scripts:

```python
from noaaharness.agent import SolarAgentHarness

# Initialize harness (default timezone UTC+7 for Thailand)
harness = SolarAgentHarness(default_tz=7.0)

# Execute query
result = harness.query("พระอาทิตย์ขึ้นที่บ้านโป่ง วันที่ 27 มี.ค. 2565 กี่โมง")

# Access formatted Thai response text:
print(result["response_text"])

# Access structured data:
loc = result["location"]
solar = result["solar_result"]
date = result["date"]

print(f"Location: {loc['name']} ({loc['latitude']}, {loc['longitude']})")
print(f"Sunrise: {solar['sunrise_hms']}, Sunset: {solar['sunset_hms']}, Noon: {solar['solar_noon_hms']}")
print(f"Maps URL: {loc['google_maps_url']}")
```

To perform raw mathematical calculations without NLP parsing:
```python
from noaaharness.solar_engine import calculate_solar

# Ban Pong, Ratchaburi (2022-03-27, UTC+7)
res = calculate_solar(lat=13.8199, lon=99.8722, tz=7.0, year=2022, month=3, day=27)
print(f"Sunrise: {res.sunrise_hms}")  # 06:19:58
print(f"Sunset:  {res.sunset_hms}")   # 18:31:55
print(f"Noon:    {res.solar_noon_hms}") # 12:25:57
```

---

## 4. 4-Tier Smart Proximity & Fallback System

When resolving locations, the harness follows a deterministic multi-tier resolution ladder:

1. **GPS Coordinates Parsing**:
   - Parses formats: `13.8199, 99.8722`, `lat: 13.82 lon: 99.87`, `พิกัด 13.8199, 99.8722`.
   - Computes Great-Circle distance using Haversine formula against all preset cities/landmarks.
   - Automatically attaches the nearest reference landmark (e.g. `[ใกล้เคียง: อำเภอบ้านโป่ง ~0.6 กม.]`).

2. **Exact Preset Match**:
   - Matches all 77 Thai provinces and major landmarks/districts (Ban Pong, Pha Taem, Phromthep Cape, Doi Inthanon, Betong, etc.).

3. **Tier 1 Fallback — Fuzzy Typo Correction**:
   - Uses `difflib` similarity (cutoff ≥ 0.70) before external network requests to protect against latency and wrong geocoding matches.
   - Example: `เชียงใหม` ➔ `เชียงใหม่`, `พัดยา` ➔ `พัทยา`, `กานจนบุรี` ➔ `กาญจนบุรี`.

4. **Live Geocoding (OpenStreetMap Nominatim TH)**:
   - Queries OpenStreetMap Nominatim restricted to Thailand for Thai queries to prevent cross-border false matches.

5. **Tier 2 Fallback — Hierarchical Administrative Matching**:
   - If a specific temple, village, or unlisted sub-location cannot be found, it checks if any known province or district name appears in the query (e.g. *"วัดร้างที่ไม่มีในแผนที่ สุพรรณบุรี"* ➔ falls back to `จังหวัดสุพรรณบุรี`).

6. **Tier 3 Fallback — Default Center (Bangkok)**:
   - If completely unrecognizable, defaults to Bangkok with a transparent alert block prepended to the response.

---

## 5. Output Standards & Quality Requirements

Every response generated by this harness must comply with:
- **Language**: Thai with proper polite particles.
- **Time Format**: Local Time with standard suffix `น.` or `เวลาท้องถิ่น` (e.g. `06:20 น.` / `06:19:58 น.`).
- **Calendar**: Always include dual years: Buddhist Era (พ.ศ.) and Christian Era (ค.ศ.), e.g. `วันที่ 27 มีนาคม พ.ศ. 2565 (ค.ศ. 2022)`.
- **Maps Link**: Always provide clickable Google Maps link:
  `[เปิดดูพิกัดบน Google Maps](https://www.google.com/maps?q={lat:.6f},{lon:.6f})`.
- **File Saving Standard**: Whenever asked to save a report or export files (e.g. *"บันทึกรายงาน"*, *"เซฟไฟล์"*, `--output`), always save into the `reports/` directory using `UTF-8` encoding (`encoding="utf-8"`).

