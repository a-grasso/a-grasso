"""Rewrite the latest-releases block in README.md from the GitHub API."""

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

OWNER = "a-grasso"
LIMIT = 5
START = "<!-- releases:start -->"
END = "<!-- releases:end -->"
VERSION_TAG = re.compile(r"^v?\d+\.\d+")

QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false) {
      nodes {
        name
        url
        isArchived
        description
        releases(first: 10, orderBy: {field: CREATED_AT, direction: DESC}) {
          nodes { tagName url publishedAt isDraft isPrerelease }
        }
      }
    }
  }
}
"""


def fetch_repos():
    out = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={QUERY}", "-f", f"login={OWNER}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return json.loads(out)["data"]["user"]["repositories"]["nodes"]


def latest_release(repo):
    for release in repo["releases"]["nodes"]:
        if release["isDraft"] or release["isPrerelease"] or not release["publishedAt"]:
            continue
        if VERSION_TAG.match(release["tagName"]):
            return release
    return None


def render(repos):
    rows = []
    for repo in repos:
        if repo["isArchived"] or repo["name"] == OWNER:
            continue
        release = latest_release(repo)
        if release:
            rows.append((release["publishedAt"], repo, release))
    rows.sort(key=lambda row: row[0], reverse=True)
    lines = []
    for published, repo, release in rows[:LIMIT]:
        day = datetime.fromisoformat(published.replace("Z", "+00:00")).strftime("%b %-d, %Y")
        lines.append(
            f"- [**{repo['name']}**]({repo['url']}) "
            f"[`{release['tagName']}`]({release['url']}) · {day}"
        )
    return "\n".join(lines)


def main():
    readme = Path(sys.argv[1] if len(sys.argv) > 1 else "README.md")
    text = readme.read_text()
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(text):
        sys.exit(f"{readme}: releases markers not found")
    block = f"{START}\n{render(fetch_repos())}\n{END}"
    readme.write_text(pattern.sub(lambda _: block, text))


if __name__ == "__main__":
    main()
