"""Render assets/stats.svg: six stat tiles + a 30-day activity chart.

Data comes from the GitHub GraphQL API using the workflow's GITHUB_TOKEN.
Set STATS_FAKE=path/to/sample.json to render from a saved response instead.
"""
import datetime as dt
import json
import os
import sys
import urllib.request
from xml.sax.saxutils import escape

OUT = sys.argv[1] if len(sys.argv) > 1 else "assets/stats.svg"
LOGIN = os.environ.get("GH_LOGIN", "HakanYilmazzz")

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      totalCount
      nodes { stargazerCount }
    }
  }
}
"""


def fetch():
    if os.environ.get("STATS_FAKE"):
        return json.load(open(os.environ["STATS_FAKE"]))["data"]["user"]
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={
            "Authorization": "bearer " + os.environ["GITHUB_TOKEN"],
            "Content-Type": "application/json",
            "User-Agent": "readme-stats-card",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if "errors" in body:
        sys.exit(f"GraphQL errors: {body['errors']}")
    return body["data"]["user"]


def fmt_date(d, with_year=False):
    s = d.strftime("%b %-d")
    return s + d.strftime(", %Y") if with_year else s


u = fetch()
cc = u["contributionsCollection"]
cal = cc["contributionCalendar"]
days = sorted(
    (dt.date.fromisoformat(d["date"]), d["contributionCount"])
    for w in cal["weeks"]
    for d in w["contributionDays"]
)
today = days[-1][0]

# current streak: today may still be empty, so allow starting from yesterday
cur, cur_start = 0, None
idx = len(days) - 1
if days[idx][1] == 0:
    idx -= 1
while idx >= 0 and days[idx][1] > 0:
    cur += 1
    cur_start = days[idx][0]
    idx -= 1

# longest streak
best, best_rng, run, run_start = 0, None, 0, None
for d, c in days:
    if c > 0:
        run += 1
        run_start = run_start or d
        if run > best:
            best, best_rng = run, (run_start, d)
    else:
        run, run_start = 0, None

# most active weekday (by average)
totals, counts = [0] * 7, [0] * 7
for d, c in days:
    totals[d.weekday()] += c
    counts[d.weekday()] += 1
avgs = [t / n if n else 0 for t, n in zip(totals, counts)]
wd = max(range(7), key=lambda i: avgs[i])
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

stars = sum(n["stargazerCount"] for n in u["repositories"]["nodes"])
repos = u["repositories"]["totalCount"]
last30 = days[-30:]
peak_day, peak = max(last30, key=lambda x: x[1])
sum30 = sum(c for _, c in last30)

tiles = [
    ("TOTAL CONTRIBUTIONS", f"{cal['totalContributions']:,}", "last 12 months", "#22d3ee"),
    ("CURRENT STREAK", f"{cur} day{'s' if cur != 1 else ''}",
     f"since {fmt_date(cur_start)}" if cur else "start one today", "#f472b6"),
    ("LONGEST STREAK", f"{best} day{'s' if best != 1 else ''}",
     f"{fmt_date(best_rng[0])} – {fmt_date(best_rng[1], True)}" if best_rng else "—", "#a855f7"),
    ("COMMITS", f"{cc['totalCommitContributions']:,}",
     f"+ {cc['totalPullRequestContributions']} pull requests", "#4ade80"),
    ("STARS EARNED", f"{stars:,}", f"across {repos} public repos", "#fbbf24"),
    ("MOST ACTIVE DAY", WEEKDAYS[wd], f"avg {avgs[wd]:.1f} contributions", "#60a5fa"),
]

W, PAD, GAP = 1000, 24, 16
TW = (W - 2 * PAD - 2 * GAP) / 3
TH = 118
CH_Y = PAD + 2 * TH + 2 * GAP
CH_H = 170
H = CH_Y + CH_H + PAD

parts = []
for i, (label, value, sub, color) in enumerate(tiles):
    x = PAD + (i % 3) * (TW + GAP)
    y = PAD + (i // 3) * (TH + GAP)
    delay = 0.1 + i * 0.12
    parts.append(f'''
  <g class="tile" style="animation-delay:{delay:.2f}s">
    <rect x="{x:.1f}" y="{y}" width="{TW:.1f}" height="{TH}" rx="14" fill="#0f1533" stroke="#1f2547"/>
    <rect x="{x:.1f}" y="{y + 18}" width="4" height="{TH - 36}" rx="2" fill="{color}"/>
    <circle cx="{x + TW - 26:.1f}" cy="{y + 26}" r="5" fill="{color}" class="pulse" style="animation-delay:{delay:.2f}s"/>
    <text x="{x + 24:.1f}" y="{y + 32}" class="lb">{escape(label)}</text>
    <text x="{x + 24:.1f}" y="{y + 74}" class="vl" fill="{color}">{escape(value)}</text>
    <text x="{x + 24:.1f}" y="{y + 99}" class="sb">{escape(sub)}</text>
  </g>''')

# 30-day bar chart
cx0, cx1 = PAD + 24, W - PAD - 24
bar_area_top, bar_area_bot = CH_Y + 58, CH_Y + CH_H - 34
bw = (cx1 - cx0) / len(last30)
mx = max(1, peak)
bars = []
for i, (d, c) in enumerate(last30):
    h = max(3, (bar_area_bot - bar_area_top) * c / mx)
    x = cx0 + i * bw + 2
    color = "url(#barg)" if c else "#1f2547"
    bars.append(
        f'<rect x="{x:.1f}" y="{bar_area_bot - h:.1f}" width="{bw - 4:.1f}" height="{h:.1f}" rx="3" '
        f'fill="{color}" class="bar" style="animation-delay:{0.9 + i * 0.025:.3f}s"><title>{d.isoformat()}: {c}</title></rect>'
    )
parts.append(f'''
  <g class="tile" style="animation-delay:0.8s">
    <rect x="{PAD}" y="{CH_Y}" width="{W - 2 * PAD}" height="{CH_H}" rx="14" fill="#0f1533" stroke="#1f2547"/>
    <text x="{PAD + 24}" y="{CH_Y + 32}" class="lb">LAST 30 DAYS</text>
    <text x="{W - PAD - 24}" y="{CH_Y + 32}" text-anchor="end" class="sb">{sum30:,} contributions · peak {peak} on {fmt_date(peak_day)}</text>
    {"".join(bars)}
    <text x="{cx0}" y="{CH_Y + CH_H - 12}" class="ax">{fmt_date(last30[0][0])}</text>
    <text x="{cx1}" y="{CH_Y + CH_H - 12}" text-anchor="end" class="ax">{fmt_date(today)}</text>
  </g>''')

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
  <linearGradient id="barg" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#7c3aed"/><stop offset=".6" stop-color="#a855f7"/><stop offset="1" stop-color="#22d3ee"/></linearGradient>
  <linearGradient id="bd" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#22d3ee"/><stop offset=".5" stop-color="#a855f7"/><stop offset="1" stop-color="#f472b6"/></linearGradient>
</defs>
<style>
  .lb{{font:700 12px 'Segoe UI',Ubuntu,Arial,sans-serif;fill:#8b93b8;letter-spacing:2.5px}}
  .vl{{font:800 34px 'Segoe UI',Ubuntu,Arial,sans-serif}}
  .sb{{font:500 13px 'Segoe UI',Ubuntu,Arial,sans-serif;fill:#9aa4c7}}
  .ax{{font:500 11px Consolas,'Courier New',monospace;fill:#6b7394}}
  .tile{{opacity:0;animation:in .6s ease-out forwards}}
  @keyframes in{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:none}}}}
  .bar{{transform-box:fill-box;transform-origin:bottom;animation:grow .7s cubic-bezier(.2,.8,.2,1) both}}
  @keyframes grow{{from{{transform:scaleY(0)}}to{{transform:scaleY(1)}}}}
  .pulse{{animation:pl 2.4s ease-in-out infinite}}
  @keyframes pl{{0%,100%{{opacity:.35}}50%{{opacity:1}}}}
</style>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="20" fill="#0b1026" stroke="url(#bd)" stroke-width="2"/>
{"".join(parts)}
</svg>'''

os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
open(OUT, "w", encoding="utf-8").write(svg)
print(f"wrote {OUT}: contributions={cal['totalContributions']} streak={cur} longest={best} stars={stars}")
