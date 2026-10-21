"""Build the profile header SVGs (light + dark) from one set of tokens.

The header draws one conversational turn of a voice agent: the caller's
speech ends, a bracket measures the gap, the agent's reply begins.

Run:  uv run --with fonttools --with brotli python assets/build_header.py <fonts-dir>
"""

import base64
import io
import math
import random
import sys
from xml.sax.saxutils import escape
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

OUT = Path(__file__).parent
FONTS = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT

THEMES = {
    "light": dict(ink="#15171c", graphite="#5e6370", hairline="#dde0e5", teal="#0a6b66"),
    "dark": dict(ink="#e6e8eb", graphite="#9aa1ad", hairline="#30363d", teal="#3fb8ad"),
}

W, H = 1200, 430
LEFT, RIGHT = 48, 1152

NAME = "Sheikh Abu Jubayer"
ROLE = "Full-Stack & AI Engineer"
LINE = "I build real-time AI voice agents and the products around them."
PLACE = "Dhaka, Bangladesh · Remote"
NOW = "now at Verbacall"
GAP = "500–700 ms"
CAPTION = "one conversational turn: the caller stops, the agent answers"

# Turn geometry
CALLER = (150, 596)   # x range of caller speech
AGENT = (784, 1152)   # x range of agent speech
CALLER_Y, AGENT_Y = 300, 366
TRACE_TOP, TRACE_BOTTOM = 262, 396


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


def envelope(n, seed, syllables):
    """Speech-like bar heights: syllable bumps spread across the whole lane.

    The lane must stay voiced right up to its edges, so the gap bracket starts
    exactly where the caller stops and ends exactly where the agent starts.
    """
    rnd = random.Random(seed)
    spacing = 1 / syllables
    centers = [(k + 0.5) * spacing + rnd.uniform(-0.25, 0.25) * spacing for k in range(syllables)]
    widths = [rnd.uniform(0.3, 0.45) * spacing for _ in centers]
    out = []
    for i in range(n):
        t = i / (n - 1)
        level = sum(math.exp(-((t - c) ** 2) / w ** 2) for c, w in zip(centers, widths))
        level = min(1.0, level) * (0.6 + 0.4 * rnd.random())
        fade = min(1.0, t / 0.02 + 0.3, (1 - t) / 0.02 + 0.3)
        out.append(max(0.12, level * fade))
    return out


def bars(x0, x1, cy, seed, syllables, color, cls):
    step, width, max_h = 8, 4, 50
    n = (x1 - x0) // step + 1
    rects = []
    for i, level in enumerate(envelope(n, seed, syllables)):
        h = round(level * max_h, 1)
        x = x0 + i * step
        rects.append(
            f'<rect class="{cls}" x="{x}" y="{cy - h / 2:.1f}" width="{width}" height="{h}" rx="2" fill="{color}"/>'
        )
    return "\n    ".join(rects)


def build(theme):
    c = THEMES[theme]
    faces = "".join([
        font_face("Bricolage", "bricolage-700.woff2", NAME),
        font_face("PlexSans", "plex-sans-500.woff2", ROLE),
        font_face("PlexSansRegular", "plex-sans-400.woff2", LINE),
        font_face("PlexMono", "plex-mono-400.woff2", PLACE + NOW + GAP + CAPTION + "calleragent"),
    ])
    gap_l, gap_r = CALLER[1] + 6, AGENT[0] - 6
    gap_mid = (gap_l + gap_r) / 2
    sweep = AGENT[1] - CALLER[0]

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">
  <title id="t">{escape(NAME)}, {escape(ROLE)}</title>
  <desc id="d">One conversational turn of an AI voice agent: the caller stops speaking and the agent answers {GAP} later.</desc>
  <style>
    {faces}
    .name {{ font: 700 64px 'Bricolage', sans-serif; fill: {c['ink']}; }}
    .role {{ font: 500 26px 'PlexSans', sans-serif; fill: {c['teal']}; }}
    .line {{ font: 400 22px 'PlexSansRegular', sans-serif; fill: {c['graphite']}; }}
    .mono {{ font: 400 17px 'PlexMono', monospace; fill: {c['graphite']}; }}
    .gap {{ font: 400 19px 'PlexMono', monospace; fill: {c['teal']}; }}
    .live {{ animation: pulse 2.4s ease-in-out infinite; transform-origin: center; transform-box: fill-box; }}
    .head {{ animation: sweep 6s cubic-bezier(.45,0,.55,1) infinite; }}
    @keyframes pulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: .35; }} }}
    @keyframes sweep {{
      0% {{ transform: translateX(0); opacity: 0; }}
      6% {{ opacity: .9; }}
      80% {{ transform: translateX({sweep}px); opacity: .9; }}
      88%,100% {{ transform: translateX({sweep}px); opacity: 0; }}
    }}
    @media (prefers-reduced-motion: reduce) {{
      .live, .head {{ animation: none; }}
      .head {{ display: none; }}
    }}
  </style>

  <text class="name" x="{LEFT - 3}" y="100">{NAME}</text>
  <text class="role" x="{LEFT}" y="146">{escape(ROLE)}</text>
  <text class="line" x="{LEFT}" y="182">{LINE}</text>

  <text class="mono" x="{RIGHT}" y="72" text-anchor="end">{PLACE}</text>
  <circle class="live" cx="{RIGHT - len(NOW) * 10.2 - 14}" cy="95" r="5" fill="{c['teal']}"/>
  <text class="mono" x="{RIGHT}" y="100" text-anchor="end">{NOW}</text>

  <line x1="{LEFT}" y1="214" x2="{RIGHT}" y2="214" stroke="{c['hairline']}" stroke-width="1"/>

  <text class="mono" x="{LEFT}" y="{CALLER_Y + 5}">caller</text>
  <text class="mono" x="{LEFT}" y="{AGENT_Y + 5}">agent</text>

  <g>
    {bars(*CALLER, CALLER_Y, seed=7, syllables=7, color=c['graphite'], cls='c')}
  </g>
  <g>
    {bars(*AGENT, AGENT_Y, seed=21, syllables=6, color=c['teal'], cls='a')}
  </g>

  <line x1="{gap_l}" y1="{TRACE_TOP}" x2="{gap_l}" y2="{TRACE_BOTTOM}" stroke="{c['graphite']}" stroke-width="1" stroke-dasharray="3 4"/>
  <line x1="{gap_r}" y1="{TRACE_TOP}" x2="{gap_r}" y2="{TRACE_BOTTOM}" stroke="{c['graphite']}" stroke-width="1" stroke-dasharray="3 4"/>
  <path d="M{gap_l} {TRACE_TOP - 6} v-8 H{gap_r} v8" fill="none" stroke="{c['teal']}" stroke-width="2"/>
  <text class="gap" x="{gap_mid}" y="{TRACE_TOP - 24}" text-anchor="middle">{GAP}</text>

  <line class="head" x1="{CALLER[0]}" y1="{TRACE_TOP + 4}" x2="{CALLER[0]}" y2="{TRACE_BOTTOM - 4}" stroke="{c['teal']}" stroke-width="2"/>

  <line x1="{LEFT}" y1="{TRACE_BOTTOM + 8}" x2="{RIGHT}" y2="{TRACE_BOTTOM + 8}" stroke="{c['hairline']}" stroke-width="1"/>
  <text class="mono" x="{LEFT}" y="{TRACE_BOTTOM + 30}">{CAPTION}</text>
</svg>
"""


for name in THEMES:
    (OUT / f"header-{name}.svg").write_text(build(name), encoding="utf-8")
    print("wrote", OUT / f"header-{name}.svg")
