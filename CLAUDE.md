# CLAUDE.md — Variorum project memory

This file is the **permanent memory** for any Claude Code session working on
Variorum. Read it first. Every decision must respect this file, `PROJECT_PLAN.md`
(PRD + roadmap + build log), the installed skills (`.claude/skills/`), and
industry best practices.

---

## What Variorum is

An AI-powered **engineering knowledge layer** for GitHub repositories — "the
memory system for software teams." It is **not** a code generator. Three product
surfaces, all built (Phases 0–3 complete):

1. **Documentation Intelligence** — PR changes code → detect doc drift (with
   evidence) → open a doc-fix PR.
2. **Engineering Memory** — ingest commit/PR/issue history → cited Q&A ("why is
   the system this way?"), keyword + semantic.
3. **Testing Intelligence** — PR → risk score + untested scenarios → open a
   test PR.

Each follows the same loop: **detect/answer → propose → human review**. Variorum
proposes; humans merge. It never auto-merges or force-pushes.

---

## 🚫 Hard constraint: $0 cost

Everything must be **free**. Do **not** introduce paid APIs, paid SaaS, paid
infra, or premium plugins. Use open-source tools, free tiers, and local tooling.
The AI providers run on **free-tier keys**; the provider-fallback layer exists so
a single provider's quota/outage never breaks the product. Before adding any
dependency or service, confirm it's free and that it earns its place (no
overengineering, no unnecessary deps).

---

## Tech stack (all free / open-source)

| Area | Choice |
|---|---|
| Backend | FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, Uvicorn |
| DB | PostgreSQL 17 (native, local; role `variorum`) |
| HTTP / auth | httpx, PyJWT[crypto] |
| Code analysis | tree-sitter + tree-sitter-language-pack |
| AI | Provider-agnostic layer over Gemini (×2 keys), DeepSeek, Perplexity — REST via httpx, no vendor SDKs |
| Frontend | Next.js 15 (App Router), React 19, TypeScript (strict), Tailwind v3, shadcn-style components, lucide-react |
| Tooling | ruff, mypy, pytest (backend); eslint, tsc (frontend) |

**Working models** (verified live; free-tier keys reject some models — do not
change without re-verifying via `backend/scripts/check_ai.py`):
`gemini-flash-latest`, `deepseek-v4-flash`, `sonar`. Embeddings:
`gemini-embedding-001` (768-dim).

---

## Repository map

```
backend/app/
  main.py            FastAPI factory (+ security headers, catch-all handler, rate-limit wiring)
  core/              config (pydantic-settings), logging, ratelimit
  db/                engine/session (pooled), declarative base
  models/            SQLAlchemy models + StrEnum enums (incl. RepositoryGuide)
  schemas/           Pydantic request/response
  api/routes/        auth, github, repositories, analysis, teams, system, webhooks
  ai/                provider-agnostic AI layer (base, manager, providers/, service, embeddings, rag)
  services/
    github/          App auth, OAuth, REST client, webhook verify, events, installations
    indexer/         tree-sitter code index, doc discovery, doc↔code linker, archive, pipeline
    analysis/        drift, doc_pr, docfix, pr_context, risk, testgen, test_pr
    knowledge.py, qa.py, symbols.py, documents.py, change_briefing.py, suppressions.py, insights.py, orientation.py, users.py, schedule.py, monitoring.py, pr_comment.py
  workers/           indexing, pr_analysis, risk_analysis, pr_comment, ingest (BackgroundTasks)
backend/alembic/     migrations         backend/tests/     pytest suite (+ conftest, _fakes)
backend/scripts/     check_env.py, check_ai.py     backend/Dockerfile + entrypoint.sh
frontend/src/
  app/               landing + dashboard routes (overview, repositories, repositories/[id],
                     insights, teams, memory)
  components/        ui/, dashboard/ (chrome, sidebar, topbar, provider, charts, finding-cards,
                     command-palette), theme-provider/toggle/themed-toaster, landing/
  lib/               api.ts, utils.ts
docs/adr/            architecture decision records
.claude/skills/      project skills (see below)
```

Read also: `PROJECT_PLAN.md` (full PRD/architecture/build log), `SETUP.md`
(GitHub App + `.env` + demo), `docs/adr/`.

---

## Skills

### Built-in Claude Code skills to use
- **`security-review`** — before merging auth/secrets/GitHub/webhook changes.
- **`code-review` / `review`** — reviewing a working diff / a PR.
- **`simplify`** — tidy a change for reuse/clarity (quality, not bug-hunting).
- **`init`** — regenerate/refresh this file if the project shape changes.
- **`dataviz`** — before building any chart/graph/dashboard viz.
- **`artifact-design`** — standalone shareable HTML artifacts.
- **`ai-writing-tropes`** — external-facing prose.

### Project skills (`.claude/skills/`) — auto-load by topic
| Skill | Use for |
|---|---|
| `variorum-frontend` | Next.js/React/strict-TS, components, API client, `frontend/` |
| `variorum-ui-ux` | design language (Linear/Vercel/GitHub/Stripe), tokens, a11y, responsive |
| `variorum-backend` | FastAPI, API design, SQLAlchemy/Alembic, services/workers |
| `variorum-python` | typing, ruff/mypy/pytest, deps, maintainable Python |
| `variorum-security` | auth/sessions, authz, secrets, GitHub App, webhooks |
| `variorum-testing` | unit/integration/API tests, fixtures, mocking, TDD |
| `variorum-git-github` | branches/commits/PRs, GitHub App dev, repo hygiene |
| `variorum-docs` | maintaining CLAUDE.md/PROJECT_PLAN/ADRs, tracking |

---

## Library decisions (evaluated; all free)

Chosen and *why*, with rejected alternatives — do not re-litigate without reason:

- **FastAPI** over Flask/Django — async, Pydantic-native, great for AI/IO workloads.
- **SQLAlchemy 2.0 + Alembic** over raw SQL / Tortoise — typed models, mature migrations.
- **psycopg (v3)** driver — current, binary wheels.
- **httpx** over `requests`/vendor SDKs — async + sync, one client for GitHub and all AI providers; keeps the dependency surface small and uniformly mockable (`MockTransport`).
- **PyJWT[crypto]** — RS256 App JWTs; standard.
- **tree-sitter + tree-sitter-language-pack** over regex/LLM parsing — deterministic, fast, prebuilt grammars.
- **AI over REST (no vendor SDKs)** — the `AIProvider` interface + `ProviderManager` give free provider swapping/fallback; SDKs would add weight and lock-in.
- **Postgres full-text (tsvector) + embeddings** for semantic search — embeddings are JSONB ranked with in-process cosine by default; an **optional pgvector path** (guarded migration `c7d2f1a9b4e0` + `PGVECTOR_ENABLED`, auto-detected via `pgvector_active()` in `services/qa.py`) uses an indexed `<=>` query when the extension is present, and falls back to JSONB otherwise. `alembic upgrade head` never fails without pgvector.
- **RAG corpus = code + docs + ingested history + synthesized decisions.** `CodeSymbol` (functions/classes), `Document` (title + stored body), `KnowledgeEntry` (commit/PR/issue), and `DecisionEntry` (the "why" timeline) are all embedded (`gemini-embedding-001`, 768-dim) and hybrid-retrieved (semantic ⊕ keyword) in the Q&A. The shared ranking primitive lives in `ai/rag.py` (`cosine`, `top_k_by_cosine`); `services/qa.py` (`retrieve` / `retrieve_decisions` / `retrieve_code` / `retrieve_docs`) blends all four into one cited answer, and **code + doc citations link to the source on GitHub**. Embedding is best-effort at write time with `embed_missing` (knowledge), `embed_missing_decisions`, `embed_missing_symbols` (`services/symbols.py`), and `embed_missing_documents` (`services/documents.py`) backfills, all run after every index job. Symbol retrieval is restricted to real definitions (no `import` rows).
- **Auto-freshness:** a `push` to a connected repo's default branch re-indexes it (and re-embeds symbols) via the webhook, so the code index and its embeddings stay current without a manual re-index. Snapshots are captured on each ingest + by the scheduler (see below).
- **Next.js + Tailwind + shadcn-style** (copy-in components, no heavy UI dep) over MUI/Chakra — matches the dev-tool aesthetic, minimal deps, full control.
- **Rejected / deferred:** Celery/Redis queue (using `BackgroundTasks` for MVP), Supabase (using plain Postgres per PRD), numpy (pure-Python cosine avoids the dep), vendor AI SDKs.

Add a dependency only when it clearly beats the above and is free.

---

## Conventions (enforced)

- **Code style:** self-documenting names; comments explain *why*, never restate code. Python line length 100; `from __future__ import annotations`; `StrEnum` enums.
- **Green gate before commit:** `ruff check .` + `mypy app` + `pytest` (backend) and `tsc --noEmit` + `npm run lint` (frontend) must pass. Every feature ships with tests.
- **Security:** ownership-scope every resource; never commit/log secrets; least-privilege GitHub App (Contents/PR R/W, Issues read, Metadata); verify webhook HMAC; human-review gate on generated PRs. Production posture: fail-fast config validation (`config.production_security_issues`), security headers + HSTS, generic client errors + catch-all handler, in-process rate limiting (`core/ratelimit`), configurable session-cookie SameSite; `/health/ready` DB-readiness probe. (See `variorum-security`, `SECURITY.md`.)
- **Git:** conventional commits with the Co-Authored-By trailer; confirm `.env`/secrets are git-ignored before committing. (See `variorum-git-github`.)
- **Docs:** update the `PROJECT_PLAN.md` build log + this file when milestones land or conventions change.

---

## Local dev

Primary DB is **native PostgreSQL on port 5432** (role `variorum`; the Docker DB
in `docker-compose.yml` is an alternative on **5433** to avoid clashing). `.env`
at repo root (git-ignored) holds all config; `.env.example` documents it.

```bash
# verify config + providers
cd backend && ./.venv/Scripts/python.exe scripts/check_env.py
cd backend && ./.venv/Scripts/python.exe scripts/check_ai.py
# run both services (Windows)
powershell -ExecutionPolicy Bypass -File scripts/start-all.ps1
# backend http://localhost:8000/docs   frontend http://localhost:3000/dashboard
```

### Gotchas (learned the hard way)
- **Never run `next build` while `next dev` is running** — it corrupts the shared `.next`. Verify with `tsc --noEmit` + `npm run lint`.
- After editing `.env`, **restart the backend** (settings are read once at startup).
- The **in-process scheduler** is a FastAPI-lifespan loop (`app/main.py`), gated by `SCHEDULER_ENABLED` (default on; off in tests). Each tick (a) sends due weekly digests (`services/schedule.py` → Slack, only when a `DigestSchedule` is due *and* the owner has a webhook) and (b) captures stale metric snapshots (`services/monitoring.py.capture_stale`, ≥12h apart per indexed repo). Single-instance only — a durable scheduler is the production upgrade (same posture as `BackgroundTasks`).
- **Metric snapshots & alerts** (`services/monitoring.py`): `MetricSnapshot` is a point-in-time capture of health/coverage/ownership/hotspot/finding counts; captured after each ingest, on `POST …/snapshot`, and by the scheduler. Trends read the series; `detect_alerts` diffs consecutive snapshots (health drop / new critical hotspot / single-owner rise) into `Alert` rows surfaced in the topbar bell. Alerts are in-app only (no Slack).
- Shared PG enum in a new table's migration → set `create_type=False`.
- Free-tier AI keys reject some model names (404) and rate-limit (429/503) — rely on the fallback chain; re-verify models with `check_ai.py`.
- Don't import `test_*`-named functions into test modules (pytest collects them) — alias.
