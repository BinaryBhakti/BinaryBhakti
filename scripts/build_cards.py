"""Renders every animated SVG card in assets/ from live GitHub data.

Run:      python3 scripts/build_cards.py            (needs `gh` logged in, or GH_TOKEN set)
Preview:  STATIC=1 python3 scripts/build_cards.py   (final frame only, for screenshots)

GitHub shows these through <img>, which sandboxes the SVG: no scripts, no network.
So fonts are embedded as base64 woff2 and all motion is CSS inside each SVG. Every element's
base style is its final state and keyframes animate *from* hidden, so reduced-motion and
STATIC both simply drop the animations.

Layout: the README column is 880px. Full cards are 880 wide, thirds are 293.333 wide, and the
12px gaps are baked into the SVGs (below each card, and by shifting each third's card), so the
README stacks them with no spacing of its own. Delays run on one page-wide timeline, so the
page plays top to bottom.
"""
import base64, json, os, subprocess, textwrap
from collections import defaultdict
from datetime import datetime
from html import escape
from pathlib import Path

LOGIN = "BinaryBhakti"
ROOT = Path(__file__).resolve().parent.parent
OUT, FONTS = ROOT / "assets", ROOT / "fonts"
STATIC = os.environ.get("STATIC") == "1"

# Kora Kaagaz palette (KoraKaagaz/app/globals.css)
PAPER, PAPER2, INK, MUTED, RULE, NAVY = "#faf8f3", "#f1ede4", "#171717", "#66655f", "#d6d5d1", "#071a43"
# Blues from the Kora Kaagaz swatches: cobalt is the signature (the site's CTA colour).
ACCENT, PERI, HAZE = "#064bff", "#90a7f9", "#dde4fd"  # cobalt, periwinkle, haze
RAMP = {"NONE": HAZE, "FIRST_QUARTILE": "#b9c7fb", "SECOND_QUARTILE": PERI, "THIRD_QUARTILE": ACCENT, "FOURTH_QUARTILE": NAVY}
W, GAP = 880, 12
THIRD, TW = W / 3, (W - 2 * GAP) / 3

FACES = {  # key: (file, family, css descriptors)
    "serif": ("serif-400.woff2", "KS", "font-style:normal"),
    "italic": ("serif-italic.woff2", "KS", "font-style:italic"),
    "sans": ("sans-450.woff2", "KG", "font-weight:400"),
    "bold": ("sans-650.woff2", "KG", "font-weight:600"),
    "mono": ("mono-400.woff2", "KM", "font-weight:400"),
}

KEYFRAMES = """
@keyframes rise{from{opacity:0;transform:translateY(18px)}}
@keyframes fade{from{opacity:0}}
@keyframes draw{from{transform:scaleX(0)}}
@keyframes grow{from{transform:scaleY(0)}}
@keyframes pop{0%{opacity:0;transform:scale(.3)}70%{transform:scale(1.15)}100%{transform:none}}
@keyframes tilein{0%{opacity:0;transform:translateY(80px) scale(.65) rotate(-8deg)}55%{opacity:1;transform:translateY(-9px) scale(1.04) rotate(1.8deg)}78%{transform:translateY(3px) scale(.99) rotate(-.6deg)}100%{transform:none}}
@keyframes slide{from{opacity:0;transform:translateX(-22px)}}
@keyframes shine{0%{transform:translateX(0)}45%,100%{transform:translateX(820px)}}
@keyframes sweep{0%{transform:translateX(0) skewX(-20deg)}24%,100%{transform:translateX(1300px) skewX(-20deg)}}
@keyframes ring{0%{opacity:.6;transform:scale(.2)}100%{opacity:0;transform:scale(2.2)}}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.25}}
@keyframes nudge{0%,100%{transform:none}50%{transform:translateX(4px)}}
@keyframes nudgeup{0%,100%{transform:none}50%{transform:translate(3px,-3px)}}
@keyframes on{0%,100%{opacity:1}}
@keyframes show{from{opacity:0}to{opacity:1}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
"""
BASE_CSS = """.s{font-family:KS,Georgia,serif}.i{font-family:KS,Georgia,serif;font-style:italic}
.g{font-family:KG,-apple-system,'Segoe UI',Helvetica,Arial,sans-serif}.b{font-weight:600}
.m{font-family:KM,ui-monospace,SFMono-Regular,Menlo,monospace}
.fb{transform-box:fill-box;transform-origin:center}.fl{transform-box:fill-box;transform-origin:left center}
.fd{transform-box:fill-box;transform-origin:center bottom}.tile{transform-box:fill-box;transform-origin:50% 60%}"""
EASE = "cubic-bezier(.2,.75,.2,1)"


def anim(name, dur, delay=0.0, tail=f"{EASE} both"):
    """Inline animation style, or nothing in STATIC mode."""
    return "" if STATIC else f' style="animation:{name} {dur}s {tail};animation-delay:{delay:.2f}s"'


def loop(name, dur, delay, base=""):
    """Infinite effect. `base` is its resting style (e.g. hidden) when animations are off."""
    return f' style="{base}{"" if STATIC else f";animation:{name} {dur}s ease-in-out {delay:.2f}s infinite"}"'


def svg(w, h, body, label, faces):
    fonts = "".join(
        f"@font-face{{font-family:{fam};{desc};src:url(data:font/woff2;base64,"
        f"{base64.b64encode((FONTS / f).read_bytes()).decode()}) format('woff2')}}"
        for f, fam, desc in (FACES[k] for k in faces))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w:g}" height="{h}" viewBox="0 0 {w:g} {h}" role="img" aria-label="{escape(label)}">
<title>{escape(label)}</title>
<style>{fonts}{BASE_CSS}{"" if STATIC else KEYFRAMES}</style>
<defs><linearGradient id="gl" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".45"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient></defs>
{body}
</svg>
"""


def paper(w, h, x=0.0):
    return f'<rect x="{x + .5:g}" y=".5" width="{w - 1:g}" height="{h - 1:g}" rx="16" fill="{PAPER}" stroke="{RULE}"/>'


def count_up(x, y, value, unit, size, fill, start):
    """Number that counts up from zero: one <text> per frame, since CSS can't change text content."""
    def t(v, style):
        return (f'<text x="{x:g}" y="{y}" class="s" font-size="{size}" fill="{fill}"{style}>{v:,}'
                f'<tspan class="i"> {escape(unit)}</tspan></text>')
    frames = [] if STATIC else [t(round(value * (1 - (1 - i / 18) ** 3)), f' style="opacity:0;animation:on .05s linear {start + i*.05:.2f}s"')
                                for i in range(18)]
    return "\n".join(frames + [t(value, anim("show", .01, start + .9, "linear both"))])


# ---------- data ----------
def fetch():
    q = """{user(login:"%s"){
      repositories(first:100,ownerAffiliations:OWNER,privacy:PUBLIC){totalCount
        nodes{name homepageUrl stargazerCount primaryLanguage{name}}}
      contributionsCollection{contributionCalendar{totalContributions
        weeks{contributionDays{date contributionCount contributionLevel weekday}}}}}}""" % LOGIN
    user = json.loads(subprocess.run(["gh", "api", "graphql", "-f", f"query={q}"], check=True,
                                     capture_output=True, text=True).stdout)["data"]["user"]
    cal = user["contributionsCollection"]["contributionCalendar"]
    repos = user["repositories"]
    return {"repos": repos["totalCount"], "repo": {r["name"]: r for r in repos["nodes"]},
            "live": sum(1 for r in repos["nodes"] if r["homepageUrl"]),
            "total": cal["totalContributions"], "weeks": [w["contributionDays"] for w in cal["weeks"]]}


def streaks(days):
    """(current, longest). Current streak may start yesterday if today has no contributions yet."""
    counts = [d["contributionCount"] for d in days]
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    i = len(counts) - 1
    if counts and counts[i] == 0:
        i -= 1
    current = 0
    while i >= 0 and counts[i]:
        current, i = current + 1, i - 1
    return current, longest


# ---------- cards ----------
def hero():
    h = 420
    rows = (ROOT / "data" / "portrait.txt").read_text().splitlines()
    # Portrait prints in row by row; metrics match CELL in make_portrait.py (line height / char width).
    ascii_rows = "".join(
        f'<text x="552" y="{60 + r*3.5:.1f}" xml:space="preserve" class="m" font-size="3.2" fill="{INK}" opacity=".85"'
        f'{anim("fade", .3, .35 + r*.018, "ease-out both")}>{escape(line)}</text>' for r, line in enumerate(rows))
    # Shine: a cobalt band clipped to the italic line's letters, swept with CSS so reduced-motion stops it.
    body = f"""<defs><linearGradient id="band" x1="0" x2="1"><stop offset="0" stop-color="{ACCENT}" stop-opacity="0"/>
<stop offset=".5" stop-color="{ACCENT}"/><stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></linearGradient>
<clipPath id="handle"><text x="38" y="278" class="i" font-size="100" letter-spacing="-2">BinaryBhakti</text></clipPath></defs>
{paper(W, h)}
<g{anim("fade", .9, 0, "ease-out both")}><rect x="40" y="46" width="8" height="8" rx="2" fill="{ACCENT}"{loop("blink", 1.6, .9)}/>
<text x="58" y="54" class="m" font-size="12" letter-spacing="1.2" fill="{MUTED}">FULL-STACK &amp; AI ENGINEER</text></g>
<text x="36" y="182" class="s" font-size="108" letter-spacing="-2" fill="{INK}"{anim("rise", .8, .15)}>Ashmit</text>
<g{anim("rise", .8, .3)}><text x="38" y="278" class="i" font-size="100" letter-spacing="-2" fill="{NAVY}">BinaryBhakti</text>
<g clip-path="url(#handle)"><rect x="-260" y="180" width="220" height="130" fill="url(#band)"{loop("shine", 7, 1.6, "transform:translateX(-600px)")}/></g></g>
<g{anim("rise", .8, .55)}><text x="42" y="328" class="g" font-size="17" fill="#2a2a28">I turn ideas into shipped</text>
<text x="42" y="354" class="g" font-size="17" fill="#2a2a28">software, fast.</text></g>
<g{anim("fade", .9, .8, "ease-out both")}><text x="42" y="388" class="m" font-size="13" fill="{INK}">github.com/BinaryBhakti</text>
<text x="232" y="388" class="m" font-size="13" fill="{ACCENT}"{loop("nudgeup", 1.8, 1.8)}>↗</text></g>
{ascii_rows}"""
    return svg(W, h + GAP, body, "Ashmit (BinaryBhakti), full-stack and AI engineer. I turn ideas into shipped software, fast.",
               ["serif", "italic", "sans", "mono"])


def heatmap(d):
    h = 220
    n = len(d["weeks"])
    step = (W - 72) / n
    x0, y0 = 36, 78
    cells, months, last_m, last_col = [], [], None, -9
    for wi, week in enumerate(d["weeks"]):
        for day in week:
            cells.append(f'<rect x="{x0 + wi*step:.1f}" y="{y0 + day["weekday"]*step:.1f}" width="{step-3:.1f}" height="{step-3:.1f}" rx="3" '
                         f'fill="{RAMP[day["contributionLevel"]]}" class="fb"{anim("pop", .4, 1 + wi*.016 + day["weekday"]*.01, "ease-out both")}>'
                         f'<title>{day["date"]}: {day["contributionCount"]}</title></rect>')
        m = week[0]["date"][:7]
        if m != last_m and wi - last_col >= 3 and x0 + wi*step < 690:  # leave room for the legend
            months.append(f'<text x="{x0 + wi*step:.1f}" y="{y0 + 7*step + 16:.0f}" class="m" font-size="10" fill="{MUTED}">'
                          f'{datetime.strptime(m, "%Y-%m").strftime("%b")}</text>')
            last_col = wi
        last_m = m
    ly = y0 + 7 * step + 7
    legend = "".join(f'<rect x="{740 + i*14}" y="{ly:.0f}" width="11" height="11" rx="2" fill="{c}"/>' for i, c in enumerate(RAMP.values()))
    body = f"""{paper(W, h)}
<text x="36" y="54" class="s" font-size="36" fill="{INK}"{anim("rise", .8, .9)}>Showing up, <tspan class="i" fill="{ACCENT}">daily</tspan></text>
<text x="844" y="50" text-anchor="end" class="m" font-size="11" letter-spacing="1.2" fill="{MUTED}"{anim("fade", .8, 1.1)}>REFRESHED EVERY MORNING</text>
{"".join(cells)}
<g{anim("fade", .6, 1.6)}>{"".join(months)}
<text x="732" y="{ly + 9:.0f}" text-anchor="end" class="m" font-size="10" fill="{MUTED}">less</text>{legend}
<text x="814" y="{ly + 9:.0f}" class="m" font-size="10" fill="{MUTED}">more</text></g>"""
    return svg(W, h + GAP, body, f"Contribution graph: {d['total']:,} contributions in the last year, refreshed daily", ["serif", "italic", "mono"])


def activity(d):
    h = 300
    days = [x for wk in d["weeks"] for x in wk]
    per = defaultdict(int)
    for x in days:
        per[x["date"][:7]] += x["contributionCount"]
    months = sorted(per)[-12:]
    top = max(months, key=per.get)
    peak = per[top] or 1
    cur, longest = streaks(days)
    active = sum(1 for x in days if x["contributionCount"])
    busy = max(days, key=lambda x: x["contributionCount"])
    base, maxh, bx, step, bw = 262, 118, 36, 45, 34
    bars = []
    for i, m in enumerate(months):
        bh = max(3, round(per[m] / peak * maxh))
        x = bx + i * step
        colour = ACCENT if m == top else RULE if i == len(months) - 1 else INK  # current month is still filling in
        dl = 2 + i * .06
        bars.append(f'<rect x="{x}" y="{base - bh}" width="{bw}" height="{bh}" rx="3" fill="{colour}" class="fd"{anim("grow", .8, dl)}/>'
                    f'<text x="{x + bw/2}" y="{base + 20}" text-anchor="middle" class="m" font-size="10" fill="{MUTED}">'
                    f'{datetime.strptime(m, "%Y-%m").strftime("%b")}</text>')
        if m == top:
            bars.append(f'<text x="{x + bw/2}" y="{base - bh - 9}" text-anchor="middle" class="m fb" font-size="11" fill="{ACCENT}"'
                        f'{anim("pop", .4, dl + .8, "ease-out both")}>{per[m]:,}</text>')
    stats = [
        (f'{cur} <tspan class="i">day{"s" if cur != 1 else ""}</tspan>', f"current streak, longest {longest}"),
        (f'{active} <tspan fill="{MUTED}">/ {len(days)}</tspan>', "days with a contribution"),
        (f'{busy["contributionCount"]}', f'on the busiest day, {datetime.strptime(busy["date"], "%Y-%m-%d").strftime("%b %-d")}'),
    ]
    right = ""
    for i, (num, cap) in enumerate(stats):
        y = 92 + i * 84
        right += (f'<g{anim("rise", .7, 2.3 + i*.15)}><text x="616" y="{y}" class="s" font-size="40" fill="{INK}">{num}</text>'
                  f'<text x="618" y="{y + 22}" class="g" font-size="12.5" fill="{MUTED}">{escape(cap)}</text></g>')
        if i < 2:
            right += f'<rect x="616" y="{y + 42}" width="228" height="1" fill="{RULE}" class="fl"{anim("draw", .7, 2.4 + i*.15)}/>'
    body = f"""{paper(W, h)}
<text x="36" y="46" class="m" font-size="11" letter-spacing="1.2" fill="{MUTED}"{anim("fade", .7, 1.7)}>THE LAST 12 MONTHS ON GITHUB</text>
<text x="34" y="104" class="s" font-size="56" fill="{INK}"{anim("rise", .8, 1.8)}>{d["total"]:,} <tspan class="i">contributions</tspan></text>
{"".join(bars)}
{right}"""
    return svg(W, h + GAP, body, f"{d['total']:,} contributions in the last 12 months. Current streak {cur} days, longest {longest}.",
               ["serif", "italic", "sans", "mono"])


def tile(i, kicker, big, desc, bg, delay, fg="#fff"):
    """big: (number, unit) to count up, or a plain string."""
    h = 210
    x = i * (GAP - (THIRD - TW))  # shifts each third so the gaps between tiles are exactly GAP
    lines = "".join(f'<text x="{x + 22:g}" y="{150 + j*20}" class="g" font-size="13.5" fill="{fg}" opacity=".9">{escape(l)}</text>'
                    for j, l in enumerate(desc))
    value = (count_up(x + 20, 112, big[0], big[1], 46, fg, delay + .45) if isinstance(big, tuple)
             else f'<text x="{x + 20:g}" y="112" class="i" font-size="46" fill="{fg}"{anim("rise", .7, delay + .45)}>{escape(big)}</text>')
    body = f"""<clipPath id="card"><rect x="{x:g}" width="{TW:g}" height="{h}" rx="16"/></clipPath>
<g class="tile"{anim("tilein", 1.1, delay, "cubic-bezier(.2,.8,.2,1) both")}>
<g clip-path="url(#card)"><rect x="{x:g}" width="{TW:g}" height="{h}" fill="{bg}"/>
<circle cx="{x + 245:g}" cy="172" r="60" fill="none" stroke="{fg}" stroke-opacity=".5" stroke-width="2" class="fb"{loop("ring", 3.2, delay + .5, "opacity:0")}/>
<rect x="{x - 140:g}" y="-20" width="90" height="250" fill="url(#gl)"{loop("sweep", 6, delay + 1.4, "transform:translateX(-400px)")}/></g>
<text x="{x + 22:g}" y="38" class="m" font-size="12" letter-spacing="1.2" fill="{fg}"{anim("slide", .6, delay + .35)}>{escape(kicker)}</text>
<text x="{x + 252:g}" y="38" class="m" font-size="14" fill="{fg}"{loop("nudge", 1.8, delay + 1.3)}>→</text>
{value}
{lines}</g>"""
    label = f"{kicker}: {big[0]:,} {big[1]}" if isinstance(big, tuple) else f"{kicker}: {big}"
    return svg(THIRD, h + GAP, body, f"{label}. {' '.join(desc)}", ["serif", "italic", "sans", "mono"])


def title(text, accent, dark):
    fill, acc = (PAPER, PERI) if dark else (INK, ACCENT)
    body = (f'<text x="2" y="50" class="s" font-size="40" fill="{fill}"{anim("rise", .8, 3.2)}>{escape(text)} '
            f'<tspan class="i" fill="{acc}">{escape(accent)}</tspan></text>')
    return svg(W, 72, body, f"{text} {accent}", ["serif", "italic"])


def repo(i, d, name, title_, desc, colour):
    h = 170
    x = (i % 3) * (GAP - (THIRD - TW))
    r = d["repo"].get(name, {})
    meta = " · ".join(p for p in [(r.get("primaryLanguage") or {}).get("name"), f"★ {r.get('stargazerCount', 0)}",
                                  "live" if r.get("homepageUrl") else None] if p)
    lines = "".join(f'<text x="{x + 22:g}" y="{70 + j*20}" class="g" font-size="13.5" fill="{MUTED}">{escape(l)}</text>'
                    for j, l in enumerate(textwrap.wrap(desc, 36)[:3]))
    body = f"""<g{anim("rise", .8, 3.4 + i*.12)}>{paper(TW, h, x)}
<rect x="{x + 22:g}" y="29" width="8" height="8" fill="{colour}"/>
<text x="{x + 38:g}" y="38" class="g b" font-size="17" fill="{INK}">{escape(title_)}</text>
{lines}
<text x="{x + 22:g}" y="146" class="m" font-size="11" fill="{MUTED}">{escape(meta)}</text></g>"""
    return svg(THIRD, h + GAP, body, f"{title_}: {desc}", ["sans", "bold", "mono"])


# (repo name, card title, description, link). Descriptions wrap at ~36 chars, 3 lines max.
REPOS = [
    ("incidentdesk-devops-capstone", "IncidentDesk", "FastAPI + React incident desk shipped through CI/CD, Terraform EKS, Helm and Argo CD.",
     "https://github.com/BinaryBhakti/incidentdesk-devops-capstone"),
    ("NotebookLLM", "NotebookLLM", "NotebookLM-style RAG app: upload PDFs and chat, with answers grounded in citations.",
     "https://notebook-llm-ochre.vercel.app"),
    ("coolash", "Palette Swift", "Build harmonious colour palettes and check accessibility contrast in one place.",
     "https://paletteswift.netlify.app/"),
    ("WhiteBoash", "WhiteBoash", "Canvas Suite: collaborative whiteboards and structured documents, on Supabase.",
     "https://white-boash-web.vercel.app"),
    ("Agent-CLI-Tool", "Agent CLI Tool", "Gemini-powered CLI agent that clones any public website into clean static files.",
     "https://github.com/BinaryBhakti/Agent-CLI-Tool"),
    ("Website-Automation-Agent", "Web Automation Agent", "Autonomous Gemini + Playwright agent that drives a real browser end to end.",
     "https://github.com/BinaryBhakti/Website-Automation-Agent"),
]

if __name__ == "__main__":
    d = fetch()
    cur, longest = streaks([x for wk in d["weeks"] for x in wk])
    files = {
        "hero.svg": hero(),
        "heatmap.svg": heatmap(d),
        "activity.svg": activity(d),
        "tile-build.svg": tile(0, "BUILD", (d["repos"], "repos"), ["Agents, DevOps pipelines and", "web apps, built in the open."], ACCENT, 2.8),
        "tile-ship.svg": tile(1, "SHIP", (d["live"], "live apps"), ["Deployed on Vercel and Netlify.", "Try a few below."], NAVY, 2.95),
        "tile-hello.svg": tile(2, "SAY HELLO", "@imashmit_", ["Notes on building with AI.", "DMs are open."], PERI, 3.1, fg=NAVY),
        "title-work-light.svg": title("What I'm", "building", dark=False),
        "title-work-dark.svg": title("What I'm", "building", dark=True),
    }
    colours = [ACCENT, NAVY, PERI]
    files |= {f"repo-{name.lower()}.svg": repo(i, d, name, t, desc, colours[i % 3]) for i, (name, t, desc, _) in enumerate(REPOS)}
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.svg"):  # the folder holds exactly what this script draws
        old.unlink()
    for name, s in files.items():
        (OUT / name).write_text(s)
    assert all((OUT / n).stat().st_size < 250_000 for n in files), "card too large for camo"
    assert all(r[0] in d["repo"] for r in REPOS), "a REPOS entry is not a public repo"
    print(f"wrote {len(files)} cards ({'static' if STATIC else 'animated'}); total={d['total']} repos={d['repos']} "
          f"live={d['live']} streak={cur}/{longest}")
