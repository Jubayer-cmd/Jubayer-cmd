"""Build the profile header SVGs (light + dark) from one set of tokens.

The header is a map of the work: rows are layers of the stack, columns are
jobs, and one trace runs through every layer I've shipped in, ending at now.

Run:  uv run --with fonttools --with brotli python assets/build_header.py <fonts-dir>
"""

import base64
import io
import math
import sys
from xml.sax.saxutils import escape
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

OUT = Path(__file__).parent
FONTS = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT

# bg matches GitHub's page so hollow nodes read as rings over the trace
THEMES = {
    "light": dict(ink="#15171c", graphite="#5e6370", hairline="#dde0e5", teal="#0a6b66", bg="#ffffff"),
    "dark": dict(ink="#e6e8eb", graphite="#9aa1ad", hairline="#30363d", teal="#3fb8ad", bg="#0d1117"),
}

W, H = 1200, 548
LEFT, RIGHT = 48, 1152

NAME = "Sheikh Abu Jubayer"
ROLE = "Full-Stack & AI Engineer"
LINE = "I ship whole products: interface, APIs, data, infra and the AI inside them."
PLACE = "Dhaka, Bangladesh · Remote"
OPEN = "open to remote roles"

# The grid
ROWS = ["team", "interface", "backend", "data", "infra", "ai"]
ROW_Y0, ROW_STEP = 304, 38
COLS = [("Grit", "2022–24", 196), ("Antopolis", "2024–25", 520), ("Verbacall", "2025–now", 844)]
HEAD_Y, TOP_RAIL, BOTTOM_RAIL = 250, 274, 520

# Stops in the order the trace visits them: down Grit, up Antopolis, down Verbacall
STOPS = [
    (0, "interface", "Unive: web and React Native apps"),
    (0, "backend", "REST APIs in Node and Express"),
    (0, "data", "PostgreSQL data model, Prisma"),
    (1, "infra", "CI/CD and Docker deployments"),
    (1, "backend", "APIs for CRM, e-commerce, CMS"),
    (1, "team", "Led 12 engineers, 15+ products"),
    (2, "team", "Plan and guide platform work"),
    (2, "interface", "No-code flow builder, React Flow"),
    (2, "backend", "NestJS + gRPC services, own OAuth"),
    (2, "data", "Postgres indexes, Redis job queues"),
    (2, "infra", "OpenTelemetry tracing, AWS"),
    (2, "ai", "AI agents, MCP tools, LLM evals"),
]

DRAW, START = 3.6, 0.3  # seconds: trace draw time, delay before it starts
CORNER = 10


def row_y(name):
    return ROW_Y0 + ROWS.index(name) * ROW_STEP


def col_x(i):
    return COLS[i][2]


def font_face(family, file, text):
    """Subset a font to the glyphs in `text` and return an inline @font-face."""
    font = TTFont(FONTS / file)
    opts = subset.Options()
    opts.flavor = "woff"
    opts.layout_features = ["kern", "liga"]
    sub = subset.Subsetter(opts)
    sub.populate(text=text)
    sub.subset(font)
    font.flavor = "woff"
    buf = io.BytesIO()
    font.save(buf)
    data = base64.b64encode(buf.getvalue()).decode()
    return f"@font-face{{font-family:'{family}';src:url(data:font/woff;base64,{data}) format('woff');}}"


def route():
    """Waypoints of the serpentine trace: down each column, across a rail, back."""
    pts = [(col_x(0), row_y(STOPS[0][1]))]
    pts += [(col_x(0), BOTTOM_RAIL), (col_x(1), BOTTOM_RAIL)]
    pts += [(col_x(1), TOP_RAIL), (col_x(2), TOP_RAIL)]
    pts += [(col_x(2), row_y(STOPS[-1][1]))]
    return pts


def rounded_path(pts, r):
    """SVG path through `pts` with each corner rounded by radius r."""
    d = [f"M{pts[0][0]} {pts[0][1]}"]
    for (ax, ay), (px, py), (bx, by) in zip(pts, pts[1:], pts[2:]):
        ux, uy = (px - ax) / math.dist((ax, ay), (px, py)), (py - ay) / math.dist((ax, ay), (px, py))
        vx, vy = (bx - px) / math.dist((px, py), (bx, by)), (by - py) / math.dist((px, py), (bx, by))
        d.append(f"L{px - ux * r:g} {py - uy * r:g}")
        d.append(f"Q{px} {py} {px + vx * r:g} {py + vy * r:g}")
    d.append(f"L{pts[-1][0]} {pts[-1][1]}")
    return " ".join(d)


def progress(pts, point):
    """Fraction of the trace's length travelled when it reaches `point`."""
    total, before = 0.0, None
    for a, b in zip(pts, pts[1:]):
        seg = math.dist(a, b)
        on_seg = (min(a[0], b[0]) <= point[0] <= max(a[0], b[0])
                  and min(a[1], b[1]) <= point[1] <= max(a[1], b[1]))
        if before is None and on_seg:
            before = total + math.dist(a, point)
        total += seg
    return before / total


def build(theme):
    c = THEMES[theme]
    chips = "".join(text for _, _, text in STOPS)
    labels = "".join(ROWS) + "".join(co + yrs for co, yrs, _ in COLS) + " ·"
    faces = "".join([
        font_face("Bricolage", "bricolage-700.woff2", NAME),
        font_face("PlexSans", "plex-sans-500.woff2", ROLE),
        font_face("PlexSansRegular", "plex-sans-400.woff2", LINE + chips),
        font_face("PlexMono", "plex-mono-400.woff2", PLACE + OPEN + labels),
    ])
    pts = route()

    row_labels = "\n  ".join(
        f'<text class="mono" x="{LEFT}" y="{row_y(r) + 5}">{r}</text>' for r in ROWS
    )
    heads = "\n  ".join(
        f'<text class="mono" x="{x - 5}" y="{HEAD_Y}"><tspan class="co">{co}</tspan> · {yrs}</text>'
        for co, yrs, x in COLS
    )
    nodes = []
    for i, (col, row, text) in enumerate(STOPS):
        x, y = col_x(col), row_y(row)
        delay = START + progress(pts, (x, y)) * DRAW
        last = i == len(STOPS) - 1
        dot = (f'<circle class="live" cx="{x}" cy="{y}" r="6" fill="{c["teal"]}"/>' if last else
               f'<circle cx="{x}" cy="{y}" r="5" fill="{c["bg"]}" stroke="{c["teal"]}" stroke-width="2"/>')
        nodes.append(
            f'<g class="n" style="animation-delay:{delay:.2f}s">{dot}'
            f'<text class="chip" x="{x + 20}" y="{y + 5.5}">{escape(text)}</text></g>'
        )
    nodes = "\n  ".join(nodes)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">
  <title id="t">{escape(NAME)}, {escape(ROLE)}</title>
  <desc id="d">A map of my work across the stack, from Grit (2022) through Antopolis to Verbacall (now): interface, backend, data, infra, team and AI.</desc>
  <style>
    {faces}
    .name {{ font: 700 64px 'Bricolage', sans-serif; fill: {c['ink']}; }}
    .role {{ font: 500 26px 'PlexSans', sans-serif; fill: {c['teal']}; }}
    .line {{ font: 400 22px 'PlexSansRegular', sans-serif; fill: {c['graphite']}; }}
    .chip {{ font: 400 16px 'PlexSansRegular', sans-serif; fill: {c['ink']}; }}
    .mono {{ font: 400 15px 'PlexMono', monospace; fill: {c['graphite']}; }}
    .co {{ fill: {c['teal']}; }}
    .trace {{ stroke-dasharray: 1; animation: draw {DRAW}s linear {START}s both; }}
    .n {{ animation: appear .5s ease-out both; }}
    .live {{ animation: pulse 2.4s ease-in-out {START + DRAW + .5:.1f}s infinite; }}
    @keyframes draw {{ from {{ stroke-dashoffset: 1; }} to {{ stroke-dashoffset: 0; }} }}
    @keyframes appear {{ from {{ opacity: 0; transform: translateX(-6px); }} to {{ opacity: 1; transform: none; }} }}
    @keyframes pulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: .3; }} }}
    @media (prefers-reduced-motion: reduce) {{
      .trace, .n, .live {{ animation: none; }}
    }}
  </style>

  <text class="name" x="{LEFT - 3}" y="100">{NAME}</text>
  <text class="role" x="{LEFT}" y="146">{escape(ROLE)}</text>
  <text class="line" x="{LEFT}" y="182">{LINE}</text>

  <text class="mono" x="{RIGHT}" y="72" text-anchor="end">{PLACE}</text>
  <text class="mono" x="{RIGHT}" y="100" text-anchor="end">{OPEN}</text>

  <line x1="{LEFT}" y1="214" x2="{RIGHT}" y2="214" stroke="{c['hairline']}" stroke-width="1"/>

  {heads}
  {row_labels}

  <path class="trace" d="{rounded_path(pts, CORNER)}" pathLength="1" fill="none" stroke="{c['teal']}" stroke-width="2" stroke-linejoin="round"/>
  {nodes}
</svg>
"""


for name in THEMES:
    (OUT / f"header-{name}.svg").write_text(build(name), encoding="utf-8")
    print("wrote", OUT / f"header-{name}.svg")
