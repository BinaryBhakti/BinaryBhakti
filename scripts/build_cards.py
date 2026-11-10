"""Builds the custom SVG cards in assets/. Run: python3 scripts/build_cards.py
SVGs are embedded via <img>, so GitHub loads no web fonts: system font stacks only."""
from html import escape
from pathlib import Path

# Kora Kaagaz palette (KoraKaagaz/app/globals.css)
PAPER, PAPER2, INK, MUTED, RULE, NAVY, ACCENT = "#faf8f3", "#f1ede4", "#171717", "#66655f", "#d6d5d1", "#071a43", "#3a5bb0"
SERIF = "Georgia, 'Times New Roman', serif"
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
OUT = Path(__file__).resolve().parent.parent / "assets"


def card(w, h, body, label):
    # 8px margin leaves room for the soft shadow inside the viewBox.
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(label)}">
<defs><filter id="s" x="-5%" y="-5%" width="110%" height="120%"><feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="{INK}" flood-opacity="0.08"/></filter></defs>
<rect x="8" y="6" width="{w-16}" height="{h-16}" rx="12" fill="{PAPER}" stroke="{RULE}" filter="url(#s)"/>
{body}
</svg>
"""


def header():
    w, h = 1000, 260
    body = f"""<text x="48" y="58" font-family="{SANS}" font-size="12" letter-spacing="3" fill="{MUTED}">BINARYBHAKTI · GITHUB PROFILE</text>
<line x1="48" y1="74" x2="{w-48}" y2="74" stroke="{INK}" stroke-width="1.5"/>
<line x1="48" y1="78" x2="{w-48}" y2="78" stroke="{RULE}"/>
<text x="46" y="156" font-family="{SERIF}" font-size="68" font-weight="700" fill="{NAVY}">Ashmit</text>
<text x="48" y="194" font-family="{SERIF}" font-size="20" font-style="italic" fill="{INK}">Full-stack &amp; AI engineer · agents, DevOps and design-first web apps.</text>
<rect x="48" y="212" width="8" height="8" rx="4" fill="{ACCENT}"/>
<text x="64" y="220" font-family="{SANS}" font-size="13" fill="{MUTED}">Open to collaborations · Next.js · TypeScript · Python · Kubernetes</text>"""
    return card(w, h, body, "Ashmit: Full-stack and AI engineer")


def section(title, kicker):
    w, h = 1000, 76
    body = f"""<rect x="8" y="6" width="6" height="60" rx="3" fill="{NAVY}"/>
<text x="36" y="44" font-family="{SERIF}" font-size="26" font-weight="700" fill="{NAVY}">{escape(title)}</text>
<text x="{w-36}" y="43" text-anchor="end" font-family="{SANS}" font-size="12" letter-spacing="2" fill="{MUTED}">{escape(kicker.upper())}</text>"""
    return card(w, h, body, title)


def project(name, lines, tag, link_hint):
    w, h = 490, 160
    desc = "".join(
        f'<text x="32" y="{92 + i*22}" font-family="{SANS}" font-size="14" fill="{MUTED}">{escape(l)}</text>' for i, l in enumerate(lines)
    )
    body = f"""<text x="32" y="56" font-family="{SERIF}" font-size="22" font-weight="700" fill="{INK}">{escape(name)}</text>
<rect x="{w-32-len(tag)*8-20}" y="36" width="{len(tag)*8+20}" height="26" rx="13" fill="{PAPER2}" stroke="{RULE}"/>
<text x="{w-32-(len(tag)*8+20)/2}" y="54" text-anchor="middle" font-family="{SANS}" font-size="12" fill="{NAVY}">{escape(tag)}</text>
<line x1="32" y1="70" x2="{w-40}" y2="70" stroke="{RULE}"/>
{desc}
<text x="{w-40}" y="{h-26}" text-anchor="end" font-family="{SANS}" font-size="12" font-weight="600" fill="{ACCENT}">{escape(link_hint)} →</text>"""
    return card(w, h, body, f"{name}: {' '.join(lines)}")


def social(label, handle):
    w, h = 320, 84
    body = f"""<circle cx="44" cy="40" r="6" fill="{NAVY}"/>
<text x="62" y="38" font-family="{SANS}" font-size="11" letter-spacing="2" fill="{MUTED}">{escape(label.upper())}</text>
<text x="62" y="58" font-family="{SERIF}" font-size="18" font-weight="700" fill="{INK}">{escape(handle)}</text>"""
    return card(w, h, body, f"{label} {handle}")


# (file, name, description lines, tag, link hint) — keep lines under ~55 chars; SVG text does not wrap.
PROJECTS = [
    ("incidentdesk", "IncidentDesk", ["FastAPI + React incident desk shipped through CI/CD,", "Terraform EKS, Helm, Argo CD and Prometheus."], "DevOps", "Repo"),
    ("notebookllm", "NotebookLLM", ["NotebookLM-style RAG app: upload PDFs and chat,", "with answers grounded in inline citations."], "AI", "Live"),
    ("paletteswift", "Palette Swift", ["Build harmonious colour palettes and check", "accessibility contrast, all in one place."], "Design", "Live"),
    ("whiteboash", "WhiteBoash", ["Canvas Suite: collaborative whiteboards", "and structured documents, on Supabase."], "Web", "Live"),
    ("agent-cli", "Agent CLI Tool", ["Gemini-powered CLI agent that clones any", "public website into clean static files."], "AI", "Repo"),
    ("web-automation", "Web Automation Agent", ["Autonomous Gemini + Playwright agent that", "drives a real browser end to end."], "Python", "Repo"),
]

if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    files = {"header.svg": header(),
             "section-stats.svg": section("By the numbers", "Activity · Languages"),
             "section-work.svg": section("Selected work", "Projects"),
             "section-social.svg": section("Elsewhere", "Say hello"),
             "social-github.svg": social("GitHub", "@BinaryBhakti"),
             "social-x.svg": social("X / Twitter", "@imashmit_")}
    files |= {f"project-{f}.svg": project(n, l, t, k) for f, n, l, t, k in PROJECTS}
    for name, svg in files.items():
        (OUT / name).write_text(svg)
    print(f"wrote {len(files)} cards to {OUT}")
