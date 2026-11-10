"""Renders every animated SVG card in assets/ from live GitHub data.

Run:      python3 scripts/build_cards.py            (needs `gh` logged in, or GH_TOKEN set)
Preview:  STATIC=1 python3 scripts/build_cards.py   (final frame only, for screenshots)

GitHub shows these through <img>, which sandboxes the SVG: no scripts, no network.
So fonts are embedded as base64 woff2 and all motion is CSS inside each SVG. Every element's
base style is its final state and keyframes animate *from* hidden, so reduced-motion and
STATIC both simply drop the animations.
"""
import base64, json, os, subprocess
from collections import defaultdict
from datetime import date, datetime
from html import escape
from pathlib import Path

LOGIN = "BinaryBhakti"
ROOT = Path(__file__).resolve().parent.parent
OUT, FONTS = ROOT / "assets", ROOT / "fonts"
STATIC = os.environ.get("STATIC") == "1"

# Kora Kaagaz palette (KoraKaagaz/app/globals.css)
PAPER, PAPER2, INK, MUTED, RULE, NAVY, ACCENT = "#faf8f3", "#f1ede4", "#171717", "#66655f", "#d6d5d1", "#071a43", "#3a5bb0"
RAMP = {"NONE": "#ebe7dc", "FIRST_QUARTILE": "#c9d3ea", "SECOND_QUARTILE": "#8fa3d4", "THIRD_QUARTILE": ACCENT, "FOURTH_QUARTILE": NAVY}

FACES = {  # key: (file, family, css descriptors)
    "serif": ("serif-400.woff2", "KS", "font-style:normal"),
    "italic": ("serif-italic.woff2", "KS", "font-style:italic"),
    "sans": ("sans-450.woff2", "KG", "font-weight:400"),
    "bold": ("sans-650.woff2", "KG", "font-weight:600"),
}

KEYFRAMES = """
@keyframes rise{from{opacity:0;transform:translateY(22px)}}
@keyframes fade{from{opacity:0}}
@keyframes draw{from{transform:scaleX(0)}}
@keyframes drawy{from{transform:scaleY(0)}}
@keyframes grow{from{transform:scaleY(0)}}
@keyframes pop{0%{opacity:0;transform:scale(.2)}70%{transform:scale(1.15)}100%{transform:none}}
@keyframes swing{0%{opacity:0;transform:translateY(70px) rotate(-6deg)}60%{opacity:1;transform:translateY(-8px) rotate(1.2deg)}82%{transform:translateY(2px) rotate(-.4deg)}100%{transform:none}}
@keyframes sweep{0%{transform:translateX(0)}30%,100%{transform:translateX(1500px)}}
@keyframes pulse{0%{opacity:.7;transform:scale(1)}70%,100%{opacity:0;transform:scale(3.2)}}
@keyframes nudge{0%,55%,100%{transform:none}75%{transform:translateX(6px)}}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes on{0%,100%{opacity:1}}
@keyframes show{from{opacity:0}to{opacity:1}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
"""
BASE_CSS = """.s{font-family:KS,Georgia,serif}.i{font-family:KS,Georgia,serif;font-style:italic}
.g{font-family:KG,-apple-system,'Segoe UI',Helvetica,Arial,sans-serif}.b{font-weight:600}
.c{letter-spacing:.22em}.fb{transform-box:fill-box;transform-origin:center}
.fl{transform-box:fill-box;transform-origin:left center}.fd{transform-box:fill-box;transform-origin:center bottom}"""
EASE = "cubic-bezier(.2,.75,.2,1)"


def anim(name, dur, delay=0.0, tail=f"{EASE} both"):
    """Inline animation style, or nothing in STATIC mode."""
    return "" if STATIC else f' style="animation:{name} {dur}s {tail};animation-delay:{delay:.3f}s"'


def svg(w, h, body, label, faces, frame=True):
    fonts = "".join(
        f"@font-face{{font-family:{fam};{desc};src:url(data:font/woff2;base64,"
        f"{base64.b64encode((FONTS / f).read_bytes()).decode()}) format('woff2')}}"
        for f, fam, desc in (FACES[k] for k in faces))
    box = (f'<rect x="8" y="6" width="{w-16}" height="{h-16}" rx="14" fill="{PAPER}" stroke="{RULE}" filter="url(#sh)"/>'
           if frame else "")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(label)}">
<title>{escape(label)}</title>
<style>{fonts}{BASE_CSS}{"" if STATIC else KEYFRAMES}</style>
<defs><filter id="sh" x="-5%" y="-5%" width="110%" height="125%"><feDropShadow dx="0" dy="3" stdDeviation="4" flood-color="{INK}" flood-opacity="0.08"/></filter>
<linearGradient id="gl" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".55"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient></defs>
{box}
{body}
</svg>
"""


def count_up(x, y, value, cls, size, fill, start, anchor="start"):
    """Number that counts up from zero: one <text> per frame (CSS can't change text content)."""
    out = []
    if not STATIC:
        for i in range(18):
            v = round(value * (1 - (1 - i / 18) ** 3))
            out.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" class="{cls}" font-size="{size}" fill="{fill}" '
                       f'style="opacity:0;animation:on .05s linear {start + i*0.05:.2f}s">{v:,}</text>')
    out.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" class="{cls}" font-size="{size}" fill="{fill}"'
               f'{anim("show", .01, start + 18*0.05, "linear both")}>{value:,}</text>')
    return "\n".join(out)


# ---------- data ----------
def fetch():
    q = """{user(login:"%s"){followers{totalCount}
      repositories(ownerAffiliations:OWNER,privacy:PUBLIC){totalCount}
      contributionsCollection{contributionCalendar{totalContributions
        weeks{contributionDays{date contributionCount contributionLevel weekday}}}}}}""" % LOGIN
    data = json.loads(subprocess.run(["gh", "api", "graphql", "-f", f"query={q}"], check=True,
                                     capture_output=True, text=True).stdout)["data"]["user"]
    cal = data["contributionsCollection"]["contributionCalendar"]
    return {"followers": data["followers"]["totalCount"], "repos": data["repositories"]["totalCount"],
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
    w, h = 1000, 360
    month = date.today().strftime("%B %Y").upper()
    ring = "BINARYBHAKTI · BUILDING IN PUBLIC · OPEN SOURCE · SHIPPING · "
    body = f"""<text x="48" y="58" class="g b c" font-size="12" fill="{MUTED}"{anim("fade", .8, .1)}>BINARYBHAKTI · GITHUB PROFILE · {month}</text>
<rect x="48" y="73" width="904" height="1.6" fill="{INK}" class="fl"{anim("draw", 1.1, .2)}/>
<rect x="48" y="78" width="904" height="1" fill="{RULE}" class="fl"{anim("draw", 1.1, .35)}/>
<clipPath id="nm"><text x="44" y="198" class="s" font-size="132">Ashmit</text></clipPath>
<g{anim("rise", 1, .45)}>
  <text x="44" y="198" class="s" font-size="132" fill="{NAVY}">Ashmit</text>
  <g clip-path="url(#nm)"><rect x="-260" y="60" width="160" height="170" fill="url(#gl)" transform="skewX(-20)"{anim("sweep", 5, 1.8, "ease-in-out infinite")}/></g>
</g>
<text x="48" y="242" class="i" font-size="30" fill="{INK}"{anim("rise", .9, .75)}>Full-stack &amp; AI engineer, building agents,</text>
<text x="48" y="278" class="i" font-size="30" fill="{INK}"{anim("rise", .9, .9)}>DevOps pipelines and design-first web apps.</text>
<g{anim("fade", .8, 1.2)}>
  <circle cx="54" cy="314" r="5" fill="{ACCENT}"/>
  <circle cx="54" cy="314" r="5" fill="{ACCENT}" class="fb" style="opacity:0{"" if STATIC else ";animation:pulse 2.2s ease-out 1.5s infinite"}"/>
  <text x="68" y="319" class="g" font-size="14" fill="{INK}">Open to collaborations</text>
  <text x="232" y="319" class="g" font-size="14" fill="{MUTED}">·  Next.js  ·  TypeScript  ·  Python  ·  Kubernetes</text>
</g>
<g{anim("pop", 1.1, .6)} class="fb">
  <circle cx="850" cy="196" r="104" fill="{PAPER2}" stroke="{RULE}"/>
  <circle cx="850" cy="196" r="70" fill="none" stroke="{RULE}"/>
  <path id="rp" d="M850,196 m-88,0 a88,88 0 1,1 176,0 a88,88 0 1,1 -176,0" fill="none"/>
  <g class="fb"{anim("spin", 40, 0, "linear infinite")}>
    <circle cx="850" cy="196" r="96" fill="none" stroke="none"/>
    <text class="g b" font-size="11.5" letter-spacing="2.9" fill="{NAVY}"><textPath href="#rp">{ring}</textPath></text>
  </g>
  <text x="850" y="222" text-anchor="middle" class="i" font-size="80" fill="{NAVY}">A</text>
</g>"""
    return svg(w, h, body, "Ashmit: Full-stack and AI engineer building agents, DevOps pipelines and design-first web apps",
               ["serif", "italic", "sans", "bold"])


def tile(kicker, value, caption, cta, bg, delay):
    w, h = 330, 220
    body = f"""<clipPath id="tc"><rect x="8" y="8" width="314" height="200" rx="18"/></clipPath>
<g class="fb"{anim("swing", 1.1, delay)}>
  <rect x="8" y="8" width="314" height="200" rx="18" fill="{bg}" filter="url(#sh)"/>
  <g clip-path="url(#tc)"><rect x="-200" y="-40" width="120" height="300" fill="url(#gl)" opacity=".5" transform="skewX(-18)"{anim("sweep", 6, delay + 1.6, "ease-in-out infinite")}/></g>
  <text x="32" y="46" class="g b c" font-size="12" fill="{PAPER}" opacity=".8">{escape(kicker)}</text>
  <circle cx="292" cy="40" r="5" fill="{PAPER}"/>
  <circle cx="292" cy="40" r="5" fill="none" stroke="{PAPER}" class="fb" style="opacity:0{"" if STATIC else f";animation:pulse 2.4s ease-out {delay+1.2:.2f}s infinite"}"/>
  {count_up(30, 132, value, "s", 84, PAPER, delay + .5)}
  <text x="32" y="160" class="g" font-size="14" fill="{PAPER}" opacity=".85">{escape(caption)}</text>
  <text x="32" y="188" class="g b" font-size="13" fill="{PAPER}">{escape(cta)}</text>
  <text x="{40 + len(cta)*7.4:.0f}" y="188" class="g b" font-size="13" fill="{PAPER}"{anim("nudge", 2.2, delay + 2, "ease-in-out infinite")}>→</text>
</g>"""
    return svg(w, h, body, f"{kicker}: {value:,} {caption}", ["serif", "sans", "bold"], frame=False)


def heatmap(d):
    w, h = 1000, 290
    x0, y0, step = 104, 112, 16
    cells, months, last_m, last_col = [], [], None, -9
    for wi, week in enumerate(d["weeks"]):
        for day in week:
            dly = .4 + wi * .018 + day["weekday"] * .01
            cells.append(f'<rect x="{x0 + wi*step}" y="{y0 + day["weekday"]*step}" width="12" height="12" rx="3" '
                         f'fill="{RAMP[day["contributionLevel"]]}" class="fb"{anim("pop", .45, dly)}>'
                         f'<title>{day["date"]}: {day["contributionCount"]}</title></rect>')
        m = week[0]["date"][:7]
        if m != last_m and wi - last_col >= 3:
            label = datetime.strptime(m, "%Y-%m").strftime("%b")
            months.append(f'<text x="{x0 + wi*step}" y="{y0 - 10}" class="g" font-size="11" fill="{MUTED}">{label}</text>')
            last_col = wi
        last_m = m
    days = "".join(f'<text x="{x0 - 12}" y="{y0 + i*step + 10}" text-anchor="end" class="g" font-size="11" fill="{MUTED}">{n}</text>'
                   for i, n in ((1, "Mon"), (3, "Wed"), (5, "Fri")))
    legend = "".join(f'<rect x="{846 + i*16}" y="{y0 + 7*step + 16}" width="12" height="12" rx="3" fill="{c}"/>'
                     for i, c in enumerate(RAMP.values()))
    head = f'{d["total"]:,} contributions'
    body = f"""<text x="48" y="62" class="s" font-size="36" fill="{NAVY}"{anim("rise", .8, .1)}>{head}</text>
<text x="{58 + len(head)*13:.0f}" y="62" class="i" font-size="24" fill="{MUTED}"{anim("fade", .8, .3)}>in the last year</text>
<g{anim("fade", .6, .3)}>{"".join(months)}{days}</g>
{"".join(cells)}
<g{anim("fade", .6, 1.4)}><text x="838" y="{y0 + 7*step + 26}" text-anchor="end" class="g" font-size="11" fill="{MUTED}">Less</text>{legend}
<text x="930" y="{y0 + 7*step + 26}" class="g" font-size="11" fill="{MUTED}">More</text></g>"""
    return svg(w, h, body, f"{d['total']:,} contributions in the last year", ["serif", "italic", "sans"])


def activity(d):
    w, h = 1000, 310
    days = [x for wk in d["weeks"] for x in wk]
    per = defaultdict(int)
    for x in days:
        per[x["date"][:7]] += x["contributionCount"]
    months = sorted(per)[-12:]
    top = max(months, key=per.get)
    peak = max(per[m] for m in months) or 1
    cur, longest = streaks(days)
    busy = max(days, key=lambda x: x["contributionCount"])
    base, maxh, bx, bw, gap = 236, 128, 52, 32, 47
    bars = []
    for i, m in enumerate(months):
        bh = max(3, round(per[m] / peak * maxh))
        x = bx + i * gap
        best = m == top
        bars.append(f'<rect x="{x}" y="{base - bh}" width="{bw}" height="{bh}" rx="5" fill="{NAVY if best else "#c9d3ea"}" '
                    f'class="fd"{anim("grow", .8, .4 + i*.07)}/>')
        bars.append(f'<text x="{x + bw/2}" y="{base + 20}" text-anchor="middle" class="g" font-size="11" fill="{MUTED}">'
                    f'{datetime.strptime(m, "%Y-%m").strftime("%b")}</text>')
        if best:
            bars.append(f'<text x="{x + bw/2}" y="{base - bh - 10}" text-anchor="middle" class="g b fb" font-size="13" fill="{NAVY}"'
                        f'{anim("pop", .5, .4 + i*.07 + .8)}>{per[m]:,}</text>')
    stats = [("CURRENT STREAK", f"{cur} day{'s' if cur != 1 else ''}"), ("LONGEST STREAK", f"{longest} days"),
             ("BUSIEST DAY", f"{busy['contributionCount']} on {datetime.strptime(busy['date'], '%Y-%m-%d').strftime('%b %-d')}"),
             ("BEST MONTH", datetime.strptime(top, "%Y-%m").strftime("%B"))]
    cells = "".join(
        f'<g{anim("rise", .7, .7 + i*.12)}><text x="{x}" y="{y}" class="g b c" font-size="10.5" fill="{MUTED}">{k}</text>'
        f'<text x="{x}" y="{y + 36}" class="s" font-size="32" fill="{NAVY}">{escape(v)}</text></g>'
        for i, ((k, v), (x, y)) in enumerate(zip(stats, [(680, 112), (840, 112), (680, 200), (840, 200)])))
    body = f"""<text x="48" y="62" class="s" font-size="36" fill="{NAVY}"{anim("rise", .8, .1)}>Monthly rhythm</text>
<text x="292" y="62" class="i" font-size="24" fill="{MUTED}"{anim("fade", .8, .3)}>last twelve months</text>
<rect x="48" y="{base}" width="560" height="1" fill="{RULE}" class="fl"{anim("draw", .8, .2)}/>
{"".join(bars)}
<rect x="646" y="96" width="1" height="164" fill="{RULE}" class="fd"{anim("drawy", .8, .5)}/>
{cells}"""
    return svg(w, h, body, f"Monthly contributions. Current streak {cur}, longest {longest}.", ["serif", "italic", "sans", "bold"])


def section(num, title, kicker):
    w, h = 1000, 92
    body = f"""<text x="40" y="58" class="g b" font-size="13" fill="{ACCENT}"{anim("fade", .6, .1)}>{num}</text>
<text x="76" y="60" class="s" font-size="38" fill="{NAVY}"{anim("rise", .8, .15)}>{escape(title)}</text>
<text x="960" y="56" text-anchor="end" class="g b c" font-size="11" fill="{MUTED}"{anim("fade", .8, .4)}>{escape(kicker.upper())}</text>
<rect x="40" y="76" width="920" height="1.5" fill="{INK}" class="fl"{anim("draw", 1, .3)}/>"""
    return svg(w, h, body, title, ["serif", "sans", "bold"], frame=False)


def project(i, name, lines, tag, cta):
    w, h = 490, 180
    d0 = .1 + i * .12
    tw = len(tag) * 8.5 + 26
    desc = "".join(f'<text x="34" y="{108 + j*22}" class="g" font-size="14.5" fill="{MUTED}">{escape(l)}</text>' for j, l in enumerate(lines))
    body = f"""<g{anim("rise", .8, d0)}>
<text x="32" y="62" class="s" font-size="34" fill="{INK}">{escape(name)}</text>
<rect x="{w - 34 - tw:.0f}" y="36" width="{tw:.0f}" height="26" rx="13" fill="{PAPER2}" stroke="{RULE}"/>
<text x="{w - 34 - tw/2:.0f}" y="53.5" text-anchor="middle" class="g b c" font-size="10.5" fill="{NAVY}">{escape(tag.upper())}</text>
</g>
<rect x="34" y="80" width="{w - 68}" height="1" fill="{RULE}" class="fl"{anim("draw", .9, d0 + .2)}/>
<g{anim("fade", .8, d0 + .35)}>{desc}
<text x="{w - 56}" y="{h - 30}" text-anchor="end" class="g b" font-size="13" fill="{ACCENT}">{escape(cta)}</text>
<text x="{w - 50}" y="{h - 30}" class="g b" font-size="13" fill="{ACCENT}"{anim("nudge", 2.4, d0 + 1.5, "ease-in-out infinite")}>→</text></g>"""
    return svg(w, h, body, f"{name}: {' '.join(lines)}", ["serif", "sans", "bold"])


def social(i, label, handle):
    w, h = 490, 120
    d0 = .1 + i * .12
    body = f"""<g{anim("rise", .8, d0)}>
<circle cx="56" cy="58" r="22" fill="{NAVY}"/>
<text x="56" y="66" text-anchor="middle" class="i" font-size="24" fill="{PAPER}">{escape(label[0])}</text>
<text x="96" y="48" class="g b c" font-size="11" fill="{MUTED}">{escape(label.upper())}</text>
<text x="96" y="80" class="s" font-size="30" fill="{INK}">{escape(handle)}</text>
<text x="{w - 44}" y="68" class="g b" font-size="18" fill="{ACCENT}"{anim("nudge", 2.4, d0 + 1.2, "ease-in-out infinite")}>→</text></g>"""
    return svg(w, h, body, f"{label} {handle}", ["serif", "italic", "sans", "bold"])


# (file, name, description lines, tag, cta). Keep lines short: SVG text does not wrap.
PROJECTS = [
    ("incidentdesk", "IncidentDesk", ["FastAPI + React incident desk shipped through CI/CD,", "Terraform EKS, Helm, Argo CD and Prometheus."], "DevOps", "View repo"),
    ("notebookllm", "NotebookLLM", ["NotebookLM-style RAG app: upload PDFs and chat,", "with answers grounded in inline citations."], "AI", "Open live"),
    ("paletteswift", "Palette Swift", ["Build harmonious colour palettes and check", "accessibility contrast, all in one place."], "Design", "Open live"),
    ("whiteboash", "WhiteBoash", ["Canvas Suite: collaborative whiteboards", "and structured documents, on Supabase."], "Web", "Open live"),
    ("agent-cli", "Agent CLI Tool", ["Gemini-powered CLI agent that clones any", "public website into clean static files."], "AI", "View repo"),
    ("web-automation", "Web Automation Agent", ["Autonomous Gemini + Playwright agent that", "drives a real browser end to end."], "Python", "View repo"),
]

if __name__ == "__main__":
    d = fetch()
    cur, longest = streaks([x for wk in d["weeks"] for x in wk])
    files = {
        "hero.svg": hero(),
        "tile-build.svg": tile("BUILD", d["repos"], "public repositories", "Browse repos", NAVY, .1),
        "tile-ship.svg": tile("SHIP", d["total"], "contributions this year", "See activity", ACCENT, .25),
        "tile-streak.svg": tile("STREAK", longest, "day longest streak", "Follow along", INK, .4),
        "heatmap.svg": heatmap(d),
        "activity.svg": activity(d),
        "section-work.svg": section("01", "Selected work", "Things I've shipped"),
        "section-social.svg": section("02", "Elsewhere", "Say hello"),
        "social-github.svg": social(0, "GitHub", "@BinaryBhakti"),
        "social-x.svg": social(1, "X / Twitter", "@imashmit_"),
    }
    files |= {f"project-{f}.svg": project(i, n, l, t, c) for i, (f, n, l, t, c) in enumerate(PROJECTS)}
    OUT.mkdir(exist_ok=True)
    for name, s in files.items():
        (OUT / name).write_text(s)
    assert all((OUT / n).stat().st_size < 200_000 for n in files), "card too large for camo"
    print(f"wrote {len(files)} cards ({'static' if STATIC else 'animated'}); total={d['total']} repos={d['repos']} streak={cur}/{longest}")
