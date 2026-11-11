"""Generate github-metrics.svg for the profile README.

Uses the GitHub GraphQL and REST APIs with the Python standard library only.
Reads GITHUB_TOKEN and LOGIN from the environment.
"""

import datetime
import html
import json
import os
import urllib.request
from collections import Counter

LOGIN = os.environ.get("LOGIN", "Karthick-Udayakumar")
TOKEN = os.environ["GITHUB_TOKEN"]
OUTPUT = "github-metrics.svg"

QUERY = """
query($login: String!) {
  user(login: $login) {
    name
    followers { totalCount }
    repositories(ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false, first: 100) {
      totalCount
      nodes { name owner { login } stargazerCount }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalRepositoriesWithContributedCommits
      contributionCalendar {
        weeks { contributionDays { contributionCount date } }
      }
    }
  }
}
"""


def request(url, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {
        "Authorization": f"bearer {TOKEN}",
        "User-Agent": "profile-metrics",
        "Accept": "application/vnd.github+json",
    }
    if payload is not None:
        headers["Content-Type"] = "application/json"
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=30) as response:
        return json.load(response)


def fetch_user(login):
    body = request("https://api.github.com/graphql", {"query": QUERY, "variables": {"login": login}})
    if body.get("errors"):
        raise SystemExit(f"GraphQL error: {body['errors']}")
    return body["data"]["user"]


def language_bytes(repos):
    totals = Counter()
    for repo in repos:
        url = f"https://api.github.com/repos/{repo['owner']['login']}/{repo['name']}/languages"
        totals.update(request(url))
    return totals


def streaks(days):
    counted = [d for d in sorted(days, key=lambda d: d["date"])]
    longest = current = 0
    for day in counted:
        current = current + 1 if day["contributionCount"] > 0 else 0
        longest = max(longest, current)
    # The current streak counts back from today, or from yesterday if today has no commits yet.
    today = datetime.date.today().isoformat()
    current_run = 0
    for day in reversed(counted):
        if day["date"] > today:
            continue
        if day["contributionCount"] > 0:
            current_run += 1
        elif day["date"] == today:
            continue
        else:
            break
    return current_run, longest


LANGUAGE_COLORS = {
    "Python": "#3572A5",
    "TypeScript": "#3178C6",
    "JavaScript": "#F1E05A",
    "HTML": "#E34C26",
    "CSS": "#563D7C",
    "Java": "#B07219",
    "Shell": "#89E051",
}
FONT = "-apple-system, Segoe UI, Helvetica, Arial, sans-serif"


def build_svg(user):
    repos = user["repositories"]["nodes"]
    contributions = user["contributionsCollection"]
    days = [d for week in contributions["contributionCalendar"]["weeks"] for d in week["contributionDays"]]
    current_streak, longest_streak = streaks(days)
    stats = [
        ("Total stars", sum(r["stargazerCount"] for r in repos)),
        ("Commits (last year)", contributions["totalCommitContributions"]),
        ("Pull requests (last year)", contributions["totalPullRequestContributions"]),
        ("Issues (last year)", contributions["totalIssueContributions"]),
        ("Contributed to (last year)", contributions["totalRepositoriesWithContributedCommits"]),
        ("Public repositories", user["repositories"]["totalCount"]),
        ("Followers", user["followers"]["totalCount"]),
        ("Current streak (days)", current_streak),
        ("Longest streak (days)", longest_streak),
    ]

    languages = language_bytes(repos)
    total_bytes = sum(languages.values()) or 1
    top_languages = languages.most_common(6)
    largest = top_languages[0][1] if top_languages else 1

    row_pitch = 36
    first_row = 146
    height = first_row + (len(stats) - 1) * row_pitch + 52

    rows = []
    for index, (label, value) in enumerate(stats):
        y = first_row + index * row_pitch
        rows.append(f'<text x="40" y="{y}" class="label">{html.escape(label)}</text>')
        rows.append(f'<text x="330" y="{y}" class="value" text-anchor="end">{value:,}</text>')
        if index < len(stats) - 1:
            rows.append(f'<line x1="40" x2="330" y1="{y + 14}" y2="{y + 14}" class="rule"/>')

    bars = []
    for index, (name, size) in enumerate(top_languages):
        y = first_row + index * row_pitch
        color = LANGUAGE_COLORS.get(name, "#58A6FF")
        bar_width = max(4, int(130 * size / largest))
        bars.append(f'<circle cx="396" cy="{y - 5}" r="5" fill="{color}"/>')
        bars.append(f'<text x="410" y="{y}" class="label">{html.escape(name)}</text>')
        bars.append(f'<rect x="530" y="{y - 11}" width="{bar_width}" height="10" rx="5" fill="{color}"/>')
        bars.append(f'<text x="722" y="{y}" class="value" text-anchor="end">{100 * size / total_bytes:.1f}%</text>')

    name = html.escape(user.get("name") or LOGIN)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="760" height="{height}" viewBox="0 0 760 {height}">
  <style>
    .card {{ fill: #0d1117; stroke: #30363d; }}
    .title {{ font: 700 20px {FONT}; fill: #f0f6fc; }}
    .subtitle {{ font: 400 13px {FONT}; fill: #8b949e; }}
    .section {{ font: 600 12px {FONT}; fill: #58a6ff; letter-spacing: 1px; }}
    .label {{ font: 400 14px {FONT}; fill: #c9d1d9; }}
    .value {{ font: 600 14px {FONT}; fill: #f0f6fc; }}
    .rule {{ stroke: #21262d; stroke-width: 1; }}
    .divider {{ stroke: #30363d; stroke-width: 1; }}
    .footer {{ font: 400 11px {FONT}; fill: #6e7681; }}
  </style>
  <rect x="0.5" y="0.5" width="759" height="{height - 1}" rx="10" class="card"/>
  <text x="40" y="46" class="title">{name}</text>
  <text x="40" y="68" class="subtitle">@{html.escape(LOGIN)} · AI &amp; QA engineering</text>
  <text x="40" y="106" class="section">OVERVIEW</text>
  <text x="396" y="106" class="section">TOP LANGUAGES BY CODE SIZE</text>
  <line x1="360" x2="360" y1="90" y2="{height - 40}" class="divider"/>
  {chr(10).join("  " + row for row in rows)}
  {chr(10).join("  " + bar for bar in bars)}
  <text x="40" y="{height - 18}" class="footer">Updated daily from the GitHub API</text>
</svg>
"""


def main():
    user = fetch_user(LOGIN)
    with open(OUTPUT, "w", encoding="utf-8") as file:
        file.write(build_svg(user))
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
