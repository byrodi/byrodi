"""Regenerates the profile: python3 assets/generate.py

Reads public repositories and contributions from the GitHub API, redraws the banner, the project
cards and the activity chart in this folder, and rewrites the marked sections of README.md.
.github/workflows/profile.yml runs it on a schedule. The token comes from GH_TOKEN, or from
`gh auth token` on a local machine.

Wordmark geometry and brand colors come from the frontend-design skill (assets/brand/generate.py).
"""
import datetime, html, json, os, re, subprocess, urllib.request

OUT = os.path.dirname(os.path.abspath(__file__))
README = os.path.join(OUT, "..", "README.md")
LOGIN = os.environ.get("GITHUB_REPOSITORY_OWNER", "byrodi")

LATEST = 6  # project cards, newest push first
DAYS = 30  # window of the activity chart
# Lists under "More". A repository goes to the last group whose topic it has.
GROUPS = [
    ("Products", {"saas", "desktop-app"}),
    ("Agent skills", {"agent-skills", "agent-skill"}),
    ("Code style", {"code-style"}),
    ("Wynncraft", {"wynncraft", "minecraft"}),
]
OTHER, FORKS = "Other projects", "Forks"

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

ICONS = {
    "layers": '<path d="M12 3 3 7.5l9 4.5 9-4.5L12 3z"/><path d="m3 12 9 4.5 9-4.5"/><path d="m3 16.5 9 4.5 9-4.5"/>',
    "pencil": '<path d="M15.5 4.5l4 4L8 20H4v-4L15.5 4.5z"/><path d="m13 7 4 4"/>',
    "palette": '<path d="M12 3a9 9 0 1 0 0 18c1 0 1.6-.7 1.6-1.6 0-.5-.2-.9-.5-1.2-.3-.3-.5-.7-.5-1.2 '
               '0-.9.7-1.6 1.6-1.6H16a5 5 0 0 0 5-5c0-4-4-7.4-9-7.4z"/>'
               '<circle cx="7.5" cy="11.5" r=".6"/><circle cx="9.5" cy="7.5" r=".6"/><circle cx="14.5" cy="7.5" r=".6"/>',
    "route": '<circle cx="6" cy="18" r="2"/><circle cx="18" cy="6" r="2"/>'
             '<path d="M8 18h7.5a3.5 3.5 0 0 0 0-7h-7a3.5 3.5 0 0 1 0-7H16"/>',
    "calendar": '<rect x="4" y="5" width="16" height="15" rx="2.5"/><path d="M4 10h16M8.5 3v4M15.5 3v4"/>',
    "cube": '<path d="M12 3 4 7.5v9l8 4.5 8-4.5v-9L12 3z"/><path d="m4 7.5 8 4.5 8-4.5"/><path d="M12 12v9"/>',
    "play": '<circle cx="12" cy="12" r="9"/><path d="M10 8.5v7l5.5-3.5L10 8.5z"/>',
    "code": '<path d="m8 7-5 5 5 5"/><path d="m16 7 5 5-5 5"/>',
}
# The first topic a repository has picks its icon; "code" is the fallback.
ICON_BY_TOPIC = [
    ("design-system", "palette"), ("diagrams", "pencil"), ("proxy", "route"), ("booking", "calendar"),
    ("minecraft", "cube"), ("browser-game", "play"), ("feed", "play"),
    ("agent-skills", "layers"), ("agent-skill", "layers"),
]

QUERY = """
query($login: String!, $from: DateTime!) {
  user(login: $login) {
    repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC,
                 orderBy: {field: PUSHED_AT, direction: DESC}) {
      nodes {
        name url description isFork isArchived stargazerCount pushedAt
        primaryLanguage { name }
        repositoryTopics(first: 20) { nodes { topic { name } } }
      }
    }
    contributionsCollection(from: $from) {
      commitContributionsByRepository(maxRepositories: 25) {
        repository { name isPrivate }
        contributions { totalCount }
      }
      contributionCalendar { weeks { contributionDays { date contributionCount } } }
    }
  }
}
"""


def fetch(today):
    token = os.environ.get("GH_TOKEN") or subprocess.run(
        ["gh", "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()
    start = today - datetime.timedelta(days=DAYS - 1)
    body = json.dumps({"query": QUERY, "variables": {"login": LOGIN, "from": f"{start}T00:00:00Z"}})
    request = urllib.request.Request("https://api.github.com/graphql", body.encode(),
                                     {"Authorization": f"bearer {token}", "User-Agent": LOGIN})
    with urllib.request.urlopen(request) as response:
        answer = json.load(response)
    if "errors" in answer:
        raise SystemExit(f"GitHub API: {answer['errors']}")
    return answer["data"]["user"]


def place(bbox, cx, cy, size, by_height=False):
    x0, y0, x1, y1 = bbox
    s = size / ((y1 - y0) if by_height else (x1 - x0))
    return f"translate({cx - (x0 + x1) / 2 * s:.2f},{cy - (y0 + y1) / 2 * s:.2f}) scale({s:.4f})"


def write(name, text):
    path = os.path.join(OUT, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text + "\n")


# Banner: the wordmark is written, rests, then erases itself, in a loop.

LOOP, REST = 5.0, 2.2  # loop length; the moment of the logo timeline shown at 0%
IN_OUT = "cubic-bezier(.42,0,.58,1)"
FALL, RISE = "cubic-bezier(.33,0,.67,.33)", "cubic-bezier(.33,.67,.67,1)"


def keyframes(name, frames):
    """frames: (second on the logo timeline, css, easing towards the next frame or None).

    0% and 100% are left out on purpose: there the element keeps its base style, the finished
    logo. Renderers without animation and prefers-reduced-motion get that same picture.
    """
    rows = sorted(((u - REST) % LOOP / LOOP * 100, css, ease) for u, css, ease in frames)
    return f"@keyframes {name}{{" + "".join(
        f"{p:.2f}%{{{css}{f';animation-timing-function:{ease}' if ease else ''}}}" for p, css, ease in rows) + "}"


def banner_css():
    css = [f".a{{animation:{LOOP}s linear infinite}}",
           ".s{stroke-dasharray:1 2}",
           ".d{transform-box:fill-box;transform-origin:center}"]
    hidden = "stroke-dashoffset:{};opacity:0"
    for i, (_, (a, b)) in enumerate(STROKES):
        e = 4.0 + 0.06 * (len(STROKES) - 1 - i)  # the last letter is erased first
        css.append(f".s{i}{{animation-name:s{i}}}")
        css.append(keyframes(f"s{i}", [
            (e, "stroke-dashoffset:0;opacity:1", IN_OUT),
            (e + 0.4, "stroke-dashoffset:-1;opacity:1", None),
            (e + 0.42, hidden.format(-1), None),
            (4.99, hidden.format(-1), None),
            (5.0, hidden.format(1), None),
            (a, hidden.format(1), None),
            (a + 0.02, "stroke-dashoffset:1;opacity:1", IN_OUT),
            (b, "stroke-dashoffset:0;opacity:1", None),
        ]))
    css.append(".i{animation-name:i}")
    css.append(keyframes("i", [
        (3.9, "transform:scale(1)", IN_OUT), (4.2, "transform:scale(0)", None),
        (1.15, "transform:scale(0)", "cubic-bezier(.3,1.6,.5,1)"), (1.45, "transform:scale(1)", None),
    ]))

    def period(dy=0, scale=1, opacity=1):
        return f"transform:translateY({dy}px) scale({scale});opacity:{opacity}"

    # The period drops in, lands on the baseline and hops three times, each hop lower.
    hops = [(0, -200, FALL), (.364, 0, RISE), (.545, -50, FALL), (.727, 0, RISE), (.818, -12.5, FALL),
            (.909, 0, RISE), (.955, -3, FALL), (1, 0, None)]
    css.append(".p{animation-name:p}")
    css.append(keyframes("p", [
        (2.8, period(), "ease-out"), (2.975, period(scale=1.35), "ease-in"), (3.15, period(), None),
        (3.2, period(), "ease-out"), (3.325, period(scale=1.15), "ease-in"), (3.45, period(), None),
        (4.35, period(), IN_OUT), (4.6, period(scale=0), None), (4.62, period(scale=0, opacity=0), None),
        (1.33, period(dy=-200, opacity=0), None),
    ] + [(1.35 + 0.7 * k, period(dy=dy), ease) for k, dy, ease in hops]))
    css.append("@media (prefers-reduced-motion:reduce){.a{animation:none}}")
    return "".join(css)


def banner(w=1360, h=480, radius=34):
    strokes = "".join(f'<path class="a s s{i}" d="{d}" pathLength="1"/>' for i, (d, _) in enumerate(STROKES))
    x, y, r = I_DOT
    px, py, pr = PERIOD
    logo = (f'<g fill="none" stroke="{CREAM}" stroke-width="{SW}" stroke-linecap="round" stroke-linejoin="round">'
            f'{strokes}<circle class="a d i" cx="{x}" cy="{y}" r="{r}" fill="{CREAM}" stroke="none"/>'
            f'<circle class="a d p" cx="{px}" cy="{py}" r="{pr}" fill="{INK}" stroke="none"/></g>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="rodi."><title>rodi.</title><style>{banner_css()}</style>'
            f'<rect width="{w}" height="{h}" rx="{radius}" fill="{ROSE}"/>'
            f'<g transform="{place(BBOX, w / 2, h / 2, 540)}">{logo}</g></svg>')


def mark(text):
    x0, y0, x1, y1 = MARK_BBOX
    d = STROKES[0][0]
    x, y, r = MARK_PERIOD
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {x1 - x0} {y1 - y0}" role="img" aria-label="r.">'
            f'<path d="{d}" fill="none" stroke="{text}" stroke-width="{SW}" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="{ROSE}"/></svg>')


# Text: an SVG inside <img> cannot wrap lines, so widths are estimated per character.

def text_width(text, size):
    def em(c):
        if c in "iljI.,:;'|! ": return 0.28
        if c in "ftr-()/": return 0.38
        if c in "mwMW": return 0.84
        return 0.66 if c.isupper() else 0.54
    return sum(em(c) for c in text) * size


def clip(text, size, width):
    if text_width(text, size) <= width:
        return text
    while text and text_width(text + "…", size) > width:
        text = text[:-1]
    return text.rstrip(" ,.;:-") + "…"


def wrap(text, size, width, max_lines):
    lines = [""]
    for word in text.split():
        candidate = f"{lines[-1]} {word}".strip()
        if text_width(candidate, size) <= width or not lines[-1]:
            lines[-1] = candidate
        else:
            lines.append(word)
    if len(lines) > max_lines:
        lines = lines[:max_lines - 1] + [clip(" ".join(lines[max_lines - 1:]), size, width)]
    return lines


def short_date(day):
    return f"{day:%b} {day.day}"


def svg(w, h, label, title, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="{html.escape(label)}"><title>{html.escape(title)}</title>'
            f'<g font-family="{FONT}">{body}</g></svg>')


def plate(w, h, t):
    return f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="20" fill="{t["surface"]}" stroke="{t["line"]}"/>'


def topics(repo):
    return [node["topic"]["name"] for node in repo["repositoryTopics"]["nodes"]]


def card(repo, t, w=410, h=206):
    name, description = repo["name"], repo["description"] or ""
    tags = topics(repo)
    icon = next((icon for topic, icon in ICON_BY_TOPIC if topic in tags), "code")
    kind = (repo["primaryLanguage"] or {}).get("name") or (tags[0].replace("-", " ") if tags else "repository")
    pushed = datetime.date.fromisoformat(repo["pushedAt"][:10])
    desc = "".join(f'<text x="24" y="{104 + i * 22}" font-size="15" fill="{t["muted"]}">{html.escape(line)}</text>'
                   for i, line in enumerate(wrap(description, 15, w - 52, 3)))
    stars = (f'<text x="{w - 24}" y="{h - 20}" font-size="12.5" text-anchor="end" fill="{t["muted"]}">'
             f'★ {repo["stargazerCount"]}</text>') if repo["stargazerCount"] else ""
    return svg(w, h, f"{name}: {description}", name,
               f'{plate(w, h, t)}'
               f'<rect x="24" y="24" width="44" height="44" rx="12" fill="{t["tile"]}"/>'
               f'<g transform="translate(34 34)" fill="none" stroke="{t["icon"]}" stroke-width="1.7" '
               f'stroke-linecap="round" stroke-linejoin="round">{ICONS[icon]}</g>'
               f'<text x="84" y="44" font-size="19" font-weight="600" fill="{t["text"]}">'
               f'{html.escape(clip(name, 19, w - 140))}</text>'
               f'<text x="84" y="63" font-size="13" fill="{t["muted"]}">{html.escape(kind)}</text>'
               f'<path d="M{w - 40} 40l10-10M{w - 38} 30h8v8" fill="none" stroke="{t["arrow"]}" stroke-width="1.7" '
               f'stroke-linecap="round" stroke-linejoin="round"/>'
               f'{desc}'
               f'<text x="24" y="{h - 20}" font-size="12.5" fill="{t["muted"]}">Updated {short_date(pushed)}</text>'
               f'{stars}')


def activity(days, commits, t, w=836, h=232):
    """days: (date, contributions) for the window; commits: (repository, commits), biggest first."""
    total = sum(count for _, count in days)
    label = f"{total} contributions in the last {len(days)} days"
    out = [plate(w, h, t),
           f'<text x="24" y="40" font-size="13" fill="{t["muted"]}">Contributions, last {len(days)} days</text>',
           f'<text x="24" y="82" font-size="34" font-weight="600" fill="{t["text"]}">{total}</text>']

    # One bar per day, anchored to the baseline. A day without contributions keeps a stub.
    x0, x1, base, top = 24, 392, 184, 108
    gap = 3
    bar = (x1 - x0 - gap * (len(days) - 1)) / len(days)
    peak = max(max(count for _, count in days), 1)
    for i, (_, count) in enumerate(days):
        x = x0 + i * (bar + gap)
        if count:
            height = max(4, (base - top) * count / peak)
            out.append(f'<rect x="{x:.1f}" y="{base - height:.1f}" width="{bar:.1f}" height="{height:.1f}" '
                       f'rx="{min(3, bar / 2):.1f}" fill="{ROSE}"/>')
        else:
            out.append(f'<rect x="{x:.1f}" y="{base - 2}" width="{bar:.1f}" height="2" rx="1" fill="{t["line"]}"/>')
    out.append(f'<text x="{x0}" y="{base + 24}" font-size="12.5" fill="{t["muted"]}">{short_date(days[0][0])}</text>')
    out.append(f'<text x="{x1}" y="{base + 24}" font-size="12.5" text-anchor="end" fill="{t["muted"]}">'
               f'{short_date(days[-1][0])}</text>')

    # Commits by repository: name, bar, value.
    left, bar0, bar1, right = 444, 640, 768, w - 24
    out.append(f'<text x="{left}" y="40" font-size="13" fill="{t["muted"]}">Commits by repository</text>')
    if not commits:
        out.append(f'<text x="{left}" y="82" font-size="15" fill="{t["muted"]}">A quiet month so far.</text>')
    most = max((count for _, count in commits), default=1)
    for i, (name, count) in enumerate(commits[:5]):
        y = 78 + i * 31
        width = max(8, (bar1 - bar0) * count / most)
        out.append(f'<text x="{left}" y="{y}" font-size="15" fill="{t["text"]}">'
                   f'{html.escape(clip(name, 15, bar0 - left - 16))}</text>'
                   f'<rect x="{bar0}" y="{y - 10}" width="{width:.1f}" height="8" rx="4" fill="{ROSE}"/>'
                   f'<text x="{right}" y="{y}" font-size="15" text-anchor="end" fill="{t["text"]}">{count}</text>')
    return svg(w, h, label, label, "".join(out))


def themed(path, alt, attrs):
    return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="./assets/{path}-dark.svg">'
            f'<img src="./assets/{path}-light.svg" alt="{html.escape(alt)}" {attrs}></picture>')


def link(repo):
    return f'[{repo["name"]}]({repo["url"]})'


def more(repos):
    """Markdown lists of the repositories that have no card."""
    grouped = {}
    for repo in repos:
        tags = set(topics(repo))
        group = FORKS if repo["isFork"] else next(
            (name for name, wanted in reversed(GROUPS) if tags & wanted), OTHER)
        grouped.setdefault(group, []).append(repo)
    order = [name for name, _ in GROUPS] + [OTHER, FORKS]
    return "\n".join(f"- {name}: {', '.join(link(repo) for repo in grouped[name])}"
                     for name in order if name in grouped)


def fill(text, section, body):
    pattern = rf"(<!-- {section}:start -->).*?(<!-- {section}:end -->)"
    if not re.search(pattern, text, flags=re.S):
        raise SystemExit(f"README.md has no {section} markers")
    return re.sub(pattern, lambda m: f"{m[1]}\n{body}\n{m[2]}", text, flags=re.S)


def main():
    today = datetime.datetime.now(datetime.timezone.utc).date()
    user = fetch(today)

    repos = [r for r in user["repositories"]["nodes"] if not r["isArchived"] and r["name"] != LOGIN]
    latest = [r for r in repos if not r["isFork"] and r["description"]][:LATEST]
    rest = [r for r in repos if r not in latest]

    contributions = user["contributionsCollection"]
    counts = {day["date"]: day["contributionCount"]
              for week in contributions["contributionCalendar"]["weeks"] for day in week["contributionDays"]}
    window = [today - datetime.timedelta(days=DAYS - 1 - i) for i in range(DAYS)]
    days = [(day, counts.get(day.isoformat(), 0)) for day in window]
    commits = sorted(((c["repository"]["name"], c["contributions"]["totalCount"])
                      for c in contributions["commitContributionsByRepository"]
                      if not c["repository"]["isPrivate"] and c["repository"]["name"] != LOGIN),
                     key=lambda pair: -pair[1])

    write("rodi.svg", banner())
    for theme, t in THEMES.items():
        for repo in latest:
            write(f"cards/{repo['name']}-{theme}.svg", card(repo, t))
        write(f"activity-{theme}.svg", activity(days, commits, t))
        write(f"mark-{theme}.svg", mark(t["text"]))
    keep = {f"{repo['name']}-{theme}.svg" for repo in latest for theme in THEMES}
    for name in os.listdir(os.path.join(OUT, "cards")):
        if name not in keep:
            os.remove(os.path.join(OUT, "cards", name))

    cards = "\n".join(f'  <a href="{repo["url"]}">'
                      + themed(f"cards/{repo['name']}", f"{repo['name']}: {repo['description']}", 'width="49%"')
                      + "</a>" for repo in latest)
    with open(README) as fh:
        text = fh.read()
    text = fill(text, "latest", f"<p>\n{cards}\n</p>")
    text = fill(text, "more", more(rest))
    with open(README, "w") as fh:
        fh.write(text)


if __name__ == "__main__":
    main()
