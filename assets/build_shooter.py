"""Build the bug-hunt SVGs (light + dark): a space shooter that plays itself.

A README can't run scripts, so the game is choreographed: every move, shot
and hit is a keyframe at a fixed time in one loop. Clicking the image in the
README opens the playable version in play/.

Run:  uv run --with fonttools --with brotli python assets/build_shooter.py <fonts-dir>
"""

import base64
import io
import random
import sys
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

OUT = Path(__file__).parent
FONTS = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT

THEMES = {
    "light": dict(ink="#15171c", graphite="#5e6370", hairline="#dde0e5", teal="#0a6b66"),
    "dark": dict(ink="#e6e8eb", graphite="#9aa1ad", hairline="#30363d", teal="#3fb8ad"),
}

W, H = 1200, 380
LEFT, RIGHT, TOP, BOTTOM = 48, 1152, 10, 370
P = 4  # pixel size of the sprites

BUG = [
    ["..X.....X..", "...X...X...", "..XXXXXXX..", ".XX.XXX.XX.",
     "XXXXXXXXXXX", "X.XXXXXXX.X", "X.X.....X.X", "...XX.XX..."],
    ["..X.....X..", "X..X...X..X", "X.XXXXXXX.X", "XXX.XXX.XXX",
     "XXXXXXXXXXX", ".XXXXXXXXX.", "..X.....X..", ".X.......X."],
]
SHIP = [".....X.....", "....XXX....", "....XXX....", ".XXXXXXXXX.", "XXXXXXXXXXX", "XXXXXXXXXXX"]
SPRITE_W, SPRITE_H = 11 * P, 8 * P

COLS_X = [300, 450, 600, 750, 900]           # column centres
ROWS_Y = [80, 170]                           # sprite tops: back row, front row
LABELS = [["timeout", "race", "deadlock", "OOM", "flaky test"],
          ["null", "N+1", "CORS", "leak", "500"]]
# (row, col) in firing order; each back-row bug dies after the front bug in its column
ORDER = [(1, 2), (1, 0), (0, 2), (1, 4), (1, 1), (0, 0), (0, 4), (1, 3), (0, 1), (0, 3)]

SHIP_TOP = 300
CENTER = 600
STEP, MOVE, FIRE, FLIGHT, BOOM = 0.9, 0.35, 0.4, 0.25, 0.35  # seconds
N = len(ORDER)
T = N * STEP + 1.6                           # loop length: all shots, then "all clear"
RESPAWN = T - 0.4


def font_face(family, file, text):
    """Subset a font to the glyphs in `text` and return an inline @font-face."""
    font = TTFont(FONTS / file)
    opts = subset.Options()
    opts.flavor = "woff"
    sub = subset.Subsetter(opts)
    sub.populate(text=text)
    sub.subset(font)
    font.flavor = "woff"
    buf = io.BytesIO()
    font.save(buf)
    data = base64.b64encode(buf.getvalue()).decode()
    return f"@font-face{{font-family:'{family}';src:url(data:font/woff;base64,{data}) format('woff');}}"


def pixels(pattern, x0=0, y0=0):
    return "".join(
        f"M{x0 + c * P} {y0 + r * P}h{P}v{P}h-{P}z"
        for r, row in enumerate(pattern) for c, ch in enumerate(row) if ch == "X"
    )


def pct(t):
    return f"{t / T * 100:.2f}%"


def steps(name, intervals):
    """Keyframes that show an element (opacity 1) only during the given intervals."""
    eps = 0.01
    frames = [f"0% {{ opacity: {1 if intervals[0][0] == 0 else 0}; }}"]
    for a, b in intervals:
        if a > 0:
            frames.append(f"{pct(a - eps)} {{ opacity: 0; }} {pct(a)} {{ opacity: 1; }}")
        if b < T:
            frames.append(f"{pct(b)} {{ opacity: 1; }} {pct(b + eps)} {{ opacity: 0; }}")
    frames.append(f"100% {{ opacity: {1 if intervals[-1][1] >= T else 0}; }}")
    return f"@keyframes {name} {{ {' '.join(frames)} }}"


def hit_time(k):
    return k * STEP + FIRE + FLIGHT


def build(theme):
    c = THEMES[theme]
    labels = "".join(l for row in LABELS for l in row)
    faces = font_face("PlexMono", "plex-mono-400.woff2", labels + "bug hunt fixed /0123456789 all clear. shipping it.")

    css, body = [], []

    # stars
    rnd = random.Random(3)
    stars = []
    for i in range(46):
        x, y = rnd.uniform(LEFT + 10, RIGHT - 10), rnd.uniform(TOP + 50, BOTTOM - 10)
        tw = f' class="tw" style="animation-delay:{-rnd.uniform(0, 3):.2f}s"' if i % 4 == 0 else ""
        stars.append(f'<circle{tw} cx="{x:.0f}" cy="{y:.0f}" r="1.2" fill="{c["graphite"]}" opacity=".45"/>')
    body.append("".join(stars))

    # bugs
    for k, (r, col) in enumerate(ORDER):
        x, y = COLS_X[col] - SPRITE_W // 2, ROWS_Y[r]
        h = hit_time(k)
        css.append(steps(f"bug{k}", [(0, h), (RESPAWN, T)]))
        body.append(
            f'<g style="animation:bug{k} {T}s linear infinite">'
            f'<path class="fa" d="{pixels(BUG[0], x, y)}" fill="{c["graphite"]}"/>'
            f'<path class="fb" d="{pixels(BUG[1], x, y)}" fill="{c["graphite"]}"/>'
            f'<text class="lbl" x="{COLS_X[col]}" y="{y + SPRITE_H + 20}" text-anchor="middle">{LABELS[r][col]}</text></g>'
        )

    # bullets and explosions
    for k, (r, col) in enumerate(ORDER):
        f, h = k * STEP + FIRE, hit_time(k)
        x, y0 = COLS_X[col] - 2, SHIP_TOP - 14
        d = y0 - (ROWS_Y[r] + SPRITE_H - 14)
        css.append(
            f"@keyframes shot{k} {{ 0%, {pct(f - .01)} {{ opacity: 0; transform: translateY(0); }} "
            f"{pct(f)} {{ opacity: 1; transform: translateY(0); }} "
            f"{pct(h)} {{ opacity: 1; transform: translateY(-{d}px); }} "
            f"{pct(h + .01)}, 100% {{ opacity: 0; transform: translateY(-{d}px); }} }}"
        )
        body.append(f'<rect x="{x}" y="{y0}" width="4" height="14" rx="1" fill="{c["teal"]}" opacity="0" '
                    f'style="animation:shot{k} {T}s linear infinite"/>')
        css.append(
            f"@keyframes boom{k} {{ 0%, {pct(h - .01)} {{ opacity: 0; transform: scale(.3); }} "
            f"{pct(h)} {{ opacity: 1; transform: scale(.3); }} "
            f"{pct(h + BOOM)}, 100% {{ opacity: 0; transform: scale(1.8); }} }}"
        )
        body.append(f'<circle class="boom" cx="{COLS_X[col]}" cy="{ROWS_Y[r] + SPRITE_H / 2}" r="22" fill="none" '
                    f'stroke="{c["teal"]}" stroke-width="3" opacity="0" style="animation:boom{k} {T}s ease-out infinite"/>')

    # ship: glide to each target, then back to centre for the next loop
    frames = [f"0% {{ transform: translateX(0); }}"]
    prev = 0
    for k, (_, col) in enumerate(ORDER):
        dx = COLS_X[col] - CENTER
        frames.append(f"{pct(k * STEP)} {{ transform: translateX({prev}px); }}")
        frames.append(f"{pct(k * STEP + MOVE)} {{ transform: translateX({dx}px); }}")
        prev = dx
    frames.append(f"{pct(N * STEP + .6)} {{ transform: translateX({prev}px); }}")
    frames.append("100% { transform: translateX(0); }")
    css.append(f"@keyframes ship {{ {' '.join(frames)} }}")
    body.append(f'<g class="ship"><path d="{pixels(SHIP, CENTER - 22, SHIP_TOP)}" fill="{c["teal"]}"/></g>')

    # score
    hits = [hit_time(k) for k in range(N)]
    for n in range(N + 1):
        start = 0 if n == 0 else hits[n - 1]
        end = hits[n] if n < N else RESPAWN
        spans = [(start, end)] + ([(RESPAWN, T)] if n == 0 else [])
        css.append(steps(f"score{n}", spans))
        body.append(f'<text class="hud" x="{RIGHT - 24}" y="44" text-anchor="end" opacity="{1 if n == 0 else 0}" '
                    f'style="animation:score{n} {T}s linear infinite">fixed {n}/{N}</text>')

    css.append(steps("clear", [(N * STEP + .2, RESPAWN - .1)]))
    body.append(f'<text class="msg" x="{CENTER}" y="250" text-anchor="middle" opacity="0" '
                f'style="animation:clear {T}s linear infinite">all clear. shipping it.</text>')

    css_text = "\n    ".join(css)
    body_text = "\n  ".join(body)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">
  <title id="t">Bug hunt</title>
  <desc id="d">A tiny space shooter that plays itself: a ship shoots down ten bugs labelled null, N+1, CORS, leak, 500, timeout, race, deadlock, OOM and flaky test.</desc>
  <style>
    {faces}
    .lbl {{ font: 400 14px 'PlexMono', monospace; fill: {c['graphite']}; }}
    .hud {{ font: 400 15px 'PlexMono', monospace; fill: {c['graphite']}; }}
    .msg {{ font: 400 22px 'PlexMono', monospace; fill: {c['teal']}; }}
    .ship {{ animation: ship {T}s ease-in-out infinite; }}
    .boom {{ transform-box: fill-box; transform-origin: center; }}
    .fa {{ animation: fa 1s steps(1) infinite; }}
    .fb {{ animation: fb 1s steps(1) infinite; }}
    .tw {{ animation: tw 3s ease-in-out infinite; }}
    @keyframes fa {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0; }} }}
    @keyframes fb {{ 0% {{ opacity: 0; }} 50% {{ opacity: 1; }} }}
    @keyframes tw {{ 0%,100% {{ opacity: .45; }} 50% {{ opacity: .05; }} }}
    {css_text}
    @media (prefers-reduced-motion: reduce) {{
      * {{ animation: none !important; }}
      .fb {{ opacity: 0; }}
    }}
  </style>

  <rect x="{LEFT}" y="{TOP}" width="{RIGHT - LEFT}" height="{BOTTOM - TOP}" rx="12" fill="none" stroke="{c['hairline']}"/>
  <text class="hud" x="{LEFT + 24}" y="44"><tspan fill="{c['teal']}">bug hunt</tspan></text>
  {body_text}
</svg>
"""


for name in THEMES:
    (OUT / f"bughunt-{name}.svg").write_text(build(name), encoding="utf-8")
    print("wrote", OUT / f"bughunt-{name}.svg")
