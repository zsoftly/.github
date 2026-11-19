# `.github`: ZSoftly organization defaults

This repository holds organization-wide GitHub defaults for **github.com/zsoftly**.

- **`profile/README.md`**: renders as the public organization profile at
  [github.com/zsoftly](https://github.com/zsoftly). Edit this to change what visitors see.
- **`profile/assets/`**: self-contained images used by the profile README, including the GitHub
  organization banner and avatar.
- **`profile/assets/zsoftly-github-avatar-1024x1024.png`**: manual upload for the GitHub
  organization avatar. It is an opaque ZSoftly-blue square with the white dot mark, made to avoid
  the grey or dark framing seen with a transparent circular image.
- **`FUNDING.yml`**: (optional) enables the **Sponsor** button across the org.

To publish, make this repository **public** and name it exactly **`.github`** under the `zsoftly`
organization.

Add org-wide community health files here too (issue/PR templates, `CODE_OF_CONDUCT.md`,
`SECURITY.md`, `CONTRIBUTING.md`). GitHub falls back to these for any repo that lacks its own.

## Shared checks

### No AI attribution

Company policy: no AI attribution in commits, pull request titles or pull request descriptions.
`scripts/no-ai-attribution/check.py` lists the patterns in one place: co-author trailers that name
an AI tool or vendor, AI vendor noreply addresses, and "generated with" footers that name an AI
tool. Plain mentions of a tool, such as a commit about a CLI config, pass.

`.github/workflows/no-ai-attribution.yml` is the reusable workflow. Each repository calls it with
the caller in `workflow-templates/no-ai-attribution.yml`; never copy the logic. The check name is
`no-ai-attribution / check`. Public repositories require it through a repository ruleset; on
GitHub Free a private repository can run it but cannot require it.

Dependabot and Renovate pull request descriptions are not checked, because they quote upstream
release notes. Their commits are.

To fix a failing pull request, reword the listed commits (`git rebase -i origin/main`, mark them
`reword`, delete the line) and run `git push --force-with-lease`. Edit the title or description in
the pull request; the check runs again on every edit.

Run the tests with `python3 -m unittest discover -s scripts/no-ai-attribution`. The script also
works as a local `commit-msg` hook: `python3 scripts/no-ai-attribution/check.py "$1"`.
