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
import time
import urllib.error
import urllib.request

# The single list of patterns, matched per line and case-insensitively.
TOOLS = r"claude|anthropic|openai|chatgpt|gpt|copilot|codex|gemini|cursor|aider|windsurf"
PATTERNS = [
    re.compile(rf"^\s*(co-authored|assisted|generated)-by:[^<]*\b({TOOLS})\b", re.I),
    re.compile(r"^\s*[\w-]+:.*@anthropic\.com\b|\bnoreply@(anthropic|openai)\.com\b", re.I),
    re.compile(rf"^\W*generated (with|by|using)\W+({TOOLS}|ai)\b", re.I),
    re.compile("\U0001f916.*\\bgenerated\\b", re.I),
]
# Their PR descriptions quote upstream release notes and commits, which we do not control.
BOT_SKIP_BODY = re.compile(r"(dependabot|renovate).*\[bot\]$")


def offending_lines(text):
    return [line.strip() for line in (text or "").splitlines() if any(p.search(line) for p in PATTERNS)]


def commit_findings(commit):
    """Message lines, plus an AI author or committer: a squash merge turns those into trailers."""
    people = [f"Co-authored-by: {p['name']} <{p['email']}>" for p in (commit["author"], commit["committer"]) if p]
    return offending_lines(commit["message"]) + offending_lines("\n".join(people))


def message_file(path):
    """A commit message file as git uses it: no comment lines, nothing below the scissors line."""
    lines = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("# ------------------------ >8"):
                break
            if not line.startswith("#"):
                lines.append(line)
    return "".join(lines)


def api(path):
    url = f"{os.environ.get('GITHUB_API_URL', 'https://api.github.com')}/{path}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "no-ai-attribution-check",
    })
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))


def pr_findings(repo, number):
    pr = api(f"repos/{repo}/pulls/{number}")
    found = []
    if not BOT_SKIP_BODY.search(pr["user"]["login"]):
        found += [("PR title", line) for line in offending_lines(pr["title"])]
        found += [("PR description", line) for line in offending_lines(pr["body"])]
    page = 1
    while True:
        commits = api(f"repos/{repo}/pulls/{number}/commits?per_page=100&page={page}")
        for c in commits:
            found += [(f"commit {c['sha'][:12]}", line) for line in commit_findings(c["commit"])]
        if len(commits) < 100:
            break
        page += 1
    if pr["commits"] > 250:
        print(f"::warning::GitHub lists only the first 250 of {pr['commits']} commits; later ones were not checked.")
    return found, pr["base"]["ref"]


def main(argv):
    if argv:
        found = [(path, line) for path in argv for line in offending_lines(message_file(path))]
        base = "main"
    elif not os.environ.get("PR_NUMBER"):
        print("Not a pull request event; nothing to check.")
        return 0
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
