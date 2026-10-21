"""Build the profile header SVGs (light + dark) from one set of tokens.

The header draws the stack I work across as a system: four layers a request
passes through, sitting on the infra that runs them. One request hops from
layer to layer, and each layer's dot lights up as it arrives.

Run:  uv run --with fonttools --with brotli python assets/build_header.py <fonts-dir>
"""

import base64
import io
import sys
from xml.sax.saxutils import escape
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

OUT = Path(__file__).parent
FONTS = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT

# bg matches GitHub's page so panels hide the packets passing behind them
THEMES = {
    "light": dict(ink="#15171c", graphite="#5e6370", hairline="#dde0e5", teal="#0a6b66", bg="#ffffff"),
    "dark": dict(ink="#e6e8eb", graphite="#9aa1ad", hairline="#30363d", teal="#3fb8ad", bg="#0d1117"),
}

W, H = 1200, 548
LEFT, RIGHT = 48, 1152

NAME = "Sheikh Abu Jubayer"
ROLE = "Full-Stack & AI Engineer"
LINE = "I build whole products: the interface, the backend, the data and the AI inside them."
PLACE = "Dhaka, Bangladesh · Remote"
OPEN = "open to remote roles"

LAYERS = [
    ("interface", ["React", "Next.js", "React Native", "Tailwind CSS", "React Flow"]),
    ("backend", ["TypeScript", "Node.js · NestJS", "Python · FastAPI", "Express", "gRPC · WebSockets"]),
    ("data", ["PostgreSQL", "MongoDB", "Redis", "BullMQ", "Prisma · TypeORM"]),
    ("ai", ["LangGraph", "LangChain", "MCP servers", "RAG", "LLM evals · LangSmith"]),
]
INFRA = ["Docker", "AWS", "CI/CD", "Nginx", "OpenTelemetry"]

GAP = 40
PANEL_W = (RIGHT - LEFT - GAP * (len(LAYERS) - 1)) / len(LAYERS)
PANEL_TOP, PANEL_H = 240, 206
WIRE_Y = PANEL_TOP + 22          # packets travel at the height of the panel labels
BASE_TOP, BASE_H = 466, 50
STEP = 1.0                       # seconds per layer; a full cycle is one step per layer


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


def panel(i, label, skills, c):
    x = LEFT + i * (PANEL_W + GAP)
    rows = "".join(
        f'<text class="skill" x="{x + 20:g}" y="{PANEL_TOP + 66 + k * 30}">{escape(s)}</text>'
        for k, s in enumerate(skills)
    )
    return (
        f'<g><rect x="{x:g}" y="{PANEL_TOP}" width="{PANEL_W:g}" height="{PANEL_H}" rx="10" '
        f'fill="{c["bg"]}" stroke="{c["hairline"]}"/>'
        f'<circle class="hit" cx="{x + 24:g}" cy="{WIRE_Y}" r="4" fill="{c["teal"]}" '
        f'style="animation-delay:{i * STEP:g}s"/>'
        f'<text class="layer" x="{x + 36:g}" y="{WIRE_Y + 5}">{label}</text>'
        f'<line x1="{x + 20:g}" y1="{PANEL_TOP + 40}" x2="{x + PANEL_W - 20:g}" y2="{PANEL_TOP + 40}" '
        f'stroke="{c["hairline"]}"/>{rows}</g>'
    )


def build(theme):
    c = THEMES[theme]
    skills = "".join(s for _, ss in LAYERS for s in ss)
    mono = PLACE + OPEN + "".join(l for l, _ in LAYERS) + "runs on" + " · ".join(INFRA)
    faces = "".join([
        font_face("Bricolage", "bricolage-700.woff2", NAME),
        font_face("PlexSans", "plex-sans-500.woff2", ROLE),
        font_face("PlexSansRegular", "plex-sans-400.woff2", LINE + skills),
        font_face("PlexMono", "plex-mono-400.woff2", mono),
    ])

    # the packet for gap g leaves layer g just after its dot lights, landing as layer g+1 lights
    packets = "\n  ".join(
        f'<circle class="pkt" cx="{LEFT + (g + 1) * PANEL_W + g * GAP:g}" cy="{WIRE_Y}" r="4.5" '
        f'fill="{c["teal"]}" style="animation-delay:{g * STEP + 0.4 * STEP:g}s"/>'
        for g in range(len(LAYERS) - 1)
    )
    panels = "\n  ".join(panel(i, label, ss, c) for i, (label, ss) in enumerate(LAYERS))
    # the base sits under all four panels; a short stub joins each panel to it
    stubs = "".join(
        f'<line x1="{LEFT + i * (PANEL_W + GAP) + PANEL_W / 2:g}" y1="{PANEL_TOP + PANEL_H}" '
        f'x2="{LEFT + i * (PANEL_W + GAP) + PANEL_W / 2:g}" y2="{BASE_TOP}" stroke="{c["hairline"]}" '
        f'stroke-dasharray="2 4"/>'
        for i in range(len(LAYERS))
    )
    infra = " · ".join(INFRA)
    cycle = STEP * len(LAYERS)
    hop_end = round(0.6 * STEP / cycle * 100)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">
  <title id="t">{escape(NAME)}, {escape(ROLE)}</title>
  <desc id="d">The stack I work across, drawn as a system: interface, backend, data and AI layers on top of the infrastructure that runs them.</desc>
  <style>
    {faces}
    .name {{ font: 700 64px 'Bricolage', sans-serif; fill: {c['ink']}; }}
    .role {{ font: 500 26px 'PlexSans', sans-serif; fill: {c['teal']}; }}
    .line {{ font: 400 22px 'PlexSansRegular', sans-serif; fill: {c['graphite']}; }}
    .skill {{ font: 400 17px 'PlexSansRegular', sans-serif; fill: {c['ink']}; }}
    .layer {{ font: 400 16px 'PlexMono', monospace; fill: {c['teal']}; }}
    .mono {{ font: 400 15px 'PlexMono', monospace; fill: {c['graphite']}; }}
    .pkt {{ opacity: 0; animation: hop {cycle}s ease-in-out infinite; }}
    .hit {{ transform-box: fill-box; transform-origin: center; animation: hit {cycle}s ease-out infinite; }}
    .live {{ animation: pulse 2.4s ease-in-out infinite; }}
    @keyframes hop {{
      0% {{ transform: translateX(0); opacity: 0; }}
      3% {{ opacity: 1; }}
      {hop_end}% {{ transform: translateX({GAP}px); opacity: 1; }}
      {hop_end + 2}%,100% {{ transform: translateX({GAP}px); opacity: 0; }}
    }}
    @keyframes hit {{ 0%,12%,100% {{ transform: scale(1); }} 4% {{ transform: scale(1.9); }} }}
    @keyframes pulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: .3; }} }}
    @media (prefers-reduced-motion: reduce) {{
      .live, .hit {{ animation: none; }}
      .pkt {{ display: none; }}
    }}
  </style>

  <text class="name" x="{LEFT - 3}" y="100">{NAME}</text>
  <text class="role" x="{LEFT}" y="146">{escape(ROLE)}</text>
  <text class="line" x="{LEFT}" y="182">{LINE}</text>

  <text class="mono" x="{RIGHT}" y="72" text-anchor="end">{PLACE}</text>
  <circle class="live" cx="{RIGHT - len(OPEN) * 9 - 12}" cy="95" r="5" fill="{c['teal']}"/>
  <text class="mono" x="{RIGHT}" y="100" text-anchor="end">{OPEN}</text>

  <line x1="{LEFT}" y1="214" x2="{RIGHT}" y2="214" stroke="{c['hairline']}" stroke-width="1"/>

  <line x1="{LEFT}" y1="{WIRE_Y}" x2="{RIGHT}" y2="{WIRE_Y}" stroke="{c['teal']}" stroke-width="1.5" stroke-dasharray="3 5" opacity=".7"/>
  {packets}
  {stubs}
  {panels}

  <rect x="{LEFT}" y="{BASE_TOP}" width="{RIGHT - LEFT}" height="{BASE_H}" rx="10" fill="{c['bg']}" stroke="{c['hairline']}"/>
  <text class="mono" x="{LEFT + 20}" y="{BASE_TOP + BASE_H / 2 + 5:g}"><tspan fill="{c['teal']}">runs on</tspan>   {escape(infra)}</text>
</svg>
"""


for name in THEMES:
    (OUT / f"header-{name}.svg").write_text(build(name), encoding="utf-8")
    print("wrote", OUT / f"header-{name}.svg")
