---
name: variorum-docs
description: Use when writing or updating Variorum documentation — PROJECT_PLAN.md, CLAUDE.md, ADRs, SETUP.md, or tracking implementation progress. Apply whenever a milestone lands or a significant decision is made.
---

# Variorum documentation & tracking

Three living documents — keep them current as work lands:

- **`CLAUDE.md`** — permanent project memory (stack, architecture, conventions, skills, library decisions, $0 rule, dev commands). The entry point for any new session. Update when architecture, tooling, or conventions change.
- **`PROJECT_PLAN.md`** — the PRD + architecture + roadmap + **build log**. Append to the build log every milestone (what shipped, tests, verification). Convert relative dates to absolute.
- **`SETUP.md`** — onboarding/demo guide (GitHub App, `.env`, run/verify/demo steps). Update when setup or env vars change.

## Architecture Decision Records
- Significant/irreversible decisions get an ADR in `docs/adr/NNNN-title.md` (context → decision → consequences). ADRs are immutable once accepted; supersede with a new one that references the old.

## Style
- Keep docs concise and skimmable (tables, short sections). State what shipped and how it was verified.
- For external-facing prose, apply the built-in **`ai-writing-tropes`** skill.
- Don't duplicate what the code or git history already records; document the *why* and the non-obvious.

## Definition of done for a milestone
Code + tests green (pytest/mypy/ruff, frontend tsc) → build log updated → CLAUDE.md/PROJECT_PLAN adjusted if conventions changed → committed with a clear message → pushed.
