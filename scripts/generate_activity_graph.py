#!/usr/bin/env python3
"""Render a self-hosted contribution graph from GitHub's live calendar."""

from __future__ import annotations

import json
import os
import sys
from datetime import date
from html import escape
from urllib.request import Request, urlopen

API_URL = "https://api.github.com/graphql"
USERNAME = os.environ.get("GITHUB_USERNAME", "SakshamSinghal20")
TOKEN = os.environ.get("GITHUB_TOKEN")
OUTPUT = os.environ.get("ACTIVITY_GRAPH_OUTPUT", "dist/activity-graph.svg")

if not TOKEN:
    raise SystemExit("GITHUB_TOKEN is required")

query = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            color
          }
        }
      }
    }
  }
}
"""

payload = json.dumps({"query": query, "variables": {"login": USERNAME}}).encode()
request = Request(
    API_URL,
    data=payload,
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "SakshamSinghal20-profile-activity-graph",
    },
    method="POST",
)

with urlopen(request, timeout=30) as response:
    result = json.load(response)

if result.get("errors"):
    raise SystemExit(json.dumps(result["errors"]))

calendar = result["data"]["user"]["contributionsCollection"]["contributionCalendar"]
weeks = calendar["weeks"]
days = [day for week in weeks for day in week["contributionDays"]]
if not days:
    raise SystemExit("GitHub returned an empty contribution calendar")

# Keep the same compact 53-week profile shape used by GitHub's calendar.
weeks = weeks[-53:]
max_count = max((day["contributionCount"] for week in weeks for day in week["contributionDays"]), default=0)
weekly_totals = [sum(day["contributionCount"] for day in week["contributionDays"]) for week in weeks]

width, height = 1040, 310
left, top = 34, 72
cell, gap = 13, 4
plot_width = 53 * (cell + gap) - gap
plot_height = 7 * (cell + gap) - gap
palette = ["#161b22", "#123b46", "#087f8c", "#00b8a9", "#00f5d4"]

svg = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">')
svg.append('<title id="title">PLAYER 01 // LIVE ACTIVITY</title>')
svg.append(f'<desc id="desc">{escape(USERNAME)} has {calendar["totalContributions"]} contributions in the last year.</desc>')
svg.append('<rect width="100%" height="100%" rx="16" fill="#0b1020"/>')
svg.append('<rect x="1" y="1" width="1038" height="308" rx="15" fill="none" stroke="#243b63"/>')
svg.append('<text x="34" y="34" fill="#00f5d4" font-family="monospace" font-size="18" font-weight="700">PLAYER 01 // LIVE ACTIVITY</text>')
svg.append(f'<text x="1005" y="34" text-anchor="end" fill="#ffe66d" font-family="monospace" font-size="14">{calendar["totalContributions"]} CONTRIBUTIONS</text>')
svg.append(f'<text x="34" y="57" fill="#8b9bb4" font-family="monospace" font-size="11">SOURCE: GITHUB CONTRIBUTION CALENDAR • REFRESHED {date.today().isoformat()}</text>')

# Draw the contribution cells in the same week/weekday order as GitHub.
for x, week in enumerate(weeks):
    for y, day in enumerate(week["contributionDays"]):
        count = day["contributionCount"]
        level = 0 if max_count == 0 else min(4, int((count / max_count) * 4) + (1 if count else 0))
        rx = left + x * (cell + gap)
        ry = top + y * (cell + gap)
        label = f'{day["date"]}: {count} contribution' + ("s" if count != 1 else "")
        svg.append(f'<rect x="{rx}" y="{ry}" width="{cell}" height="{cell}" rx="3" fill="{palette[level]}"><title>{escape(label)}</title></rect>')

# Add a compact weekly trend line beneath the grid for a more arcade-like readout.
chart_top = top + plot_height + 34
max_week = max(weekly_totals, default=1) or 1
points = []
for i, total in enumerate(weekly_totals):
    px = left + i * (cell + gap) + cell / 2
    py = chart_top + 40 - (total / max_week) * 40
    points.append(f"{px:.1f},{py:.1f}")
svg.append(f'<line x1="{left}" y1="{chart_top + 40}" x2="{left + plot_width}" y2="{chart_top + 40}" stroke="#243b63"/>')
svg.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="#00f5d4" stroke-width="2.5" stroke-linejoin="round"/>')
for point in points:
    px, py = point.split(",")
    svg.append(f'<circle cx="{px}" cy="{py}" r="3.2" fill="#ff2e63" stroke="#0b1020" stroke-width="1.5"/>')
svg.append(f'<text x="{left}" y="{height - 12}" fill="#8b9bb4" font-family="monospace" font-size="11">LOW ACTIVITY</text>')
svg.append(f'<text x="{left + plot_width}" y="{height - 12}" text-anchor="end" fill="#8b9bb4" font-family="monospace" font-size="11">HIGH ACTIVITY</text>')
svg.append("</svg>")

os.makedirs(os.path.dirname(OUTPUT) or ".", exist_ok=True)
with open(OUTPUT, "w", encoding="utf-8") as handle:
    handle.write("\n".join(svg) + "\n")

print(f"Generated {OUTPUT} for {USERNAME}: {calendar['totalContributions']} contributions")
