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
  main.py            FastAPI factory
  core/              config (pydantic-settings), logging
  db/                engine/session, declarative base
  models/            SQLAlchemy models + StrEnum enums
  schemas/           Pydantic request/response
  api/routes/        auth, github, repositories, analysis, system, webhooks
  ai/                provider-agnostic AI layer (base, manager, providers/, service, embeddings)
  services/
    github/          App auth, OAuth, REST client, webhook verify, events, installations
    indexer/         tree-sitter code index, doc discovery, doc↔code linker, archive, pipeline
    analysis/        drift, doc_pr, docfix, pr_context, risk, testgen, test_pr
    knowledge.py, qa.py, users.py
  workers/           indexing, pr_analysis, risk_analysis, ingest (BackgroundTasks)
backend/alembic/     migrations         backend/tests/     pytest suite (+ conftest, _fakes)
backend/scripts/     check_env.py, check_ai.py
frontend/src/        app/ (routes), components/ (+ ui/), lib/ (api.ts, utils.ts)
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
- **Postgres full-text (tsvector) + in-process cosine** for semantic search — **pgvector is the intended production store but is not installed on the native PG**, so embeddings are JSONB ranked in Python (fine at this scale). Upgrade path documented in `PROJECT_PLAN.md`.
- **Next.js + Tailwind + shadcn-style** (copy-in components, no heavy UI dep) over MUI/Chakra — matches the dev-tool aesthetic, minimal deps, full control.
- **Rejected / deferred:** Celery/Redis queue (using `BackgroundTasks` for MVP), Supabase (using plain Postgres per PRD), numpy (pure-Python cosine avoids the dep), vendor AI SDKs.

Add a dependency only when it clearly beats the above and is free.

---

## Conventions (enforced)

- **Code style:** self-documenting names; comments explain *why*, never restate code. Python line length 100; `from __future__ import annotations`; `StrEnum` enums.
- **Green gate before commit:** `ruff check .` + `mypy app` + `pytest` (backend) and `tsc --noEmit` + `npm run lint` (frontend) must pass. Every feature ships with tests.
- **Security:** ownership-scope every resource; never commit/log secrets; least-privilege GitHub App; verify webhook HMAC; human-review gate on generated PRs. (See `variorum-security`.)
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
- Shared PG enum in a new table's migration → set `create_type=False`.
- Free-tier AI keys reject some model names (404) and rate-limit (429/503) — rely on the fallback chain; re-verify models with `check_ai.py`.
- Don't import `test_*`-named functions into test modules (pytest collects them) — alias.
