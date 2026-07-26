# Variorum — Final Production Audit

_Last updated: 2026-07-26. Pre-launch engineering review across security, code
quality, documentation, deployment, and product._

## Executive summary

Variorum is a mature, well-architected product. All three PRD surfaces
(Documentation Intelligence, Engineering Memory, Testing Intelligence) plus
repository/team insights, optional pgvector semantic search, and a new
**Repository Orientation** feature are implemented, tested, and consistent with a
"propose → human review" model that never auto-merges or force-pushes.

This audit ran three parallel reviews (security-adjacent code quality,
documentation accuracy, deployment readiness), applied the high-value fixes,
shipped one new production feature, reconciled the documentation, and added a
deployment guide and a container image.

**Verdict: READY FOR PRODUCTION** as a single always-on backend instance behind
HTTPS with the documented configuration. Horizontal scale requires the deferred
durable-queue work (documented). No blocking security or correctness issues
remain.

## Security review

**Verified sound (unchanged):** strict CORS allowlist; `HttpOnly` + conditional
`Secure` session cookies; constant-time webhook HMAC; consistent ownership
scoping (cross-tenant → 404); no SQL injection (ORM/parameterized only); no
`eval`/`exec`; AI output parsed/validated, never executed; installation tokens
in-memory only; no secrets in logs or the repository (`.env`, `*.pem`, `*.key`,
`secrets/` gitignored; `git ls-files` clean).

**Hardened in this pass:**
- Configurable session-cookie `SameSite` (`SESSION_COOKIE_SAMESITE`) so
  split-domain deploys can use `None; Secure` without code changes.
- Input validation constraints on request models (`pr_number > 0`, bounded
  `head_sha`, `question` length) to reject malformed input at the edge.
- Malformed-AI-JSON now returns a clean `502` (was an unhandled `500`) on the
  synchronous `ask` and `orientation` paths.

**Confirmed from earlier passes:** fail-fast production config validation,
security-headers middleware + HSTS, generic client errors + catch-all handler,
in-process rate limiting, defense-in-depth path-traversal guard on generated
writes, and the documented AI data-flow (diffs sent to providers over TLS).

## Code quality review

- **New feature is fully wired** (model → migration → service → endpoints →
  frontend → tests); not dead code.
- **Removed dead code:** unused `AIService.complete_json`; unused frontend API
  client methods (`health`, `installations`, `analyzeRisk`) and their interfaces.
- **Fixed a real theme bug:** dashboard charts hardcoded dark colors and rendered
  wrong in light mode; tooltips/axes/cursors now use CSS variables.
- **Correctness/logging:** risk-worker per-file failure log now records the real
  PR number; stale webhook-dispatch comment corrected.
- **Consciously deferred** (tracked in "Remaining risks", low risk, not blocking):
  extracting the shared PR-creation error/branch helpers (`analysis.py`,
  `doc_pr.py`/`test_pr.py`), a `RiskFindingStatus` enum, persisting risk
  "PR-opened" state, and minor frontend DRY (shared `TabButton`, severity-slice
  helper, polling util). These are maintainability polish on tested paths; the
  mandate was to avoid unnecessary rewrites before launch.

Linters/type-checkers are clean: `ruff`, `mypy` (backend); `eslint`, `tsc`
(frontend).

## Documentation review

Reconciled to the current implementation:
- **README.md** — added Repository Orientation + insights/teams to features;
  corrected the roadmap (shipped vs. next); fixed the structure map; linked the
  deployment guide.
- **PROJECT_PLAN.md** — status line, roadmap table, GitHub App permissions (added
  Issues: Read), pgvector wording (now optional-with-fallback), "no semantic
  search" limitation removed, and a post-MVP build-log section.
- **CLAUDE.md** — repository map (teams route, `insights.py`, `orientation.py`,
  `ratelimit.py`, Dockerfile, new frontend files), pgvector wording, and the
  production security posture.
- **.env.example** — documented `SESSION_COOKIE_SAMESITE`, `RATE_LIMIT_ENABLED`,
  `PGVECTOR_ENABLED`, and the DB pool variables.
- **New:** `PRODUCTION_DEPLOYMENT_GUIDE.md`. `SECURITY.md`, `CONTRIBUTING.md`,
  `PRODUCTION_CHECKLIST.md`, and the ADRs were verified accurate.

## Testing results

- **Backend:** full `pytest` suite green (155 tests incl. new orientation and
  insights/teams coverage), `ruff` and `mypy` clean.
- **Frontend:** `tsc --noEmit` and `eslint` clean; production `next build`
  succeeds for all 10 routes (including the new `teams` and `repositories/[id]`).
- **Live smoke:** backend boots with security headers + rate limiting active;
  new endpoints (`/teams`, `/repositories/{id}/insights`, `/orientation`) return
  `401` unauthenticated and are present in OpenAPI; landing + dashboard routes
  render.

## Deployment readiness

- Backend `Dockerfile` + `entrypoint.sh` (migrate then serve, honors `$PORT` and
  `WEB_CONCURRENCY`); DB pool tuning; `/health` + `/api/v1/system/status` for
  probes; fail-fast on insecure production config.
- Guarded pgvector migration is safe on any PostgreSQL.
- The cross-origin cookie/CORS decision is documented with two clear options.

**Ready** for a single always-on backend + managed Postgres + HTTPS frontend.

## Remaining risks (future attention, non-blocking)

1. **Horizontal scale needs a durable queue** — in-process `BackgroundTasks`
   don't survive restarts or span replicas; deploy single-instance until the
   queue lands. (Documented.)
2. **In-process rate limiter** is per-process; add an edge/shared limiter for
   multi-replica.
3. **`npm audit`** flags advisories in Next.js's *bundled* transitive deps
   (`postcss`, `sharp`). Investigated: upgrading to the latest 15.x (15.5.22)
   does **not** clear them — those versions ship the same bundled deps, and
   npm's only offered "fix" is a nonsensical downgrade to `next@9`. Both are
   non-exploitable here (postcss runs at build time on our own CSS; `next/image`
   isn't used with untrusted images). **Accepted** on Next `15.1.4` until an
   upstream Next release updates the bundled deps; revisit on the next major
   Next upgrade.
4. **Deferred refactors** (PR-flow dedup, risk-status enum, risk PR-opened state,
   frontend DRY) — maintainability polish, best done as isolated reviewed PRs.

## New feature: Repository Orientation

**Problem.** New engineers spend weeks reverse-engineering an unfamiliar
repository — what it is, how it fits together, where to start, and *why* it's
built this way.

**Why existing tools fail.** Copilot/Cursor/Claude Code operate on the code in
front of them; they don't ingest and retain a repository's commit/PR/issue
history or maintain a persistent structural map, so they can't ground a
"why/where to start" tour in real project history with citations.

**Why Variorum can.** It already indexes code (tree-sitter), discovers
documentation, and ingests engineering history into a knowledge store. Orientation
**fuses these three signals** into a single cited onboarding guide.

**Implementation.** `RepositoryGuide` model + migration `d5b8e3c07f21`;
`services/orientation.py` assembles a compact, bounded context (languages,
top-level modules, key docs, recent history) and asks the AI for strict-JSON
output (summary, key areas with paths, where-to-start, cited decisions,
conventions), parsed defensively; `GET`/`POST /repositories/{id}/orientation`
(owner-scoped, AI-guarded, regenerate-in-place); an Orientation card on the repo
detail page. Fully tested.

**Business value.** Faster onboarding, a living "why" for the codebase, and a
differentiated capability that leverages Variorum's unique cross-history +
code + docs understanding.

### Other strong candidates (proposed, not built)

- **Knowledge Ownership / Bus-Factor Map** — from authorship in ingested history,
  surface per-area expertise and dangerous single-owner concentration. Needs
  per-file authorship (extra history data); higher build cost.
- **Decision Ledger / Software-Evolution Timeline** — a synthesized, cited
  narrative of how the architecture evolved and why. Natural next step on top of
  Engineering Memory.
