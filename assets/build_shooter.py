"""Build the bug-hunt SVGs (light + dark): a boss fight that plays itself.

One boss, the production bug, drifts across the top. The ship follows it and
fires one skill per shot; each hit knocks a segment off the boss's HP bar
until it blows up. A README can't run scripts, so every move, shot and hit
is a keyframe at a fixed time in one loop. Clicking the image in the README
opens the playable version in play/.

Run:  uv run --with fonttools --with brotli python assets/build_shooter.py <fonts-dir>
"""

import base64
import io
import random
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont

OUT = Path(__file__).parent
FONTS = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT

THEMES = {
    "light": dict(ink="#15171c", graphite="#5e6370", hairline="#dde0e5", teal="#0a6b66", bg="#ffffff"),
    "dark": dict(ink="#e6e8eb", graphite="#9aa1ad", hairline="#30363d", teal="#3fb8ad", bg="#0d1117"),
}

W, H = 1200, 380
LEFT, RIGHT, TOP, BOTTOM = 48, 1152, 10, 370

BOSS = [
    ["....XX....XX....", ".....XX..XX.....", "....XXXXXXXX....", "...XXXXXXXXXX...", "..XXX.XXXX.XXX..",
     ".XXXXXXXXXXXXXX.", "XXXXXXXXXXXXXXXX", "XX.XXXXXXXXXX.XX", "XX.XX......XX.XX", "...XXX....XXX..."],
    ["....XX....XX....", ".....XX..XX.....", "....XXXXXXXX....", "...XXXXXXXXXX...", "..XXX.XXXX.XXX..",
     ".XXXXXXXXXXXXXX.", "XXXXXXXXXXXXXXXX", "XX.XXXXXXXXXX.XX", "...XX......XX...", ".XXX........XXX."],
]
BP = 7                                   # boss pixel size
BOSS_W, BOSS_H = 16 * BP, 10 * BP
BOSS_TOP = 78
SHIP = [".....X.....", "....XXX....", "....XXX....", ".XXXXXXXXX.", "XXXXXXXXXXX", "XXXXXXXXXXX"]
SP = 4                                   # ship pixel size
SHIP_TOP = 312

SKILLS = ["TypeScript", "React", "Next.js", "Node.js", "NestJS", "Python",
          "FastAPI", "PostgreSQL", "Redis", "Docker", "AWS", "LangGraph"]
N = len(SKILLS)
CENTER = 600

STEP, MOVE, FIRE, FLIGHT, BOOM = 0.8, 0.35, 0.4, 0.3, 0.35  # seconds
T = N * STEP + 2.2                       # loop: every shot, then the win screen
RESPAWN = T - 0.4
PILL_H = 24
PILL_TOP0 = SHIP_TOP - PILL_H - 6        # where a shot starts
PILL_TOP1 = BOSS_TOP + BOSS_H - 10       # where it meets the boss

rnd = random.Random(11)
BOSS_X = [round(rnd.uniform(LEFT + 160, RIGHT - 160)) for _ in range(N)]  # boss centre at each shot


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


def pixels(pattern, p, x0=0, y0=0):
    return "".join(
        f"M{x0 + c * p} {y0 + r * p}h{p}v{p}h-{p}z"
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


def glide(name, xs, end_hold):
    """translateX keyframes that move to xs[k] at the start of step k, then home."""
    frames, prev = ["0% { transform: translateX(0); }"], 0
    for k, x in enumerate(xs):
        dx = x - CENTER
        frames.append(f"{pct(k * STEP)} {{ transform: translateX({prev}px); }}")
        frames.append(f"{pct(k * STEP + MOVE)} {{ transform: translateX({dx}px); }}")
        prev = dx
    frames.append(f"{pct(end_hold)} {{ transform: translateX({prev}px); }}")
    frames.append("100% { transform: translateX(0); }")
    return f"@keyframes {name} {{ {' '.join(frames)} }}"


def hit_time(k):
    return k * STEP + FIRE + FLIGHT


def build(theme):
    c = THEMES[theme]
    hud_text = "bug hunt boss: production bug hp production bug fixed. shipping it."
    faces = font_face("PlexMono", "plex-mono-400.woff2", "".join(SKILLS) + hud_text)
    hits = [hit_time(k) for k in range(N)]
    last = hits[-1]

    css, body = [], []

    # stars
    stars = []
    srnd = random.Random(3)
    for i in range(46):
        x, y = srnd.uniform(LEFT + 10, RIGHT - 10), srnd.uniform(TOP + 50, BOTTOM - 10)
        tw = f' class="tw" style="animation-delay:{-srnd.uniform(0, 3):.2f}s"' if i % 4 == 0 else ""
        stars.append(f'<circle{tw} cx="{x:.0f}" cy="{y:.0f}" r="1.2" fill="{c["graphite"]}" opacity=".45"/>')
    body.append("".join(stars))

    # boss: glides with the ship, flashes teal on every hit, blows up on the last
    css.append(glide("boss", BOSS_X, T - 0.6))
    css.append(steps("bossalive", [(0, last), (RESPAWN, T)]))
    flashes = " ".join(
        f"{pct(h - .01)} {{ opacity: 0; }} {pct(h)} {{ opacity: 1; }} {pct(h + .12)} {{ opacity: 0; }}" for h in hits
    )
    css.append(f"@keyframes flash {{ 0% {{ opacity: 0; }} {flashes} 100% {{ opacity: 0; }} }}")
    bx, by = CENTER - BOSS_W // 2, BOSS_TOP
    body.append(
        f'<g class="boss"><g style="animation:bossalive {T}s linear infinite">'
        f'<path class="fa" d="{pixels(BOSS[0], BP, bx, by)}" fill="{c["graphite"]}"/>'
        f'<path class="fb" d="{pixels(BOSS[1], BP, bx, by)}" fill="{c["graphite"]}"/>'
        f'<path d="{pixels(BOSS[0], BP, bx, by)}" fill="{c["teal"]}" opacity="0" '
        f'style="animation:flash {T}s linear infinite"/></g></g>'
    )

    # shots: one skill each, flying straight up from wherever the ship is
    for k, (skill, x) in enumerate(zip(SKILLS, BOSS_X)):
        f, h = k * STEP + FIRE, hits[k]
        w = len(skill) * 8 + 20
        d = PILL_TOP0 - PILL_TOP1
        css.append(
            f"@keyframes shot{k} {{ 0%, {pct(f - .01)} {{ opacity: 0; transform: translateY(0); }} "
            f"{pct(f)} {{ opacity: 1; transform: translateY(0); }} "
            f"{pct(h)} {{ opacity: 1; transform: translateY(-{d}px); }} "
            f"{pct(h + .01)}, 100% {{ opacity: 0; transform: translateY(-{d}px); }} }}"
        )
        body.append(
            f'<g opacity="0" style="animation:shot{k} {T}s cubic-bezier(.3,0,.8,1) infinite">'
            f'<rect x="{x - w / 2:g}" y="{PILL_TOP0}" width="{w}" height="{PILL_H}" rx="{PILL_H // 2}" fill="{c["teal"]}"/>'
            f'<text class="pill" x="{x}" y="{PILL_TOP0 + 16.5}" text-anchor="middle">{escape(skill)}</text></g>'
        )
        big = k == N - 1
        css.append(
            f"@keyframes boom{k} {{ 0%, {pct(h - .01)} {{ opacity: 0; transform: scale(.3); }} "
            f"{pct(h)} {{ opacity: 1; transform: scale(.3); }} "
            f"{pct(h + (BOOM * 2 if big else BOOM))}, 100% {{ opacity: 0; transform: scale({3.2 if big else 1.4}); }} }}"
        )
        cy = BOSS_TOP + BOSS_H / 2 if big else PILL_TOP1 + 4
        body.append(f'<circle class="ring" cx="{x}" cy="{cy}" r="{40 if big else 16}" fill="none" stroke="{c["teal"]}" '
                    f'stroke-width="3" opacity="0" style="animation:boom{k} {T}s ease-out infinite"/>')

    # ship
    css.append(glide("ship", BOSS_X, N * STEP + 0.6))
    body.append(f'<g class="ship"><path d="{pixels(SHIP, SP, CENTER - 22, SHIP_TOP)}" fill="{c["teal"]}"/></g>')

    # HUD: name on the left, HP bar on the right that loses a segment per hit
    body.append(f'<text class="hud" x="{LEFT + 24}" y="44"><tspan fill="{c["teal"]}">bug hunt</tspan>'
                f'   boss: production bug</text>')
    seg_w, seg_gap = 18, 4
    bar_right = RIGHT - 24
    bar_left = bar_right - N * (seg_w + seg_gap) + seg_gap
    body.append(f'<text class="hud" x="{bar_left - 12}" y="44" text-anchor="end">hp</text>')
    for k in range(N):
        # segments drain from the right
        x = bar_right - (k + 1) * (seg_w + seg_gap) + seg_gap
        css.append(steps(f"hp{k}", [(0, hits[k]), (RESPAWN, T)]))
        body.append(f'<rect x="{x}" y="34" width="{seg_w}" height="10" rx="2" fill="{c["graphite"]}" '
                    f'stroke="{c["hairline"]}" stroke-width="0" style="animation:hp{k} {T}s linear infinite"/>')

    css.append(steps("win", [(last + .3, RESPAWN - .1)]))
    body.append(f'<text class="msg" x="{CENTER}" y="214" text-anchor="middle" opacity="0" '
                f'style="animation:win {T}s linear infinite">production bug fixed. shipping it.</text>')

    css_text = "\n    ".join(css)
    body_text = "\n  ".join(body)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">
  <title id="t">Bug hunt</title>
  <desc id="d">A boss fight that plays itself: a ship fires skills ({escape(', '.join(SKILLS))}) at the production bug until it is fixed.</desc>
  <style>
    {faces}
    .hud {{ font: 400 15px 'PlexMono', monospace; fill: {c['graphite']}; }}
    .pill {{ font: 400 13px 'PlexMono', monospace; fill: {c['bg']}; }}
    .msg {{ font: 400 22px 'PlexMono', monospace; fill: {c['teal']}; }}
    .boss {{ animation: boss {T}s ease-in-out infinite; }}
    .ship {{ animation: ship {T}s ease-in-out infinite; }}
    .ring {{ transform-box: fill-box; transform-origin: center; }}
    .fa {{ animation: fa .8s steps(1) infinite; }}
    .fb {{ animation: fb .8s steps(1) infinite; }}
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
  {body_text}
</svg>
"""


for name in THEMES:
    (OUT / f"bughunt-{name}.svg").write_text(build(name), encoding="utf-8")
    print("wrote", OUT / f"bughunt-{name}.svg")
