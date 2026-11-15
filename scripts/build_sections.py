#!/usr/bin/env python3
"""Build the images below the neofetch card. Run after build_card.py.

Outputs (in assets/), one terminal panel per section, plus a stacked version for phones:
  session-{projects,experiments,writing}[-narrow].svg

Edit PROJECTS / EXPERIMENTS / WRITING below to change the text.
Type size and width follow the neofetch card, so everything lines up.
"""
import json, pathlib, re, sys, textwrap

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_card as bc

ROOT, HERE = bc.ROOT, bc.HERE
C = bc.THEMES["dark"]
FS, LH, PAD = bc.FS, bc.LH, bc.PAD
CW = FS * bc.ADV

# ------------------------------------------------------------------ content
def content(s):
    projects = [
        dict(slug="campus-oj", status="live · private source", url="oj.nine19een.com",
             copy="An OJ for my university's competitive programming team (~60), used in training and exams."),
        dict(slug="canvascast", status=f"open source · {s['canvascast']} stars", url="github.com/nine19een/CanvasCast",
             copy="A browser whiteboard for drawing and recording algorithm explanations, with video export.",
             note="Featured in Ruan Yifeng's Tech Weekly #398"),
        dict(slug="schedule", status="live · private source", url="schedule.nine19een.com",
             copy="A timetable app I made to avoid ads and clutter. I've used it for over half a semester."),
        dict(slug="arsenal-transfer-alert", status="public repo", url="github.com/nine19een/arsenal-transfer-alert",
             copy="A seasonal tool that filtered Arsenal transfer reports from X with DeepSeek and sent Bark alerts."),
    ]
    experiments = [
        dict(slug="agent-harness-lab", status="experiment", url="nine19een.com/writing",
             bars=[("agent loop", 67.5, "67.5%", "54/80", True), ("one-shot", 31.25, "31.25%", "25/80", False)],
             copy="20 SWE-bench Lite tasks, four independent runs each. One setup, not a model ranking."),
        dict(slug="video-to-handout", status="public repo", url="github.com/nine19een/video-to-handout",
             copy="A Codex-driven workflow for slide-aligned handouts, with checks at each step—after it missed half a lecture."),
    ]
    writing = dict(
        intro="Notes on building software, coding agents, experiments, and what breaks.",
        posts=[("2026-10-09", "Agent Harness Lab Follow-up Experiment Retrospective"),
               ("2026-09-22", "I Just Wanted a Clean IP for ChatGPT. Somehow I Ended Up Building a Proxy Chain."),
               ("2026-05-10", "AtCoder ABC457-E Review: Interval Unions, Structural Cases, and an Offline Fenwick Tree")])
    return projects, experiments, writing

# ------------------------------------------------------------------ drawing
# A row is a list of elements placed on a character grid:
#   ("t", col, segs)                 text starting at col
#   ("r", col, segs)                 text ending at col
#   ("bar", col0, col1, pct, main)   a drawn bar between two columns
#   ("cur", col)                     the blinking cursor
def seglen(segs): return sum(len(t) for t, _ in segs)

def draw(rows, W, title, pad_y=PAD):
    body = [f'<rect x=".5" y=".5" width="{W - 1:.1f}" height="{{H}}" rx="12" fill="{C["bg"]}" stroke="{C["line"]}"/>']
    y = pad_y + FS
    for row in rows:
        for el in row:
            if el[0] == "t":
                body.append(bc.text(PAD + el[1] * CW, y, el[2]))
            elif el[0] == "r":
                body.append(bc.text(PAD + (el[1] - seglen(el[2])) * CW, y, el[2]))
            elif el[0] == "bar":
                x0, x1 = PAD + el[1] * CW, PAD + el[2] * CW
                top = y - FS + 4
                body.append(f'<rect x="{x0:.1f}" y="{top:.1f}" width="{x1 - x0:.1f}" height="{FS - 2}" rx="2" fill="{C["line"]}"/>')
                body.append(f'<rect x="{x0:.1f}" y="{top:.1f}" width="{(x1 - x0) * el[3] / 100:.1f}" height="{FS - 2}" rx="2" '
                            f'fill="{C["k"] if el[4] else C["l1"]}"/>')
            elif el[0] == "cur":
                body.append(f'<rect class="cur" x="{PAD + el[1] * CW:.1f}" y="{y - FS + 3:.1f}" width="{CW:.1f}" height="{FS + 2}" fill="{C["cur"]}"/>')
        y += LH
    H = y - LH + (LH - FS) + pad_y
    body[0] = body[0].replace("{H}", f"{H - 1:.1f}")
    style = (f"text{{font-size:{FS}px}}.k{{fill:{C['k']};font-weight:600}}.t{{fill:{C['t']}}}.m{{fill:{C['m']}}}"
             f".a{{fill:{C['a']};font-weight:600}}"
             "@keyframes b{50%{opacity:0}}.cur{animation:b 1.1s steps(1) infinite}"
             "@media (prefers-reduced-motion:reduce){.cur{animation:none}}")
    return bc.svg(W, H, title, style, "", body)

def prompt(cmd): return [("t", 0, [("~ ", "k"), ("$ ", "m"), (cmd, "t")])]

def wrapped(s, width, col, cls="t"):
    return [[("t", col, [(line, cls)])] for line in textwrap.wrap(s, width)]

def bar_rows(bars, c0, c1):
    """label, bar, percentage and run count on one row; c0..c1 is the usable column range."""
    return [[("t", c0, [(label, "a" if main else "t")]), ("bar", c0 + 12, c1 - 17, pct, main),
             ("r", c1 - 8, [(ptxt, "t")]), ("r", c1, [(runs, "m")])]
            for label, pct, ptxt, runs, main in bars]

# ------------------------------------------------------------------ panels
def entry(e, cols):
    head = [("t", 0, [(e["slug"], "a"), ("  " + e["status"], "m")])]
    if len(e["slug"]) + 2 + len(e["status"]) + 3 + len(e["url"]) <= cols:
        head.append(("r", cols, [(e["url"], "m")]))
    rows = [head]
    if "bars" in e:
        rows += [[]] + bar_rows(e["bars"], 2, cols) + [[]]
    rows += wrapped(e["copy"], cols - 2, 2)
    if e.get("note"):
        rows += wrapped(e["note"], cols - 2, 2, "m")
    return rows

def session(cmd, entries, cols, W, title, last=False):
    rows = [prompt(cmd)]
    for e in entries:
        rows += [[]] + e
    if last:
        rows += [[], prompt("") + [("cur", 4)]]
    return draw(rows, W, title)

def writing_rows(w, cols):
    rows = [wrapped(w["intro"], cols, 0, "m")]
    posts = []
    for date, title in w["posts"]:
        lines = textwrap.wrap(title, cols - 12)
        posts.append([("t", 0, [(date, "k")]), ("t", 12, [(lines[0], "t")])])
        posts += [[("t", 12, [(l, "t")])] for l in lines[1:]]
    return rows + [posts]

# ------------------------------------------------------------------ main
def card_size(stats, narrow):
    w = float(re.search(r'width="(\d+)"', bc.card("dark", narrow, stats)).group(1))
    return w, int((w - 2 * PAD) / CW)

if __name__ == "__main__":
    stats = json.loads((HERE / "stats.json").read_text())
    projects, experiments, writing = content(stats)
    out = ROOT / "assets"
    for narrow in (False, True):
        W, cols = card_size(stats, narrow)
        sfx = "-narrow" if narrow else ""
        (out / f"session-projects{sfx}.svg").write_text(
            session("ls ~/projects", [entry(e, cols) for e in projects], cols, W, "Projects: " + ", ".join(e["slug"] for e in projects)))
        (out / f"session-experiments{sfx}.svg").write_text(
            session("ls ~/experiments", [entry(e, cols) for e in experiments], cols, W,
                    "Experiments: Agent Harness Lab (agent loop 67.5%, one-shot 31.25%) and Video-to-Handout"))
        (out / f"session-writing{sfx}.svg").write_text(
            session("ls -t ~/writing | head -3", writing_rows(writing, cols), cols, W, "Writing: three selected posts", last=True))
    print("wrote", ", ".join(sorted(p.name for p in out.glob("session-*.svg"))))
