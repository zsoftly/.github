#!/usr/bin/env python3
"""Fail a pull request whose commits, title or description carry AI attribution.

CI:    GITHUB_TOKEN, GITHUB_REPOSITORY and PR_NUMBER set (see the reusable workflow).
Local: check.py FILE...   (for example .git/COMMIT_EDITMSG in a commit-msg hook)
No dependencies beyond the Python 3 standard library.
"""
import json
import os
import re
import sys
import urllib.request

# The single list of patterns. Each one matches a whole line, case-insensitively.
TOOLS = r"claude|anthropic|openai|chatgpt|copilot|codex|gemini|cursor"
PATTERNS = [
    re.compile(rf"^\s*co-authored-by:.*\b({TOOLS})\b", re.I),
    re.compile(r"@anthropic\.com\b|\bnoreply@openai\.com\b", re.I),
    re.compile(rf"\bgenerated (with|by)\W+({TOOLS}|ai)\b", re.I),
    re.compile("\U0001f916.*\\bgenerated\\b", re.I),
]
# Their PR descriptions quote upstream release notes and commits, which we do not control.
BOTS_SKIP_BODY = {"dependabot[bot]", "renovate[bot]"}


def offending_lines(text):
    return [line.strip() for line in (text or "").splitlines() if any(p.search(line) for p in PATTERNS)]


def api(path):
    url = f"{os.environ.get('GITHUB_API_URL', 'https://api.github.com')}/{path}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "no-ai-attribution-check",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def pr_findings(repo, number):
    pr = api(f"repos/{repo}/pulls/{number}")
    found = []
    if pr["user"]["login"] not in BOTS_SKIP_BODY:
        found += [("PR title", line) for line in offending_lines(pr["title"])]
        found += [("PR description", line) for line in offending_lines(pr["body"])]
    page = 1
    while True:
        commits = api(f"repos/{repo}/pulls/{number}/commits?per_page=100&page={page}")
        for c in commits:
            found += [(f"commit {c['sha'][:12]}", line) for line in offending_lines(c["commit"]["message"])]
        if len(commits) < 100:
            break
        page += 1
    if pr["commits"] > 250:
        print(f"::warning::GitHub lists only the first 250 of {pr['commits']} commits; later ones were not checked.")
    return found, pr["base"]["ref"]


def main(argv):
    if argv:
        found = [(path, line) for path in argv for line in offending_lines(open(path, encoding="utf-8").read())]
        base = "main"
    else:
        found, base = pr_findings(os.environ["GITHUB_REPOSITORY"], os.environ["PR_NUMBER"])
    if not found:
        print("No AI attribution found.")
        return 0
    for where, line in found:
        print(f"::error title=AI attribution::{where}: {line}".replace("%", "%25"))
    print(f"""
ZSoftly policy: no AI attribution in commits, PR titles or PR descriptions.
How to fix:
  Commits: git fetch origin && git rebase -i origin/{base}
           mark each commit listed above as 'reword', delete the attribution line,
           then git push --force-with-lease
  Title or description: edit the pull request; this check runs again on every edit.""")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
