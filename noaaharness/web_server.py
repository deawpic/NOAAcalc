"""
Lightweight Web Server & REST API for NOAA Solar Harness
Provides zero-dependency HTTP server with:
- /api/query (POST): Thai Natural Language Solar Q&A
- /api/calculate (GET): Parameterized NOAA Calculation
- / (GET): Interactive Solar Calculator & Thai Chat Harness UI
"""

import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional

from noaaharness.agent import SolarAgentHarness
from noaaharness.solar_engine import calculate_solar, minutes_to_hm, minutes_to_hms, minutes_to_duration_th
from noaaharness.geocoder import resolve_location
from noaaharness.date_parser import format_date_thai

HTML_CHAT_UI = """<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NOAA Solar Harness — ถามตอบคำนวณเวลาดวงอาทิตย์ (ภาษาไทย)</title>
<style>
:root {
  --bg: #0b0f19;
  --panel: #131b2e;
  --card: #1c2744;
  --accent: #38bdf8;
  --text: #f1f5f9;
  --muted: #94a3b8;
  --border: #293556;
  --user: #0284c7;
  --bot: #1e293b;
  --green: #34d399;
  --orange: #fb923c;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  padding: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Sarabun", "Segoe UI", Roboto, sans-serif;
  background: var(--bg);
  color: var(--text);
  display: flex;
  flex-direction: column;
  height: 100vh;
}
header {
  background: linear-gradient(135deg, #0284c7, #6366f1);
  padding: 16px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}
header h1 {
  margin: 0;
  font-size: 1.25rem;
  display: flex;
  align-items: center;
  gap: 10px;
}
header .subtitle {
  font-size: 0.85rem;
  opacity: 0.9;
  margin-top: 4px;
}
.badges {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.badge {
  background: rgba(0,0,0,0.3);
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 0.75rem;
  border: 1px solid rgba(255,255,255,0.2);
}
main {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 960px;
  width: 100%;
  margin: 0 auto;
}
.msg {
  display: flex;
  flex-direction: column;
  max-width: 85%;
  animation: fadeIn 0.2s ease-in-out;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}
.msg.user {
  align-self: flex-end;
}
.msg.bot {
  align-self: flex-start;
}
.bubble {
  padding: 14px 18px;
  border-radius: 14px;
  line-height: 1.6;
  font-size: 0.95rem;
  white-space: pre-wrap;
  word-break: break-word;
}
.user .bubble {
  background: var(--user);
  color: #fff;
  border-bottom-right-radius: 2px;
}
.bot .bubble {
  background: var(--bot);
  border: 1px solid var(--border);
  border-bottom-left-radius: 2px;
}
.bot .bubble a {
  color: var(--accent);
  text-decoration: underline;
  font-weight: bold;
}
.suggestions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  padding: 10px 20px;
  max-width: 960px;
  margin: 0 auto;
  width: 100%;
}
.chip {
  background: var(--panel);
  border: 1px solid var(--border);
  color: var(--accent);
  font-size: 0.82rem;
  padding: 6px 12px;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.2s;
}
.chip:hover {
  background: var(--accent);
  color: #000;
}
footer {
  padding: 14px 20px 20px;
  background: var(--panel);
  border-top: 1px solid var(--border);
}
.input-wrap {
  display: flex;
  gap: 10px;
  max-width: 960px;
  margin: 0 auto;
}
input[type="text"] {
  flex: 1;
  padding: 12px 16px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--bg);
  color: #fff;
  font-size: 1rem;
  outline: none;
}
input[type="text"]:focus {
  border-color: var(--accent);
}
button.send-btn {
  background: var(--accent);
  color: #04101e;
  font-weight: bold;
  border: none;
  padding: 12px 24px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 1rem;
  transition: filter 0.2s;
}
button.send-btn:hover {
  filter: brightness(1.15);
}
</style>
</head>
<body>

<header>
  <div>
    <h1>☀️ NOAA Solar Harness</h1>
    <div class="subtitle">ระบบถาม-ตอบคำนวณเวลาพระอาทิตย์ขึ้น-ตก-เที่ยงวันจริง (Local Time / พ.ศ. / ค.ศ. / Google Maps)</div>
  </div>
  <div class="badges">
    <span class="badge">ความแม่นยำ ±1 นาที</span>
    <span class="badge">Jean Meeus NOAA</span>
    <span class="badge">รองรับพิกัด & ชื่อสถานที่</span>
  </div>
</header>

<main id="chatBox">
  <div class="msg bot">
    <div class="bubble">สวัสดีครับ! ยินดีต้อนรับสู่ **NOAA Solar Calculator Harness** ☀️
คุณสามารถพิมพ์ถามเป็นภาษาไทยได้ทั้งชื่อสถานที่หรือพิกัด เช่น:
• "พระอาทิตย์ขึ้นที่อำเภอบ้านโป่ง วันที่ 27 มีนาคม 2565 กี่โมง"
• "พรุ่งนี้พระอาทิตย์ตกที่เชียงใหม่เวลาเท่าไหร่"
• "คำนวณเวลาพระอาทิตย์ที่พิกัด 13.8199, 99.8722"
• "เที่ยงวันจริงที่กรุงเทพฯ วันนี้"

พร้อมลิงก์ Google Maps และเวลา Local Time พ.ศ. / ค.ศ. ทันทีครับ!</div>
  </div>
</main>

<div class="suggestions">
  <span class="chip" onclick="quickSend('พระอาทิตย์ขึ้นที่บ้านโป่ง วันที่ 27 มี.ค. 2565')">📍 บ้านโป่ง 27 มี.ค. 2565</span>
  <span class="chip" onclick="quickSend('พรุ่งนี้พระอาทิตย์ตกที่เชียงใหม่กี่โมง')">🌄 พรุ่งนี้ที่เชียงใหม่</span>
  <span class="chip" onclick="quickSend('พิกัด 13.8199, 99.8722 พระอาทิตย์ขึ้นกี่โมง')">🌐 พิกัด 13.8199, 99.8722</span>
  <span class="chip" onclick="quickSend('จุดชมพระอาทิตย์ขึ้นผาแต้ม อุบลราชธานี วันนี้')">🌅 ผาแต้ม อุบลราชธานี</span>
  <span class="chip" onclick="quickSend('เที่ยงวันจริงที่กรุงเทพฯ วันนี้กี่โมง')">☀️ เที่ยงวันจริงที่กรุงเทพฯ</span>
</div>

<footer>
  <form class="input-wrap" onsubmit="event.preventDefault(); sendMsg();">
    <input id="userInput" type="text" placeholder="พิมพ์คำถาม เช่น 'พระอาทิตย์ตกที่ภูเก็ตวันนี้' หรือพิกัด..." autocomplete="off">
    <button type="submit" class="send-btn">ส่งคำถาม</button>
  </form>
</footer>

<script>
const chatBox = document.getElementById('chatBox');
const userInput = document.getElementById('userInput');

function formatMarkdownLinks(text) {
  // Convert [text](url) to HTML <a href="..." target="_blank">text</a>
  return text.replace(/\\[([^\\]]+)\\]\\((https?:\\/\\/[^\\)]+)\\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1 ↗</a>');
}

function appendMsg(sender, text) {
  const d = document.createElement('div');
  d.className = 'msg ' + sender;
  const b = document.createElement('div');
  b.className = 'bubble';
  if (sender === 'bot') {
    b.innerHTML = formatMarkdownLinks(text);
  } else {
    b.textContent = text;
  }
  d.appendChild(b);
  chatBox.appendChild(d);
  chatBox.scrollTop = chatBox.scrollHeight;
}

async function sendMsg() {
  const q = userInput.value.trim();
  if (!q) return;
  appendMsg('user', q);
  userInput.value = '';

  try {
    const res = await fetch('/api/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: q })
    });
    const data = await res.json();
    if (data.response_text) {
      appendMsg('bot', data.response_text);
    } else {
      appendMsg('bot', 'เกิดข้อผิดพลาดในการประมวลผลคำตอบ');
    }
  } catch (err) {
    appendMsg('bot', 'เกิดข้อผิดพลาดในการเชื่อมต่อกับเซิร์ฟเวอร์');
  }
}

function quickSend(text) {
  userInput.value = text;
  sendMsg();
}
</script>

</body>
</html>
"""


class NOAAHandler(BaseHTTPRequestHandler):

    agent = SolarAgentHarness()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/chat":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_CHAT_UI.encode("utf-8"))
            return

        elif path == "/api/calculate":
            qs = urllib.parse.parse_qs(parsed.query)
            try:
                lat = float(qs.get("lat", [13.8199])[0])
                lon = float(qs.get("lon", [99.8722])[0])
                tz = float(qs.get("tz", [7.0])[0])
                year = int(qs.get("year", [2022])[0])
                month = int(qs.get("month", [3])[0])
                day = int(qs.get("day", [27])[0])

                res = calculate_solar(lat, lon, tz, year, month, day)
                out = res.to_dict()

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(out, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/query":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body) if body else {}
                query_text = data.get("query", "")
                short_answer = data.get("short_answer", False)
                result = self.agent.query(query_text, short_answer=short_answer)

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()


def start_server(port: int = 8080, host: str = "0.0.0.0"):
    server_address = (host, port)
    httpd = HTTPServer(server_address, NOAAHandler)
    print(f"☀️ NOAA Solar Harness Server running at http://{host}:{port}/ (Ctrl+C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down server...")
        httpd.server_close()


if __name__ == "__main__":
    start_server()
