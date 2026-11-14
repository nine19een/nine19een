#!/usr/bin/env python3
"""Build the profile images for github.com/nine19een.

Outputs (all in assets/):
  banner-{dark,light}.svg          the nine19een wordmark in characters
  card-{dark,light}.svg            terminal card: avatar left, details right
  card-{dark,light}-narrow.svg     same card stacked, for phones

Inputs (all in scripts/):
  banner-19.txt, banner-letters.txt   the wordmark, two layers on one grid
  avatar-dark.txt, avatar-light.txt   your ASCII avatar; dark = inverted export.
                                      If one is missing, its card shows an
                                      empty frame of the same size.
  CARD below                          the text on the right side of the card
  stats.json                          last known GitHub numbers

Stats come from the GitHub REST API (GITHUB_TOKEN is used if set). If the API
can't be reached, the numbers in stats.json are kept.

Standard library only, so the GitHub Action needs no installs.
"""
import base64, datetime, json, os, pathlib, urllib.request, zlib
from xml.sax.saxutils import escape

ROOT = pathlib.Path(__file__).resolve().parent.parent
HERE = ROOT / "scripts"
USER = "nine19een"

# ------------------------------------------------------------------ card text
# Each line is a list of (text, style). Styles: k key, t text, m muted, a accent.
def card_text(s):
    K = lambda key, val: [(key + ":", "k"), (" " + val, "t")]
    P = lambda name, val: [("  " + name + " ", "a"), ("." * (15 - len(name)) + " ", "m"), (val, "t")]
    return [
        [("nine19een", "a"), ("@", "m"), ("github", "a")],
        [("-" * 16, "m")],
        K("OS", "CS undergrad, class of 2029"),
        K("Host", "nine19een.com"),
        K("Uptime", "year 2 of 4"),
        K("Shell", "Codex, Claude"),
        K("Kernel", "C++ / algorithms"),
        K("Focus", "AI coding, coding agents, LLM apps"),
        K("Learning", "PyTorch, model training"),
        [],
        [("Projects:", "k")],
        P("campus-oj", "live, runs our team's exams"),
        P("canvascast", f"open source, {s['canvascast']} stars"),
        P("schedule", "live, ad-free timetable"),
        P("agent-harness", "loop 67.5% vs one-shot 31.25%"),
        [],
        K("Writing", "20+ posts on agents and AI coding"),
        K("Awards", "Lanqiao Cup national 3rd, Beijing 1st"),
        K("AFK", "football, piano, gym, badminton"),
        K("Contact", "nine19eenowo@gmail.com"),
        K("GitHub", f"{s['repos']} repos, {s['stars']} stars, {s['followers']} followers"),
    ]

# ------------------------------------------------------------------ live stats
def fetch(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": USER})
    if os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)

def load_stats():
    path = HERE / "stats.json"
    stats = json.loads(path.read_text())
    try:
        u = fetch(f"https://api.github.com/users/{USER}")
        repos = fetch(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner")
        new = {
            "repos": u["public_repos"],
            "followers": u["followers"],
            "stars": sum(r["stargazers_count"] for r in repos if not r["fork"]),
            "canvascast": next(r["stargazers_count"] for r in repos if r["name"] == "CanvasCast"),
        }
        if any(new[k] != stats.get(k) for k in new):   # only bump the date when a number moves
            stats = {**new, "updated": datetime.date.today().isoformat()}
            path.write_text(json.dumps(stats, indent=2) + "\n")
    except Exception as e:
        print(f"stats: kept cached values ({e})")
    return stats

# ------------------------------------------------------------------ look
THEMES = {
    "dark": dict(bg="#101015", line="#2A2533", t="#EFEDF4", m="#A6A2B0", k="#B28AEF", a="#D6B8FF",
                 p0="#9C6FE4", p1="#D6B8FF",            # the 19
                 l0="#A6A2B0", l1="#6F6A7A",            # wordmark letters, two tones
                 v0="#EFEDF4", v1="#A98BDB",            # avatar, top to bottom
                 slot="#3A3346", cur="#B28AEF"),
    "light": dict(bg="#FBFAFD", line="#E4DEEE", t="#1B1822", m="#6E6878", k="#7D52CC", a="#6A3FB8",
                  p0="#6A3FB8", p1="#A47BE8",
                  l0="#6E6878", l1="#A6A2B0",
                  v0="#2B2633", v1="#7D52CC",
                  slot="#CFC6DE", cur="#7D52CC"),
}
SWATCHES = ["#101015", "#1C1725", "#A6A2B0", "#EFEDF4", "#D6B8FF", "#B28AEF"]
ADV = 0.6                  # IBM Plex Mono advance width, in em
FS, LH = 16, 21            # card text
PAD = 36
AVATAR_SLOT = (124, 62)    # cols, rows of the empty frame when an avatar file is missing

def font_css():
    css = ""
    for w in (400, 600):
        b = base64.b64encode((HERE / "fonts" / f"plex-mono-{w}.woff2").read_bytes()).decode()
        css += f"@font-face{{font-family:P;font-weight:{w};src:url(data:font/woff2;base64,{b}) format('woff2')}}"
    return css

FAMILY = "font-family:P,'IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"

def text(x, y, segs, size=None):
    spans = "".join(f'<tspan class="{c}">{escape(t)}</tspan>' for t, c in segs)
    fs = f' style="font-size:{size:.2f}px"' if size else ""   # inline style: a CSS rule would beat an attribute
    return f'<text x="{x:.1f}" y="{y:.1f}"{fs} xml:space="preserve">{spans}</text>'

def grad(id_, x0, y0, x1, y1, c0, c1):
    return (f'<linearGradient id="{id_}" gradientUnits="userSpaceOnUse" x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}">'
            f'<stop offset="0" stop-color="{c0}"/><stop offset="1" stop-color="{c1}"/></linearGradient>')

def svg(W, H, title, style, defs, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-label="{escape(title)}">\n'
            f'<title>{escape(title)}</title>\n<style>{font_css()}text{{{FAMILY}}}{style}</style>\n'
            f'<defs>{defs}</defs>\n' + "\n".join(body) + "\n</svg>\n")

def read_art(name):
    p = HERE / name
    if not p.exists():
        return None
    lines = [l.rstrip() for l in p.read_text(encoding="utf-8").split("\n")]
    while lines and not lines[0].strip(): lines.pop(0)
    while lines and not lines[-1].strip(): lines.pop()
    cut = min(len(l) - len(l.lstrip()) for l in lines if l.strip())
    return [l[cut:] for l in lines]

# ------------------------------------------------------------------ banner
def banner(theme):
    c = THEMES[theme]
    l19 = (HERE / "banner-19.txt").read_text().rstrip("\n").split("\n")
    let = (HERE / "banner-letters.txt").read_text().rstrip("\n").split("\n")
    cols = max(map(len, l19 + let))
    size, lh = 12, 12 * 1.14
    cw = size * ADV
    W, H = cols * cw, len(let) * lh + size * 0.4
    body = []
    for i, (a, b) in enumerate(zip(l19, let)):
        y = (i + 1) * lh
        segs, row = [], ""
        # letters: two tones, picked per "19" pair so the texture looks scattered
        for x, ch in enumerate(b.ljust(cols)):
            tone = "l0" if zlib.crc32(f"{i}:{x // 2}".encode()) % 3 else "l1"
            segs.append((ch, tone))
        merged = []
        for t, cl in segs:
            if merged and merged[-1][1] == cl: merged[-1] = (merged[-1][0] + t, cl)
            else: merged.append((t, cl))
        body.append(text(0, y, merged))
        body.append(text(0, y, [(a, "p")]))
    x0 = min(len(r) - len(r.lstrip()) for r in l19 if r.strip()) * cw
    x1 = max(len(r) for r in l19) * cw
    style = (f".l0{{fill:{c['l0']}}}.l1{{fill:{c['l1']}}}.p{{fill:url(#g19);font-weight:600}}"
             f"text{{font-size:{size}px}}")
    return svg(W, H, "nine19een", style, grad("g19", x0, 0, x1, H, c["p0"], c["p1"]), body)

# ------------------------------------------------------------------ card
def card(theme, narrow, stats):
    c = THEMES[theme]
    art = read_art(f"avatar-{theme}.txt")
    a_cols, a_rows = (max(map(len, art)), len(art)) if art else AVATAR_SLOT
    info = card_text(stats)
    cw = FS * ADV
    info_w = max(sum(len(t) for t, _ in l) for l in info if l) * cw
    info_h = (len(info) + 2) * LH                      # details plus the swatch row
    top = PAD + FS                                     # prompt baseline
    y0 = top + LH * 2                                  # first output baseline
    body = [text(PAD, top, [("~ ", "k"), ("$ ", "m"), ("neofetch", "t")])]

    if narrow:   # avatar on top, sized to the text column's width
        afs = info_w / (a_cols * ADV)
        ax, ay = PAD, y0 - FS
        ix, iy = PAD, ay + a_rows * afs * 1.15 + LH * 2
        W = PAD * 2 + info_w
    else:        # avatar left, as tall as the details
        afs = info_h / (a_rows * 1.15)
        ax, ay = PAD, y0 - FS
        ix, iy = PAD + a_cols * afs * ADV + 48, y0
        W = ix + info_w + PAD
    alh = afs * 1.15
    aw, ah = a_cols * afs * ADV, a_rows * alh

    if art:
        for i, row in enumerate(art):
            body.append(text(ax, ay + afs + i * alh, [(row, "v")], afs))
    else:
        body.append(f'<rect x="{ax:.1f}" y="{ay:.1f}" width="{aw:.1f}" height="{ah:.1f}" rx="8" fill="none" '
                    f'stroke="{c["slot"]}" stroke-dasharray="6 6"/>')
        body.append(f'<text x="{ax + aw / 2:.1f}" y="{ay + ah / 2:.1f}" text-anchor="middle" class="m s">'
                    f'scripts/avatar-{theme}.txt</text>')
        body.append(f'<text x="{ax + aw / 2:.1f}" y="{ay + ah / 2 + 18:.1f}" text-anchor="middle" class="m s">'
                    f'{a_cols} x {a_rows}</text>')

    for i, l in enumerate(info):
        if l:
            body.append(text(ix, iy + i * LH, l))
    sy = iy + (len(info) + 1) * LH
    for j, col in enumerate(SWATCHES):
        body.append(f'<rect x="{ix + j * cw * 3:.1f}" y="{sy - FS + 4:.1f}" width="{cw * 3:.1f}" height="{LH - 4}" '
                    f'fill="{col}" stroke="{c["line"]}"/>')
    ey = max(sy, ay + ah) + LH * 2                     # closing prompt
    body.append(text(PAD, ey, [("~ ", "k"), ("$ ", "m")]))
    body.append(f'<rect class="cur" x="{PAD + cw * 4:.1f}" y="{ey - FS + 3:.1f}" width="{cw:.1f}" height="{FS + 2}" fill="{c["cur"]}"/>')
    body.append(f'<text x="{W - PAD:.1f}" y="{ey:.1f}" text-anchor="end" class="m s">updated {escape(stats["updated"])}</text>')
    H = ey + PAD
    body.insert(0, f'<rect x=".5" y=".5" width="{W - 1:.1f}" height="{H - 1:.1f}" rx="12" fill="{c["bg"]}" stroke="{c["line"]}"/>')
    style = (f"text{{font-size:{FS}px}}.k{{fill:{c['k']};font-weight:600}}.t{{fill:{c['t']}}}.m{{fill:{c['m']}}}"
             f".a{{fill:{c['a']};font-weight:600}}.v{{fill:url(#gv)}}.s{{font-size:12px}}"
             "@keyframes b{50%{opacity:0}}.cur{animation:b 1.1s steps(1) infinite}"
             "@media (prefers-reduced-motion:reduce){.cur{animation:none}}")
    title = "nine19een running neofetch: an ASCII avatar beside profile details"
    return svg(W, H, title, style, grad("gv", ax, ay, ax, ay + ah, c["v0"], c["v1"]), body)

if __name__ == "__main__":
    stats = load_stats()
    out = ROOT / "assets"
    out.mkdir(exist_ok=True)
    for theme in THEMES:
        (out / f"banner-{theme}.svg").write_text(banner(theme))
        for narrow in (False, True):
            (out / f"card-{theme}{'-narrow' if narrow else ''}.svg").write_text(card(theme, narrow, stats))
        if not (HERE / f"avatar-{theme}.txt").exists():
            print(f"note: scripts/avatar-{theme}.txt not found, card-{theme} shows an empty frame")
    print("wrote", ", ".join(sorted(p.name for p in out.glob("*.svg"))))
