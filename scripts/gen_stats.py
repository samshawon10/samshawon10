"""Generate assets/stats.svg (terminal-style GitHub stats) for the profile README.
Run by .github/workflows/stats.yml; uses the built-in GITHUB_TOKEN. No third-party services."""
import json, os, sys, datetime, urllib.request
from xml.sax.saxutils import escape

USER = os.environ.get("GH_USER", "samshawon10")
TOKEN = os.environ.get("GITHUB_TOKEN")
OUT = os.environ.get("STATS_OUT", "assets/stats.svg")
LANG_COLORS = {"JavaScript": "#f1e05a", "TypeScript": "#3178c6", "HTML": "#e34f26", "CSS": "#9b6bd1",
               "Python": "#3572a5", "Java": "#b07219", "C++": "#f34b7d", "C": "#8a8a8a", "SCSS": "#c6538c",
               "Shell": "#89e051", "Jupyter Notebook": "#da5b0b", "Dart": "#00b4ab", "PHP": "#4f5d95"}
FONT = '"SF Mono","JetBrains Mono",Consolas,"Liberation Mono","Courier New",monospace'


def call(url, data=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "profile-stats", "Accept": "application/vnd.github+json"})
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def collect():
    user = call(f"https://api.github.com/users/{USER}")
    repos, page = [], 1
    while True:
        chunk = call(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner&page={page}")
        repos += chunk
        if len(chunk) < 100:
            break
        page += 1
    own = [r for r in repos if not r["fork"]]
    langs = {}
    for r in own:
        try:
            for k, v in call(r["languages_url"]).items():
                langs[k] = langs.get(k, 0) + v
        except Exception:
            pass
    contrib = None
    if TOKEN:
        try:
            q = 'query{user(login:"%s"){contributionsCollection{contributionCalendar{totalContributions}}}}' % USER
            res = call("https://api.github.com/graphql", json.dumps({"query": q}).encode())
            contrib = res["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
        except Exception:
            pass
    return {"repos": user["public_repos"], "followers": user["followers"],
            "stars": sum(r["stargazers_count"] for r in own), "forks": sum(r["forks_count"] for r in own),
            "contrib": contrib, "langs": langs}


def render(d):
    rows = [("public repos", d["repos"]), ("stars earned", d["stars"]), ("forks", d["forks"]), ("followers", d["followers"])]
    if d["contrib"] is not None:
        rows.append(("contributions, last year", d["contrib"]))
    total = sum(d["langs"].values()) or 1
    top = sorted(d["langs"].items(), key=lambda kv: -kv[1])[:5]
    left = ""
    for i, (k, v) in enumerate(rows):
        y = 92 + i * 26
        left += (f'<text class="fi" style="animation-delay:{.4 + i * .25:.2f}s" x="24" y="{y}">'
                 f'<tspan fill="#ffb454">{escape(k)}</tspan></text>'
                 f'<text class="fi" style="animation-delay:{.4 + i * .25:.2f}s" x="396" y="{y}" text-anchor="end" fill="#3ddc84" font-weight="700">{v:,}</text>')
    right = ""
    for i, (k, v) in enumerate(top):
        y = 92 + i * 26
        pct = v / total * 100
        w = max(3, round(pct / 100 * 150))
        color = LANG_COLORS.get(k, "#3ddc84")
        right += (f'<circle cx="{474}" cy="{y - 5}" r="4" fill="{color}"/>'
                  f'<text x="488" y="{y}" fill="#d7ffe5">{escape(k)}</text>'
                  f'<rect x="620" y="{y - 11}" width="150" height="8" rx="4" fill="#111a15"/>'
                  f'<rect class="bar" style="animation-delay:{.6 + i * .2:.2f}s" x="620" y="{y - 11}" width="{w}" height="8" rx="4" fill="#3ddc84"/>'
                  f'<text x="876" y="{y}" text-anchor="end" fill="#8b949e">{pct:.1f}%</text>')
    if not top:
        right = '<text x="456" y="92" fill="#5c6b66">no language data yet</text>'
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    h = 92 + max(len(rows), len(top)) * 26 + 34
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 {h}" width="900" height="{h}" role="img" aria-label="GitHub stats for {USER}">
<style>text{{font-family:{FONT};font-size:14px;white-space:pre}}.fi{{opacity:0;animation:fi .01s forwards}}@keyframes fi{{to{{opacity:1}}}}.bar{{transform-box:fill-box;transform-origin:left center;transform:scaleX(0);animation:gr 1.1s ease-out forwards}}@keyframes gr{{to{{transform:scaleX(1)}}}}@media (prefers-reduced-motion:reduce){{.fi{{opacity:1;animation:none}}.bar{{transform:none;animation:none}}}}</style>
<rect x=".5" y=".5" width="899" height="{h - 1}" rx="12" fill="#070b09" stroke="#1f2a24"/>
<rect x="430" y="20" width="1" height="{h - 60}" fill="#1f2a24"/>
<text x="24" y="44"><tspan fill="#3ddc84">$</tspan><tspan fill="#d7ffe5"> gh stats --user {USER}</tspan></text>
<text x="456" y="44"><tspan fill="#3ddc84">$</tspan><tspan fill="#d7ffe5"> top-languages</tspan></text>
{left}{right}
<text x="24" y="{h - 14}" font-size="11" fill="#5c6b66"># updated {stamp} UTC, regenerated automatically</text>
</svg>'''


if __name__ == "__main__":
    if os.environ.get("STATS_DEMO"):
        data = {"repos": 24, "stars": 12, "forks": 3, "followers": 42, "contrib": 769,
                "langs": {"JavaScript": 52000, "TypeScript": 31000, "HTML": 18000, "CSS": 9000, "Python": 7000}}
    else:
        try:
            data = collect()
        except Exception as e:
            print("stats failed:", e, file=sys.stderr)
            sys.exit(1)
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(render(data))
    print("wrote", OUT)
