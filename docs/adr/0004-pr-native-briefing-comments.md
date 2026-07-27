# 4. PR-native impact briefings via sticky comments (opt-in)

- **Status:** Accepted
- **Date:** 2026-07-27

## Context

Variorum's PR Impact Briefing (per-file hotspot risk, module ownership / bus
factor, prior test-risk findings) and contradiction checks lived only in the
dashboard — reviewers had to leave the PR to see them. The value is highest *at
the PR, at review time*.

Two delivery mechanisms were considered:

1. **GitHub Check Run** — richer UI, but requires the `checks: write` permission,
   which the App does not currently hold. Adding it forces every installation to
   re-approve expanded permissions.
2. **Issue comment on the PR** — uses the App's existing Pull requests: write
   permission; no re-approval needed.

## Decision

Post the briefing as a **single sticky PR comment**. A hidden HTML marker
(`<!-- variorum:pr-briefing -->`) identifies Variorum's own comment so repeated
runs **update in place** instead of piling up (`upsert_pr_comment` in
`services/pr_comment.py`).

Posting is **opt-in per repository** (`Repository.pr_comments_enabled`, default
false): automatic posting on `pull_request` webhooks happens only when enabled,
since posting is outward-facing. A manual endpoint
(`POST /repositories/{id}/pr-comment/{pr_number}`) posts on the owner's explicit
action regardless of the flag. The webhook enqueues the comment job **after**
drift + risk analysis (BackgroundTasks run sequentially), so the comment reflects
their findings. The job is best-effort and never crashes the worker.

## Consequences

- Zero new GitHub App permissions and no re-approval; stays within least
  privilege and the $0 constraint.
- Idempotent: one evolving comment per PR, not a stream of duplicates.
- Respects the human-review gate — Variorum posts guidance, never approvals,
  merges, or code changes.
- Trade-off: a Markdown comment is less structured than a Check Run's UI.
  Acceptable for now; a Check Run can be added later behind the same service if
  the permission cost is ever justified.
