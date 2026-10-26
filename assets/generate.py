"""Regenerates the profile assets in this folder: python3 assets/generate.py

Wordmark geometry and brand colors come from the frontend-design skill (assets/brand/generate.py).
"""
import os

OUT = os.path.dirname(os.path.abspath(__file__))

ROSE, CREAM, INK = "#d78494", "#fdeff2", "#8e3a50"
SW = 22  # wordmark stroke width in logo units
FONT = "'Segoe UI', system-ui, -apple-system, BlinkMacSystemFont, Arial, sans-serif"

# (path, draw window in seconds)
STROKES = [
    ("M0,100 V50 A50,50 0 0 1 50,0 H58", (0.00, 0.45)),
    ("M156,0 A50,50 0 0 0 106,50 A50,50 0 0 0 156,100 A50,50 0 0 0 206,50 A50,50 0 0 0 156,0", (0.25, 0.75)),
    ("M304,0 A50,50 0 0 0 254,50 A50,50 0 0 0 304,100 A50,50 0 0 0 354,50 A50,50 0 0 0 304,0", (0.50, 1.00)),
    ("M354,-50 V100", (0.80, 1.10)),
    ("M406,0 V100", (0.95, 1.25)),
]
I_DOT, PERIOD = (406, -45, 13), (457, 97, 14)
BBOX = (-11, -61, 471, 111)
MARK_PERIOD, MARK_BBOX = (88, 97, 14), (-11, -11, 102, 111)

# Light values are the design system tokens; dark keeps the same roles on a warm dark surface.
THEMES = {
    "light": dict(surface="#ffffff", line="#eee4e9", text="#29242a", muted="#74616c",
                  tile="#fcecf0", icon="#a94460", arrow="#a88c9a"),
    "dark": dict(surface="#171216", line="#3a2c34", text="#f7ecf0", muted="#bba6b1",
                 tile="#3a2330", icon="#ec9aab", arrow="#7f6b76"),
}

# The final state is the base style and keyframes only run from the hidden state,
# so renderers without animation and prefers-reduced-motion get the full wordmark.
DRAW_CSS = """
.s{stroke-dasharray:1 2;animation:draw .5s cubic-bezier(.45,0,.25,1) both}
.i{transform-box:fill-box;transform-origin:center;animation:pop .3s 1.4s cubic-bezier(.3,1.6,.5,1) both}
.p{animation:drop .7s 1.6s cubic-bezier(.5,0,.5,1.4) both}
@keyframes draw{0%{stroke-dashoffset:1;opacity:0}1%{opacity:1}to{stroke-dashoffset:0}}
@keyframes pop{from{transform:scale(0)}}
@keyframes drop{0%{transform:translateY(-200px);opacity:0}1%{opacity:1}}
@media (prefers-reduced-motion:reduce){.s,.i,.p{animation:none}}
"""

ICONS = {
    "layers": '<path d="M12 3 3 7.5l9 4.5 9-4.5L12 3z"/><path d="m3 12 9 4.5 9-4.5"/><path d="m3 16.5 9 4.5 9-4.5"/>',
    "pencil": '<path d="M15.5 4.5l4 4L8 20H4v-4L15.5 4.5z"/><path d="m13 7 4 4"/>',
    "palette": '<path d="M12 3a9 9 0 1 0 0 18c1 0 1.6-.7 1.6-1.6 0-.5-.2-.9-.5-1.2-.3-.3-.5-.7-.5-1.2 '
               '0-.9.7-1.6 1.6-1.6H16a5 5 0 0 0 5-5c0-4-4-7.4-9-7.4z"/>'
               '<circle cx="7.5" cy="11.5" r=".6"/><circle cx="9.5" cy="7.5" r=".6"/><circle cx="14.5" cy="7.5" r=".6"/>',
    "route": '<circle cx="6" cy="18" r="2"/><circle cx="18" cy="6" r="2"/>'
             '<path d="M8 18h7.5a3.5 3.5 0 0 0 0-7h-7a3.5 3.5 0 0 1 0-7H16"/>',
}

CARDS = [
    ("skills", "agent skills", "layers",
     ["Plugin marketplace for my agent skills", "in Claude Code and Codex."]),
    ("sketchdraw", "TypeScript", "pencil",
     ["Hand-drawn diagrams from Mermaid", "and UI sketches from JSON."]),
    ("frontend-design", "design system", "palette",
     ["The light pink-plum design system", "this page is drawn in."]),
    ("proxyrun", "desktop app", "route",
     ["Free per-app proxy client for", "Windows and Linux/WSL."]),
]


def place(bbox, cx, cy, size, by_height=False):
    x0, y0, x1, y1 = bbox
    s = size / ((y1 - y0) if by_height else (x1 - x0))
    return f"translate({cx - (x0 + x1) / 2 * s:.2f},{cy - (y0 + y1) / 2 * s:.2f}) scale({s:.4f})"


def write(name, text):
    path = os.path.join(OUT, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text + "\n")


def banner(w=1280, h=400):
    strokes = "".join(f'<path class="s" d="{d}" pathLength="1" style="animation-delay:{a + .3:.2f}s;'
                      f'animation-duration:{b - a:.2f}s"/>' for d, (a, b) in STROKES)
    x, y, r = I_DOT
    px, py, pr = PERIOD
    logo = (f'<g fill="none" stroke="{CREAM}" stroke-width="{SW}" stroke-linecap="round" stroke-linejoin="round">'
            f'{strokes}<circle class="i" cx="{x}" cy="{y}" r="{r}" fill="{CREAM}" stroke="none"/>'
            f'<circle class="p" cx="{px}" cy="{py}" r="{pr}" fill="{INK}" stroke="none"/></g>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="rodi."><title>rodi.</title><style>{DRAW_CSS.strip()}</style>'
            f'<rect width="{w}" height="{h}" rx="24" fill="{ROSE}"/>'
            f'<g transform="{place(BBOX, w / 2, h / 2 + 4, 540)}">{logo}</g></svg>')


def card(name, kind, icon, lines, t, w=410, h=170):
    desc = "".join(f'<text x="24" y="{108 + i * 23}" font-size="15" fill="{t["muted"]}">{line}</text>'
                   for i, line in enumerate(lines))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="{name}: {" ".join(lines)}"><title>{name}</title>'
            f'<g font-family="{FONT}">'
            f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="20" fill="{t["surface"]}" stroke="{t["line"]}"/>'
            f'<rect x="24" y="24" width="44" height="44" rx="12" fill="{t["tile"]}"/>'
            f'<g transform="translate(34 34)" fill="none" stroke="{t["icon"]}" stroke-width="1.7" '
            f'stroke-linecap="round" stroke-linejoin="round">{ICONS[icon]}</g>'
            f'<text x="84" y="44" font-size="19" font-weight="600" fill="{t["text"]}">{name}</text>'
            f'<text x="84" y="63" font-size="13" fill="{t["muted"]}">{kind}</text>'
            f'<path d="M{w - 40} 40l10-10M{w - 38} 30h8v8" fill="none" stroke="{t["arrow"]}" stroke-width="1.7" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'
            f'{desc}</g></svg>')


def mark(text):
    x0, y0, x1, y1 = MARK_BBOX
    d = STROKES[0][0]
    x, y, r = MARK_PERIOD
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {x1 - x0} {y1 - y0}" role="img" aria-label="r.">'
            f'<path d="{d}" fill="none" stroke="{text}" stroke-width="{SW}" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="{ROSE}"/></svg>')


write("banner.svg", banner())
for theme, t in THEMES.items():
    for name, kind, icon, lines in CARDS:
        write(f"cards/{name}-{theme}.svg", card(name, kind, icon, lines, t))
    write(f"mark-{theme}.svg", mark(t["text"]))
