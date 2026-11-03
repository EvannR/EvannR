#!/usr/bin/env python3
"""
Contribution forest: turns a GitHub contribution calendar into an animated SVG.

Each day with contributions becomes a tree (bigger = more contributions).
The forest grows in a wave from left to right, a harvest front then sweeps
across and cuts it down, and the cycle starts again: growth, harvest,
regeneration.

Usage:
  GITHUB_TOKEN=... python forest.py --user EvannR --out dist
  python forest.py --demo --out dist        # random data, no token needed
"""
import argparse
import json
import os
import random
import urllib.request
from datetime import date, timedelta

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks { contributionDays { date weekday contributionCount contributionLevel } }
      }
    }
  }
}
"""

LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2,
          "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}

THEMES = {
    "light": {
        "soil": "#ebedf0", "soil_used": "#e3d9c6", "trunk": "#8a6a46",
        "leaf": ["#9be9a8", "#40c463", "#30a14e", "#216e39"],
        "pine": ["#7fd492", "#2f9e55", "#23803f", "#185a2c"],
        "front": "#d9a441",     },
    "dark": {
        "soil": "#161b22", "soil_used": "#2b2419", "trunk": "#a07a4f",
        "leaf": ["#2ea043", "#26a641", "#2ea043", "#39d353"],
        "pine": ["#238636", "#1f8a37", "#238636", "#2fb547"],
        "front": "#e3b341",     },
}

PITCH = 16          # distance between cells
CELL = 12           # size of a soil patch
LEFT, TOP = 10, 14  # margins
PERIOD = 18.0       # seconds for one full cycle
STEP = 0.09         # delay between two columns (speed of the wave)


def fetch(user, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": user}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        payload = json.load(r)
    if "errors" in payload:
        raise SystemExit(payload["errors"])
    weeks = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [[(d["weekday"], LEVELS[d["contributionLevel"]], d["contributionCount"])
             for d in w["contributionDays"]] for w in weeks]


def demo():
    rng = random.Random(4)
    start = date.today() - timedelta(days=364)
    start -= timedelta(days=(start.weekday() + 1) % 7)
    weeks, day = [], start
    while day <= date.today():
        week = []
        for wd in range(7):
            if day > date.today():
                break
            lvl = rng.choices([0, 1, 2, 3, 4], [50, 20, 15, 10, 5])[0]
            week.append((wd, lvl, lvl * 3))
            day += timedelta(days=1)
        weeks.append(week)
    return weeks


def tree(level, pine, c):
    """Tree drawn with its base at (0, 0), growing upwards."""
    if level == 1:  # sprout
        return (f'<path d="M0 0V-4" stroke="{c["trunk"]}" stroke-width="1.1"/>'
                f'<ellipse cx="-1.8" cy="-4.4" rx="2" ry="1.1" fill="{c["leaf"][0]}" transform="rotate(-25 -1.8 -4.4)"/>'
                f'<ellipse cx="1.8" cy="-4.8" rx="2" ry="1.1" fill="{c["leaf"][1]}" transform="rotate(25 1.8 -4.8)"/>')
    h = {2: 3.0, 3: 3.5, 4: 4.0}[level]
    trunk = f'<rect x="-0.9" y="{-h:.1f}" width="1.8" height="{h:.1f}" rx="0.5" fill="{c["trunk"]}"/>'
    if pine:
        w, top = {2: 4.0, 3: 5.0, 4: 6.0}[level], {2: 10, 3: 12.5, 4: 15}[level]
        col = c["pine"][level - 1]
        mid = h + (top - h) * 0.45
        return (trunk +
                f'<path d="M{-w} {-h + 0.5}L0 {-mid - 2}L{w} {-h + 0.5}Z" fill="{col}"/>'
                f'<path d="M{-w * 0.75} {-mid + 1}L0 {-top}L{w * 0.75} {-mid + 1}Z" fill="{col}"/>')
    r = {2: 3.4, 3: 4.4, 4: 5.3}[level]
    cy = -h - r + 0.8
    col, light = c["leaf"][level - 1], c["leaf"][max(level - 2, 0)]
    return (trunk + f'<circle cy="{cy:.1f}" r="{r}" fill="{col}"/>'
            f'<circle cx="{-r * 0.35:.1f}" cy="{cy - r * 0.35:.1f}" r="{r * 0.38:.1f}" fill="{light}" opacity="0.7"/>')


def render(weeks, theme):
    c = THEMES[theme]
    ncol = len(weeks)
    width = LEFT * 2 + ncol * PITCH
    height = TOP + 7 * PITCH + 8
    sweep = ncol * STEP                       # time for a wave to cross the grid
    grow_end, cut_at = 9, 62                  # % of the cycle
    front_start = cut_at / 100 * PERIOD
    f0 = front_start / PERIOD * 100
    f1 = (front_start + sweep) / PERIOD * 100

    css = f"""
    .t {{ transform-box: fill-box; transform-origin: 50% 100%;
          animation: life {PERIOD}s linear infinite both; }}
    @keyframes life {{
      0%   {{ transform: scale(0); opacity: 0; }}
      1%   {{ opacity: 1; }}
      {grow_end}%  {{ transform: scale(1.08); }}
      {grow_end + 3}% {{ transform: scale(1); }}
      {cut_at}%  {{ transform: scale(1); opacity: 1; }}
      {cut_at + 1.5}% {{ transform: scale(0.18, 0.12); opacity: 0.9; }}
      {cut_at + 14}% {{ transform: scale(0.18, 0.12); opacity: 0; }}
      100% {{ transform: scale(0); opacity: 0; }}
    }}
    .front {{ animation: front {PERIOD}s linear infinite; }}
    @keyframes front {{
      0%, {f0:.2f}% {{ transform: translateX(0); opacity: 0; }}
      {f0 + 0.5:.2f}% {{ opacity: 0.55; }}
      {f1 - 0.5:.2f}% {{ opacity: 0.55; }}
      {f1:.2f}%, 100% {{ transform: translateX({ncol * PITCH}px); opacity: 0; }}
    }}
    """

    soil, trees = [], []
    for x, week in enumerate(weeks):
        for wd, level, _ in week:
            px, py = LEFT + x * PITCH, TOP + wd * PITCH
            fill = c["soil_used"] if level else c["soil"]
            soil.append(f'<rect x="{px + 2}" y="{py + 2}" width="{CELL}" height="{CELL}" rx="2.5" fill="{fill}"/>')
            if level:
                pine = level >= 3 and (x * 7 + wd) % 3 == 0
                cx, base = px + 2 + CELL / 2, py + 2 + CELL - 1
                trees.append(
                    f'<g transform="translate({cx:.1f} {base:.1f})">'
                    f'<g class="t" style="animation-delay:{x * STEP:.2f}s">{tree(level, pine, c)}</g></g>')

    front = (f'<g class="front"><rect x="{LEFT - 6}" y="{TOP - 4}" width="5" height="{7 * PITCH + 6}" '
             f'rx="2.5" fill="{c["front"]}"/></g>')

    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">'
            f'<style>{css}</style>{"".join(soil)}{front}{"".join(trees)}</svg>')


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--user", default="EvannR")
    p.add_argument("--out", default="dist")
    p.add_argument("--demo", action="store_true")
    a = p.parse_args()
    weeks = demo() if a.demo else fetch(a.user, os.environ["GITHUB_TOKEN"])
    os.makedirs(a.out, exist_ok=True)
    for theme in THEMES:
        path = os.path.join(a.out, f"forest-{theme}.svg")
        with open(path, "w") as f:
            f.write(render(weeks, theme))
        print("wrote", path)


if __name__ == "__main__":
    main()
