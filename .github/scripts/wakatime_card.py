"""Fetch last-7-days WakaTime stats and render assets/wakatime.svg."""
import json, os, sys, urllib.error, urllib.request
from xml.sax.saxutils import escape

OUT = sys.argv[1] if len(sys.argv) > 1 else "assets/wakatime.svg"
COLORS = ["#22d3ee", "#a855f7", "#f472b6", "#60a5fa", "#4ade80", "#fbbf24"]

def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 readme-stats-card", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        print(f"WakaTime error {e.code}: {e.read().decode(errors='replace')[:300]}", file=sys.stderr)
        raise

def human(sec):
    h, m = int(sec // 3600), int(sec % 3600 // 60)
    if h and m: return f"{h} hr{'s' if h != 1 else ''} {m} min{'s' if m != 1 else ''}"
    if h: return f"{h} hr{'s' if h != 1 else ''}"
    return f"{m} min{'s' if m != 1 else ''}"

def fetch():
    """Uses WakaTime public share (embed) JSON links: no API key needed."""
    if os.environ.get("WAKA_FAKE"):
        return json.load(open(os.environ["WAKA_FAKE"]))["data"]
    act_url = os.environ.get("WAKA_ACTIVITY_URL", "").strip()
    lang_url = os.environ.get("WAKA_LANGS_URL", "").strip()
    if not act_url or not lang_url:
        print("WAKA_ACTIVITY_URL / WAKA_LANGS_URL secrets are missing; rendering placeholder.", file=sys.stderr)
        return {"languages": []}
    days = get_json(act_url).get("data", [])
    total = sum(float(d.get("grand_total", {}).get("total_seconds", 0)) for d in days)
    langs = get_json(lang_url).get("data", [])
    out = []
    for l in sorted(langs, key=lambda x: -float(x.get("percent", 0))):
        pct = float(l.get("percent", 0))
        secs = total * pct / 100
        out.append({"name": l.get("name", "?"), "percent": pct, "total_seconds": secs, "text": human(secs)})
    return {"languages": out, "human_readable_total": human(total)}

data = fetch()
langs = [l for l in (data.get("languages") or []) if l.get("total_seconds", 0) >= 60][:6]
total = data.get("human_readable_total") or "0 mins"

W, ROW, TOP = 900, 46, 112
H = TOP + (max(1, len(langs)) - 1) * ROW + 52
rows = ""
if not langs:
    rows = (f'<text x="{W/2}" y="{TOP+20}" text-anchor="middle" class="lb" '
            f'style="fill:#9aa4c7">Collecting data… check back in a few days</text>')
for i, l in enumerate(langs):
    y = TOP + i * ROW
    pct = float(l.get("percent", 0))
    bw = max(6, 430 * pct / 100)
    c = COLORS[i % len(COLORS)]
    d = 0.3 + i * 0.15
    rows += f'''
  <g class="row" style="animation-delay:{d:.2f}s">
    <circle cx="44" cy="{y}" r="6" fill="{c}"/>
    <text x="60" y="{y+6}" class="lb">{escape(l["name"])}</text>
    <rect x="220" y="{y-7}" width="430" height="14" rx="7" fill="#1f2547"/>
    <rect x="220" y="{y-7}" width="{bw:.1f}" height="14" rx="7" fill="{c}" class="bar" style="animation-delay:{d:.2f}s"/>
    <text x="{W-36}" y="{y+6}" text-anchor="end" class="vl">{escape(l.get("text",""))} · {pct:.0f}%</text>
  </g>'''

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs><linearGradient id="bd" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#22d3ee"/><stop offset=".5" stop-color="#a855f7"/><stop offset="1" stop-color="#f472b6"/></linearGradient></defs>
<style>
  .tt{{font:700 22px 'Segoe UI',Ubuntu,Arial,sans-serif;fill:#e6edff}}
  .sb{{font:500 14px 'Segoe UI',Ubuntu,Arial,sans-serif;fill:#9aa4c7;letter-spacing:2px}}
  .tot{{font:800 22px Consolas,'Courier New',monospace;fill:#22d3ee}}
  .lb{{font:600 16px Consolas,'Courier New',monospace;fill:#e6edff}}
  .vl{{font:15px Consolas,'Courier New',monospace;fill:#9aa4c7}}
  .row{{opacity:0;animation:in .5s ease-out forwards}}
  @keyframes in{{from{{opacity:0;transform:translateX(-10px)}}to{{opacity:1;transform:none}}}}
  .bar{{transform-box:fill-box;transform-origin:left;animation:grow 1.1s cubic-bezier(.2,.8,.2,1) both}}
  @keyframes grow{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}
</style>
<rect x="1.5" y="1.5" width="{W-3}" height="{H-3}" rx="18" fill="#0b1026" stroke="url(#bd)" stroke-width="2"/>
<text x="36" y="50" class="tt">⏱️ This week in code</text>
<text x="36" y="76" class="sb">LAST 7 DAYS · TRACKED WITH WAKATIME</text>
<text x="{W-36}" y="58" text-anchor="end" class="tot">{escape(total)}</text>
{rows}
</svg>'''
os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
open(OUT, "w", encoding="utf-8").write(svg)
print("wrote", OUT, "with", len(langs), "languages, total", total)
