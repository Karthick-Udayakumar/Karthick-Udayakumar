"""Generate github-metrics.svg for the profile README.

Uses only the GitHub GraphQL API and the Python standard library.
Reads GITHUB_TOKEN and LOGIN from the environment.
"""

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
    followers { totalCount }
    repositories(ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false, first: 100) {
      totalCount
      nodes { stargazerCount primaryLanguage { name } }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
    }
  }
}
"""


def fetch_user(login):
    payload = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "profile-metrics",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.load(response)
    if body.get("errors"):
        raise SystemExit(f"GraphQL error: {body['errors']}")
    return body["data"]["user"]


def build_svg(user):
    repos = user["repositories"]["nodes"]
    contributions = user["contributionsCollection"]
    stats = [
        ("Public repositories", user["repositories"]["totalCount"]),
        ("Total stars", sum(r["stargazerCount"] for r in repos)),
        ("Followers", user["followers"]["totalCount"]),
        ("Commits (last year)", contributions["totalCommitContributions"]),
        ("Pull requests (last year)", contributions["totalPullRequestContributions"]),
        ("Issues (last year)", contributions["totalIssueContributions"]),
    ]
    languages = Counter(
        r["primaryLanguage"]["name"] for r in repos if r["primaryLanguage"]
    ).most_common(5)
    max_count = max((count for _, count in languages), default=1)

    rows = []
    for index, (label, value) in enumerate(stats):
        y = 70 + index * 30
        rows.append(f'<text x="30" y="{y}" class="label">{html.escape(label)}</text>')
        rows.append(f'<text x="290" y="{y}" class="value">{value:,}</text>')

    bars = []
    for index, (name, count) in enumerate(languages):
        y = 70 + index * 30
        width = int(180 * count / max_count)
        bars.append(f'<text x="380" y="{y}" class="label">{html.escape(name)}</text>')
        bars.append(f'<rect x="500" y="{y - 12}" width="{width}" height="12" rx="3" class="bar"/>')
        bars.append(f'<text x="{505 + width}" y="{y}" class="value">{count}</text>')

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="720" height="260" viewBox="0 0 720 260">
  <style>
    .card {{ fill: #0d1117; stroke: #30363d; }}
    .title {{ font: 600 18px -apple-system, Segoe UI, Helvetica, Arial, sans-serif; fill: #58a6ff; }}
    .section {{ font: 600 13px -apple-system, Segoe UI, Helvetica, Arial, sans-serif; fill: #8b949e; }}
    .label {{ font: 14px -apple-system, Segoe UI, Helvetica, Arial, sans-serif; fill: #c9d1d9; }}
    .value {{ font: 600 14px -apple-system, Segoe UI, Helvetica, Arial, sans-serif; fill: #f0f6fc; }}
    .bar {{ fill: #238636; }}
  </style>
  <rect x="0.5" y="0.5" width="719" height="259" rx="8" class="card"/>
  <text x="30" y="36" class="title">{html.escape(user.get("name") or LOGIN)} - GitHub metrics</text>
  <text x="30" y="56" class="section">OVERVIEW</text>
  <text x="380" y="56" class="section">TOP LANGUAGES (by repos)</text>
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
