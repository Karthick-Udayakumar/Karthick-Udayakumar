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


def build_svg(user):
    repos = user["repositories"]["nodes"]
    contributions = user["contributionsCollection"]
    days = [d for week in contributions["contributionCalendar"]["weeks"] for d in week["contributionDays"]]
    current_streak, longest_streak = streaks(days)
    stats = [
        ("Total stars", sum(r["stargazerCount"] for r in repos)),
        ("Total commits (last year)", contributions["totalCommitContributions"]),
        ("Total PRs (last year)", contributions["totalPullRequestContributions"]),
        ("Total issues (last year)", contributions["totalIssueContributions"]),
        ("Contributed to (last year)", contributions["totalRepositoriesWithContributedCommits"]),
        ("Public repositories", user["repositories"]["totalCount"]),
        ("Followers", user["followers"]["totalCount"]),
        ("Current streak (days)", current_streak),
        ("Longest streak (days)", longest_streak),
    ]

    languages = language_bytes(repos)
    total_bytes = sum(languages.values()) or 1
    top_languages = languages.most_common(6)

    rows = []
    for index, (label, value) in enumerate(stats):
        y = 74 + index * 22
        rows.append(f'<text x="30" y="{y}" class="label">{html.escape(label)}</text>')
        rows.append(f'<text x="250" y="{y}" class="value" text-anchor="end">{value:,}</text>')

    bars = []
    for index, (name, size) in enumerate(top_languages):
        y = 74 + index * 30
        percent = 100 * size / total_bytes
        width = int(200 * size / total_bytes / (top_languages[0][1] / total_bytes))
        bars.append(f'<text x="380" y="{y}" class="label">{html.escape(name)}</text>')
        bars.append(f'<rect x="500" y="{y - 11}" width="{width}" height="11" rx="3" class="bar"/>')
        bars.append(f'<text x="710" y="{y}" class="value" text-anchor="end">{percent:.1f}%</text>')

    height = 74 + 9 * 22 + 20
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="720" height="{height}" viewBox="0 0 720 {height}">
  <style>
    .card {{ fill: #0d1117; stroke: #30363d; }}
    .title {{ font: 600 18px -apple-system, Segoe UI, Helvetica, Arial, sans-serif; fill: #58a6ff; }}
    .section {{ font: 600 13px -apple-system, Segoe UI, Helvetica, Arial, sans-serif; fill: #8b949e; }}
    .label {{ font: 14px -apple-system, Segoe UI, Helvetica, Arial, sans-serif; fill: #c9d1d9; }}
    .value {{ font: 600 14px -apple-system, Segoe UI, Helvetica, Arial, sans-serif; fill: #f0f6fc; }}
    .bar {{ fill: #238636; }}
  </style>
  <rect x="0.5" y="0.5" width="719" height="{height - 1}" rx="8" class="card"/>
  <text x="30" y="36" class="title">{html.escape(user.get("name") or LOGIN)} - GitHub stats</text>
  <text x="30" y="56" class="section">OVERVIEW</text>
  <text x="380" y="56" class="section">TOP LANGUAGES (by code size)</text>
  {chr(10).join("  " + row for row in rows)}
  {chr(10).join("  " + bar for bar in bars)}
</svg>
"""


def main():
    user = fetch_user(LOGIN)
    with open(OUTPUT, "w", encoding="utf-8") as file:
        file.write(build_svg(user))
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
