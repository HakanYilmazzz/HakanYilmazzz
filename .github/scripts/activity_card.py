"""Render assets/activity.svg: a timeline of recent public GitHub activity.

Uses the REST events API with the workflow's GITHUB_TOKEN.
Set ACT_FAKE=path/to/events.json to render from saved events instead.
"""
import datetime as dt
import json
import os
import sys
import urllib.request
from xml.sax.saxutils import escape

OUT = sys.argv[1] if len(sys.argv) > 1 else "assets/activity.svg"
LOGIN = os.environ.get("GH_LOGIN", "HakanYilmazzz")
MAX_ROWS = 6


def fetch():
    if os.environ.get("ACT_FAKE"):
        return json.load(open(os.environ["ACT_FAKE"]))
    req = urllib.request.Request(
        f"https://api.github.com/users/{LOGIN}/events/public?per_page=100",
        headers={
            "Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
            "Accept": "application/vnd.github+json",
            "User-Agent": "readme-activity-card",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def short_repo(name):
    owner, _, repo = name.partition("/")
    return repo if owner.lower() == LOGIN.lower() else name


def clip(s, n):
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"


# type -> (glyph, color)
STYLE = {
    "push": ("↑", "#22d3ee"),
    "release": ("◆", "#f472b6"),
    "create": ("+", "#4ade80"),
    "star": ("★", "#fbbf24"),
    "fork": ("⑂", "#60a5fa"),
    "pr": ("⇄", "#a855f7"),
    "issue": ("!", "#fb923c"),
    "public": ("◉", "#4ade80"),
    "comment": ("”", "#9aa4c7"),
}


def describe(e):
    """Return (kind, title, subtitle) or None to skip."""
    t, p, repo = e["type"], e.get("payload", {}), short_repo(e["repo"]["name"])
    if t == "PushEvent":
        commits = p.get("commits") or []
        msg = commits[-1]["message"].splitlines()[0] if commits else ""
        branch = (p.get("ref") or "").replace("refs/heads/", "")
        count = len(commits) or p.get("size") or None
        return "push", repo, msg or (f"on {branch}" if branch else ""), count
    if t == "ReleaseEvent" and p.get("action") == "published":
        rel = p.get("release", {})
        return "release", repo, f"Published {rel.get('name') or rel.get('tag_name', '')}", 1
    if t == "CreateEvent":
        if p.get("ref_type") == "repository":
            return "create", repo, clip(p.get("description") or "Created a new repository", 70), 1
        if p.get("ref_type") == "tag":
            return "create", repo, f"Tagged {p.get('ref')}", 1
        return None
    if t == "WatchEvent":
        return "star", e["repo"]["name"], "Starred a repository", 1
    if t == "ForkEvent":
        return "fork", e["repo"]["name"], "Forked a repository", 1
    if t == "PullRequestEvent" and p.get("action") in ("opened", "closed", "reopened"):
        pr = p.get("pull_request", {})
        verb = "Merged" if pr.get("merged") else p["action"].capitalize()
        return "pr", repo, f"{verb} PR #{pr.get('number', '')}: {pr.get('title', '')}", 1
    if t == "IssuesEvent" and p.get("action") in ("opened", "closed"):
        iss = p.get("issue", {})
        return "issue", repo, f"{p['action'].capitalize()} issue #{iss.get('number', '')}: {iss.get('title', '')}", 1
    if t == "PublicEvent":
        return "public", repo, "Made the repository public", 1
    if t == "IssueCommentEvent":
        iss = p.get("issue", {})
        return "comment", repo, f"Commented on #{iss.get('number', '')}: {iss.get('title', '')}", 1
    return None


def ago(ts, now):
    s = int((now - ts).total_seconds())
    if s < 3600:
        return f"{max(1, s // 60)}m ago"
    if s < 86400:
        return f"{s // 3600}h ago"
    d = s // 86400
    return "yesterday" if d == 1 else f"{d}d ago"


events = fetch()
now = dt.datetime.now(dt.timezone.utc)
rows = []
for e in events:
    if e["repo"]["name"].lower() == f"{LOGIN}/{LOGIN}".lower():
        continue  # skip the profile repo's own README updates
    info = describe(e)
    if not info:
        continue
    kind, repo, sub, n = info
    ts = dt.datetime.fromisoformat(e["created_at"].replace("Z", "+00:00"))
    last = rows[-1] if rows else None
    # merge consecutive pushes to the same repo
    if last and kind == "push" and last["kind"] == "push" and last["repo"] == repo:
        last["n"] = (last["n"] or 0) + n if (last["n"] and n) else None
        continue
    # merge consecutive identical release/tag rows for the same repo
    if last and kind == last["kind"] == "release" and last["repo"] == repo:
        last["extra"] += 1
        continue
    rows.append({"kind": kind, "repo": repo, "sub": sub, "n": n, "ts": ts, "extra": 0})
    if len(rows) > MAX_ROWS:
        rows.pop()
        break

TITLES = {
    "push": lambda r: f"Pushed {r['n']} commit{'s' if r['n'] != 1 else ''} to" if r["n"] else "Pushed to",
    "release": lambda r: "Released",
    "create": lambda r: "Created",
    "star": lambda r: "Starred",
    "fork": lambda r: "Forked",
    "pr": lambda r: "Pull request in",
    "issue": lambda r: "Issue in",
    "public": lambda r: "Open-sourced",
    "comment": lambda r: "Discussion in",
}

W, PAD, ROW, TOP = 1000, 28, 66, 84
H = TOP + max(1, len(rows)) * ROW + 18
parts = []
if not rows:
    parts.append(f'<text x="{W/2}" y="{TOP+30}" text-anchor="middle" class="sb">No public activity yet.</text>')
else:
    y0, y1 = TOP + 18, TOP + (len(rows) - 1) * ROW + 18
    parts.append(f'<path d="M{PAD+22} {y0}V{y1}" stroke="url(#ln)" stroke-width="2" class="line"/>')
for i, r in enumerate(rows):
    glyph, color = STYLE[r["kind"]]
    y = TOP + i * ROW
    d = 0.15 + i * 0.12
    sub = r["sub"]
    if r["extra"]:
        sub += f"  (+{r['extra']} more)"
    parts.append(f'''
  <g class="row" style="animation-delay:{d:.2f}s">
    <circle cx="{PAD+22}" cy="{y+18}" r="16" fill="#0b1026" stroke="{color}" stroke-width="2"/>
    <text x="{PAD+22}" y="{y+24}" text-anchor="middle" class="gl" fill="{color}">{escape(glyph)}</text>
    <text x="{PAD+54}" y="{y+16}" class="tt">{escape(TITLES[r['kind']](r))} <tspan class="rp" fill="{color}">{escape(r['repo'])}</tspan></text>
    <text x="{PAD+54}" y="{y+38}" class="sb">{escape(clip(sub, 92))}</text>
    <text x="{W-PAD}" y="{y+16}" text-anchor="end" class="tm">{escape(ago(r['ts'], now))}</text>
  </g>''')

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
  <linearGradient id="bd" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#22d3ee"/><stop offset=".5" stop-color="#a855f7"/><stop offset="1" stop-color="#f472b6"/></linearGradient>
  <linearGradient id="ln" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#22d3ee"/><stop offset="1" stop-color="#a855f7" stop-opacity=".2"/></linearGradient>
</defs>
<style>
  .hd{{font:700 22px 'Segoe UI',Ubuntu,Arial,sans-serif;fill:#e6edff}}
  .hs{{font:500 13px 'Segoe UI',Ubuntu,Arial,sans-serif;fill:#8b93b8;letter-spacing:2.5px}}
  .tt{{font:600 16px 'Segoe UI',Ubuntu,Arial,sans-serif;fill:#e6edff}}
  .rp{{font-weight:800}}
  .sb{{font:14px Consolas,'Courier New',monospace;fill:#9aa4c7}}
  .tm{{font:600 13px Consolas,'Courier New',monospace;fill:#6b7394}}
  .gl{{font:800 17px 'Segoe UI Symbol','Segoe UI',Ubuntu,'DejaVu Sans',Arial,sans-serif}}
  .row{{opacity:0;animation:in .5s ease-out forwards}}
  @keyframes in{{from{{opacity:0;transform:translateX(-12px)}}to{{opacity:1;transform:none}}}}
  .line{{stroke-dasharray:1000;stroke-dashoffset:1000;animation:draw 1.4s .1s ease-out forwards}}
  @keyframes draw{{to{{stroke-dashoffset:0}}}}
</style>
<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="20" fill="#0b1026" stroke="url(#bd)" stroke-width="2"/>
<text x="{PAD}" y="44" class="hd">Latest from the workshop</text>
<text x="{W-PAD}" y="44" text-anchor="end" class="hs">UPDATED {now.strftime('%b %-d, %H:%M').upper()} UTC</text>
{"".join(parts)}
</svg>'''

os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
open(OUT, "w", encoding="utf-8").write(svg)
print(f"wrote {OUT} with {len(rows)} rows")
