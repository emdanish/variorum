---
name: variorum-git-github
description: Use for Git/GitHub workflow on Variorum — branching, commits, pull requests, repository hygiene, and GitHub App development (JWT/installation tokens, webhooks, local tunneling).
---

# Variorum Git & GitHub workflow

## Commits & branches
- Work on `main` for this solo repo's incremental milestones; branch off `main` for anything experimental or risky (e.g. demo branches).
- Commit only when a change is **complete and tested** (suite + mypy + ruff green). Small, coherent commits — not one-line-at-a-time.
- Conventional messages: `feat(...)`, `fix(...)`, `chore(...)`, `harden(...)`. Subject then a body explaining *why*. End with:
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
- **Before every commit**, confirm secrets are excluded: `git diff --cached --name-only | grep -x ".env"` should print nothing; `.env`, `*.pem`, `secrets/`, `.venv/`, `node_modules/` stay ignored.

## Pull requests
- Human review is the gate. Variorum-generated PRs (doc-fix, test) go to non-protected branches and are **never auto-merged or force-pushed**.

## GitHub App development
- Auth flow: App JWT (RS256, from the private key) → per-installation access token (short-lived, cached) → repo reads/writes. User identity via the App's OAuth (`client_id`/`secret`).
- Config lives in `.env` (`GITHUB_APP_*`); see `SETUP.md` for the click-by-click App creation and every value.
- Local webhooks need a tunnel (smee.io): `npx --yes -p smee-client smee --url <smee-url> --target http://localhost:8000/webhooks/github`. The App's webhook secret must match `GITHUB_WEBHOOK_SECRET`.
- For a demo without a tunnel, use the manual "Analyze" endpoints instead of webhooks.

## Repo hygiene
- `.gitattributes` normalizes line endings to LF (deploys target Linux). Delete throwaway branches after use.
