"""Render assets/languages.svg: language breakdown across public, non-fork repos.

Uses the GitHub GraphQL API with the workflow's GITHUB_TOKEN.
Set LANG_FAKE=path/to/sample.json to render from a saved response instead.
"""
import json
import os
import sys
import urllib.request
from xml.sax.saxutils import escape

OUT = sys.argv[1] if len(sys.argv) > 1 else "assets/languages.svg"
LOGIN = os.environ.get("GH_LOGIN", "HakanYilmazzz")
TOP_N = 8
SKIP = {"HTML", "CSS", "Batchfile", "Inno Setup", "NSIS", "Makefile", "Dockerfile", "PowerShell"}

QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      nodes {
        name
        languages(first: 12, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


def fetch():
    if os.environ.get("LANG_FAKE"):
        return json.load(open(os.environ["LANG_FAKE"]))["data"]["user"]
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={
            "Authorization": "bearer " + os.environ["GITHUB_TOKEN"],
            "Content-Type": "application/json",
            "User-Agent": "readme-languages-card",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if "errors" in body:
        sys.exit(f"GraphQL errors: {body['errors']}")
    return body["data"]["user"]


user = fetch()
sizes, colors, repo_count = {}, {}, {}
for repo in user["repositories"]["nodes"]:
    if repo["name"].lower() == LOGIN.lower():
        continue
    for e in repo["languages"]["edges"]:
        name = e["node"]["name"]
        if name in SKIP:
            continue
        sizes[name] = sizes.get(name, 0) + e["size"]
        colors[name] = e["node"]["color"] or "#9aa4c7"
        repo_count[name] = repo_count.get(name, 0) + 1

total = sum(sizes.values()) or 1
ranked = sorted(sizes.items(), key=lambda kv: -kv[1])
top = ranked[:TOP_N]
rest = sum(v for _, v in ranked[TOP_N:])
items = [(n, v / total * 100, colors[n], repo_count[n]) for n, v in top]
if rest:
    items.append(("Other", rest / total * 100, "#4b5577", None))

W, PAD = 1000, 32
BAR_Y, BAR_H = 92, 18
GRID_Y = BAR_Y + BAR_H + 40
ROW = 44
rows_per_col = (len(items) + 1) // 2
H = GRID_Y + rows_per_col * ROW + 14

# stacked bar
segs, x = [], PAD
bar_w = W - 2 * PAD
for i, (name, pct, color, _) in enumerate(items):
    w = bar_w * pct / 100
    segs.append(
        f'<rect x="{x:.2f}" y="{BAR_Y}" width="{max(w, 0.5):.2f}" height="{BAR_H}" fill="{color}" '
        f'class="seg" style="animation-delay:{0.2 + i * 0.08:.2f}s"/>'
    )
    x += w

# legend grid (two columns)
col_w = (W - 2 * PAD) / 2
legend = []
for i, (name, pct, color, nrepo) in enumerate(items):
    col, row = divmod(i, rows_per_col)
    lx = PAD + col * col_w
    ly = GRID_Y + row * ROW
    d = 0.5 + i * 0.07
    sub = f"{nrepo} repo{'s' if nrepo != 1 else ''}" if nrepo else ""
    legend.append(f'''
  <g class="row" style="animation-delay:{d:.2f}s">
    <circle cx="{lx + 8}" cy="{ly}" r="7" fill="{color}"/>
    <text x="{lx + 26}" y="{ly + 6}" class="nm">{escape(name)}</text>
    <text x="{lx + 200}" y="{ly + 6}" class="rp">{escape(sub)}</text>
    <rect x="{lx + 280}" y="{ly - 4}" width="{col_w - 380:.1f}" height="8" rx="4" fill="#1f2547"/>
    <rect x="{lx + 280}" y="{ly - 4}" width="{max(4, (col_w - 380) * pct / max(items[0][1], 1)):.1f}" height="8" rx="4" fill="{color}" class="mini" style="animation-delay:{d:.2f}s"/>
    <text x="{lx + col_w - 20:.1f}" y="{ly + 6}" text-anchor="end" class="pc">{pct:.1f}%</text>
  </g>''')

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
  <linearGradient id="bd" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#22d3ee"/><stop offset=".5" stop-color="#a855f7"/><stop offset="1" stop-color="#f472b6"/></linearGradient>
  <clipPath id="barclip"><rect x="{PAD}" y="{BAR_Y}" width="{bar_w}" height="{BAR_H}" rx="9"/></clipPath>
</defs>
<style>
  .hd{{font:700 22px 'Segoe UI',Ubuntu,Arial,sans-serif;fill:#e6edff}}
  .hs{{font:500 13px 'Segoe UI',Ubuntu,Arial,sans-serif;fill:#8b93b8;letter-spacing:2.5px}}
  .nm{{font:600 16px 'Segoe UI',Ubuntu,Arial,sans-serif;fill:#e6edff}}
  .rp{{font:13px Consolas,'Courier New',monospace;fill:#6b7394}}
  .pc{{font:700 15px Consolas,'Courier New',monospace;fill:#c4c9d6}}
  .seg{{transform-box:fill-box;transform-origin:left;animation:grow .8s cubic-bezier(.2,.8,.2,1) both}}
  .mini{{transform-box:fill-box;transform-origin:left;animation:grow 1s cubic-bezier(.2,.8,.2,1) both}}
  @keyframes grow{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}
  .row{{opacity:0;animation:in .5s ease-out forwards}}
  @keyframes in{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:none}}}}
</style>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="20" fill="#0b1026" stroke="url(#bd)" stroke-width="2"/>
<text x="{PAD}" y="50" class="hd">What I write in</text>
<text x="{W - PAD}" y="50" text-anchor="end" class="hs">ACROSS {sum(1 for r in user["repositories"]["nodes"] if r["name"].lower() != LOGIN.lower())} PUBLIC REPOS</text>
<rect x="{PAD}" y="{BAR_Y}" width="{bar_w}" height="{BAR_H}" rx="9" fill="#1f2547"/>
<g clip-path="url(#barclip)">{"".join(segs)}</g>
{"".join(legend)}
</svg>'''

os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
open(OUT, "w", encoding="utf-8").write(svg)
print(f"wrote {OUT}: " + ", ".join(f"{n} {p:.1f}%" for n, p, _, _ in items))
