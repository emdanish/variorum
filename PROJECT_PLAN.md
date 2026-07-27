# Variorum — Engineering Knowledge Infrastructure

> **Variorum** *(n.)* — an edition of a text annotated with notes and variant
> readings gathered from many sources. Variorum does the same for a codebase:
> it keeps the *context* around the code — the decisions, history, and rationale —
> alive and current.

This document is the single source of truth for the project. Any engineer (human
or agent) joining with zero prior context should be able to read this file and
understand **what** we are building, **why**, **how**, **what is done**, and
**what remains**.

- **Status:** All phases (0–3) shipped. Post-MVP: repository & team insights,
  optional pgvector semantic search (auto-detected, with fallback), repository
  orientation (onboarding guides), and a security/production-hardening pass —
  all landed. See the build log at the end of this file.
- **Last updated:** 2026-07-26
- **Owner:** ai-team@elementaltv.com

---

## Table of contents

1. [Product Requirements Document (PRD)](#1-product-requirements-document-prd)
2. [Product vision](#2-product-vision)
3. [Problem statement](#3-problem-statement)
4. [Target users](#4-target-users)
5. [User personas](#5-user-personas)
6. [Product goals](#6-product-goals)
7. [Non-goals](#7-non-goals)
8. [Complete feature list](#8-complete-feature-list)
9. [Product roadmap](#9-product-roadmap)
10. [Phase breakdown](#10-phase-breakdown)
11. [Technical architecture](#11-technical-architecture)
12. [Database design](#12-database-design)
13. [API design](#13-api-design)
14. [Folder structure](#14-folder-structure)
15. [Development milestones](#15-development-milestones)
16. [Testing strategy](#16-testing-strategy)
17. [Security considerations](#17-security-considerations)
18. [Deployment strategy](#18-deployment-strategy)
19. [Future scalability plan](#19-future-scalability-plan)
20. [Known limitations](#20-known-limitations)
21. [Build log — what is done / what remains](#21-build-log)

---

## 1. Product Requirements Document (PRD)

**Product name:** Variorum

**One-liner:** The memory system for software teams — an AI-powered engineering
knowledge layer that continuously understands a repository and keeps the context
around the code accurate over time.

**Category:** Developer tooling / DevInfra SaaS.

**What it is:** A GitHub App + web application that connects to a team's
repositories, builds a structural + semantic understanding of the code, watches
pull requests, and (Phase 1) detects when documentation has drifted out of sync
with the code, then proposes documentation fixes as reviewable pull requests.

**What it is not:** A code generator, a ChatGPT wrapper, or a replacement for
Copilot/Cursor/Claude Code. Those answer *"what code should I write?"* Variorum
answers *"why does this code exist and how does the whole system fit together?"*

**Primary MVP outcome (Phase 1):** Prove the loop —
connect repo → understand code → detect doc drift on a PR → open a doc-fix PR that
a human reviews and merges.

**Success criteria for MVP:**

- A user can sign up, install the GitHub App, and select repositories.
- On repository connect, Variorum indexes the repo structure (files, symbols) and
  discovers documentation.
- On a new pull request, Variorum analyzes changed files against related docs and
  produces a drift assessment with **evidence** (file paths, symbols, diff hunks).
- When drift is found, Variorum can open a pull request updating the docs.
- Every claim Variorum makes cites its source. No unsupported assertions.

---

## 2. Product vision

Create an AI-powered engineering knowledge layer that continuously understands a
software repository and becomes **the memory system for software teams**.

It helps teams answer, with evidence:

- **What exists?** (structure, components, ownership)
- **Why does it exist?** (decisions, trade-offs, historical rationale)
- **How does it work?** (data flow, relationships, dependencies)
- **What changed?** (impact of a diff, affected docs and tests)
- **What might break?** (risk surface, missing coverage)

The knowledge layer is derived from the artifacts teams already produce — commits,
PRs, issues, reviews, docs, and code — so it stays current without extra manual
upkeep.

---

## 3. Problem statement

Code is not a team's only valuable asset; the **context around the code** is
equally valuable and far more fragile. Today that context is scattered across
commits, PRs, issues, reviews, docs, chat, and the memory of senior engineers.

As teams grow and engineers leave, this context evaporates. Concrete symptoms:

- Documentation silently becomes wrong after a refactor (e.g. auth moves from
  session cookies to JWT, but the auth guide still describes cookies).
- New engineers can't find *why* an unusual workaround exists.
- Nobody remembers which decision a given architecture came from.
- High-risk areas of the system are invisible until they break.

Variorum targets the highest-frequency, most measurable slice of this problem
first: **documentation drift** (Phase 1), then broadens to engineering memory
(Phase 2) and testing intelligence (Phase 3).

---

## 4. Target users

- **Primary:** Small-to-mid engineering teams (5–50 engineers) on GitHub who care
  about documentation and onboarding but can't afford dedicated tech-writer time.
- **Secondary:** Fast-growing startups experiencing knowledge loss from turnover.
- **Tertiary:** Open-source maintainers who want docs to stay in sync with code.

**Buyer:** Engineering manager, staff/principal engineer, or head of engineering.
**Daily user:** Any developer opening PRs.

---

## 5. User personas

**Priya — Staff Engineer / knowledge owner.** Answers the same "why is it like
this?" questions repeatedly. Wants that knowledge captured with evidence so she
stops being a human cache. Trusts a tool only if every claim is traceable.

**Marcus — Engineering Manager / buyer.** Feels onboarding pain and audit risk
from stale docs. Wants a low-friction install, no new developer workflow, and
clear signal that the tool reduces knowledge loss.

**Ava — New Backend Engineer.** Two weeks in. Needs to know *why* Redis queues
exist and where a business rule lives, without interrupting senior engineers.

**Sam — OSS Maintainer.** Overwhelmed by PRs. Wants docs to update themselves as
reviewable PRs so contributors and users aren't misled.

---

## 6. Product goals

1. **Zero new workflow.** Value delivered inside the existing GitHub PR flow.
2. **Evidence-first.** Every statement cites files, symbols, commits, or PRs.
3. **Human-in-the-loop.** Variorum proposes; humans approve. It never force-pushes
   to protected branches or merges on its own.
4. **Provider-agnostic AI.** No lock-in to a single model vendor; automatic
   fallback across providers.
5. **Scale-aware analysis.** Never send whole repos blindly to a model; select
   relevant context via structural indexing.
6. **Production quality.** Clean architecture, migrations, tests, security.

---

## 7. Non-goals

- Not a code-generation assistant or IDE plugin (Phase 1–3).
- Not a general chatbot.
- Not a hosted git provider or a replacement for GitHub.
- Not auto-merging changes into protected branches.
- Not supporting non-GitHub providers in the MVP (GitLab/Bitbucket are future).
- Not building our own foundation models; we orchestrate third-party providers.
- No fine-tuning in the MVP.

---

## 8. Complete feature list

**Phase 1 — Documentation Intelligence (MVP)**
- Account creation & auth (session-based app auth).
- GitHub App installation flow + repository selection.
- Repository ingestion: clone/read via GitHub App token, structural index
  (Tree-sitter) of files, functions, classes, imports.
- Documentation discovery (Markdown, docs/, READMEs, docstrings).
- Webhook ingestion for `pull_request` and `push` events.
- PR analysis: map changed code → related docs → drift assessment with evidence.
- Doc-fix generation: produce updated doc content + a pull request.
- Dashboard: repositories, analysis jobs, detected drift, generated PRs.

**Phase 2 — Engineering Memory**
- Ingest commits, PRs, issues, reviews into a knowledge store.
- Q&A over the knowledge store ("Why do we use Redis queues?") with citations.
- Decision timeline per subsystem.

**Phase 3 — AI Testing Intelligence**
- Risk scoring of changed files.
- Coverage gap detection against existing tests.
- Test-PR generation, verified through the repo's existing CI.

---

## 9. Product roadmap

| Phase | Theme | Outcome | Target |
|------:|-------|---------|--------|
| 0 | Foundation | Repo, architecture, AI layer, GitHub App skeleton, DB schema | ✅ shipped |
| 1 | Documentation Intelligence (MVP) | Doc-drift detection → doc-fix PRs | ✅ shipped |
| 2 | Engineering Memory | Evidence-cited Q&A over repo history | ✅ shipped |
| 3 | Testing Intelligence | Risk + coverage → test PRs | ✅ shipped |
| + | Insights & Teams | Repo/team analytics rollups | ✅ shipped |
| + | Semantic search at scale | Optional pgvector, auto-detected + fallback | ✅ shipped |
| + | Repository Orientation | Cited onboarding guides | ✅ shipped |

---

## 10. Phase breakdown

### Phase 0 — Foundation (current)
Monorepo scaffold; FastAPI backend; Next.js frontend; PostgreSQL 17 + Alembic;
AI provider abstraction with fallback (Gemini×2 → DeepSeek → Perplexity); GitHub
App auth (JWT → installation token); webhook receiver with signature verification;
core data model.

### Phase 1 — Documentation Intelligence (MVP)
1. **Connect:** installation → select repos → persist installation & repos.
2. **Understand:** background ingestion → Tree-sitter structural index → doc map.
3. **Detect:** on `pull_request`, compute changed symbols → find related docs →
   ask AI (with tight, relevant context) whether docs drifted → structured verdict
   with evidence.
4. **Propose:** if drift, generate updated doc content → create branch → commit →
   open PR referencing the triggering PR.
5. **Observe:** dashboard surfaces jobs, verdicts, and generated PRs.

### Phase 2 — Engineering Memory
History ingestion pipeline; knowledge entries with source links; retrieval
(keyword first, `pgvector` semantic search later); cited answers.

### Phase 3 — Testing Intelligence
Risk model over churn + centrality; coverage gap analysis; test generation;
CI-verified test PRs.

---

## 11. Technical architecture

```
                          ┌───────────────────────────┐
                          │        GitHub              │
                          │  App · Webhooks · REST/Git │
                          └────────────┬──────────────┘
                                       │ webhooks / API
                    ┌──────────────────▼───────────────────┐
                    │            Backend (FastAPI)          │
   Browser  ─────►  │  API  ·  Webhook receiver  ·  Workers │
   (Next.js)        │                                       │
                    │  ┌─────────────────────────────────┐  │
                    │  │  Services                        │  │
                    │  │  · GitHub (App auth, PRs, git)   │  │
                    │  │  · Indexer (Tree-sitter)         │  │
                    │  │  · Doc-drift analyzer            │  │
                    │  └─────────────────────────────────┘  │
                    │  ┌─────────────────────────────────┐  │
                    │  │  AI Service Layer                │  │
                    │  │  ProviderManager → fallback      │  │
                    │  │  Gemini1·Gemini2·DeepSeek·Pplx   │  │
                    │  └─────────────────────────────────┘  │
                    └──────────────┬────────────────────────┘
                                   │ SQLAlchemy
                          ┌────────▼─────────┐
                          │  PostgreSQL 17   │
                          │  (+ pgvector L8) │
                          └──────────────────┘
```

**Key decisions**
- **Split frontend/backend.** Next.js (Vercel) for UI; FastAPI (Python) for the
  AI/code-analysis heavy lifting where the ecosystem (Tree-sitter, provider SDKs)
  is strongest.
- **AI abstraction is mandatory.** Application code depends on an `AIService`
  interface, never on a concrete provider. `ProviderManager` handles ordering,
  quota/error detection, and fallback.
- **Structural indexing before LLMs.** Tree-sitter extracts symbols and
  relationships deterministically; LLMs receive only selected, relevant context.
- **Async background work.** Ingestion and PR analysis run as background jobs
  (FastAPI `BackgroundTasks` for the MVP; pluggable to a real queue later).
- **Evidence is a first-class data type.** Every AI verdict carries structured
  citations persisted alongside the result.

---

## 12. Database design

PostgreSQL 17. Migrations via Alembic. Core tables (Phase 0/1):

- **users** — `id`, `email` (unique), `name`, `avatar_url`, `github_user_id`,
  `created_at`, `updated_at`.
- **github_installations** — `id`, `installation_id` (unique, from GitHub),
  `account_login`, `account_type`, `owner_user_id → users`, `created_at`,
  `suspended_at`.
- **repositories** — `id`, `installation_id → github_installations`,
  `github_repo_id` (unique), `full_name`, `default_branch`, `private`,
  `indexing_status` (enum), `last_indexed_at`, `created_at`.
- **code_symbols** — `id`, `repository_id → repositories`, `path`, `language`,
  `kind` (function/class/method/…), `name`, `start_line`, `end_line`,
  `signature`, `updated_at`. Index on `(repository_id, path)`.
- **documents** — `id`, `repository_id`, `path`, `kind` (markdown/docstring/…),
  `title`, `content_hash`, `updated_at`.
- **doc_code_links** — `id`, `document_id → documents`,
  `symbol_id → code_symbols` (nullable), `path` (fallback link target),
  `confidence`, `source` (heuristic/ai). Association of docs ↔ code.
- **analysis_jobs** — `id`, `repository_id`, `type` (index/pr_analysis),
  `status` (queued/running/succeeded/failed), `trigger` (webhook/manual),
  `external_ref` (PR number / delivery id), `error`, `created_at`,
  `started_at`, `finished_at`.
- **drift_findings** — `id`, `analysis_job_id → analysis_jobs`, `document_id`,
  `severity` (info/low/medium/high), `summary`, `evidence` (JSONB: file paths,
  symbols, diff hunks, provider, model), `status`
  (detected/pr_opened/dismissed), `created_at`.
- **generated_prs** — `id`, `drift_finding_id`, `repository_id`, `pr_number`,
  `branch`, `url`, `state`, `created_at`.
- **provider_calls** *(observability)* — `id`, `provider`, `model`, `purpose`,
  `success`, `latency_ms`, `error_kind`, `created_at`.

**Phase 2 additions:** `knowledge_entries`, `entry_sources`, plus `pgvector`
embedding columns for semantic retrieval.

Enum types live in the DB; SQLAlchemy models mirror them. See
`backend/app/models/`.

---

## 13. API design

REST, JSON, versioned under `/api/v1`. Selected endpoints:

**Auth & health**
- `GET  /health` — liveness.
- `GET  /api/v1/auth/me` — current user.
- `POST /api/v1/auth/logout`.

**GitHub**
- `GET  /api/v1/github/install-url` — where to send the user to install the App.
- `GET  /api/v1/github/installations` — installations for the user.
- `GET  /api/v1/github/installations/{id}/repositories` — selectable repos.
- `POST /api/v1/repositories/{id}/connect` — begin ingestion.
- `POST /webhooks/github` — GitHub webhook receiver (signature-verified).

**Repositories & analysis**
- `GET  /api/v1/repositories` — connected repos + status.
- `GET  /api/v1/repositories/{id}` — detail (symbols/docs summary).
- `GET  /api/v1/repositories/{id}/jobs` — analysis jobs.
- `GET  /api/v1/jobs/{id}` — job detail incl. findings.
- `GET  /api/v1/findings/{id}` — drift finding + evidence.
- `POST /api/v1/findings/{id}/open-pr` — generate a doc-fix PR.

**Conventions:** Pydantic request/response schemas; consistent error envelope
`{ "error": { "code", "message", "details" } }`; cursor pagination on lists;
idempotent webhook handling keyed on delivery id.

---

## 14. Folder structure

```
variorum/
├─ PROJECT_PLAN.md            # this file — kept current
├─ README.md
├─ .gitignore
├─ .env.example               # documented; real .env is git-ignored
├─ docker-compose.yml         # local PostgreSQL 17 (+ pgvector image)
├─ Makefile                   # common dev commands
├─ docs/
│  └─ adr/                     # architecture decision records
├─ scripts/                    # dev/setup scripts
├─ backend/
│  ├─ pyproject.toml
│  ├─ requirements.txt
│  ├─ alembic.ini
│  ├─ alembic/                 # migrations
│  ├─ app/
│  │  ├─ main.py               # FastAPI app factory
│  │  ├─ core/                 # config, logging, security
│  │  ├─ db/                   # engine, session, base
│  │  ├─ models/               # SQLAlchemy models
│  │  ├─ schemas/              # Pydantic schemas
│  │  ├─ api/                  # routers (v1) + deps
│  │  ├─ ai/                   # AI abstraction + providers + fallback
│  │  ├─ services/             # github, indexer, analyzer
│  │  └─ workers/              # background jobs
│  └─ tests/
└─ frontend/
   ├─ package.json
   ├─ next.config.mjs
   ├─ tailwind.config.ts
   ├─ tsconfig.json
   └─ src/
      ├─ app/                  # Next.js App Router
      ├─ components/           # UI + shadcn/ui
      └─ lib/                  # api client, utils
```

---

## 15. Development milestones

- **M0 — Foundation (Phase 0):** scaffold, config, DB models + first migration,
  AI provider layer with fallback + tests, GitHub App auth + webhook verify,
  runnable backend, Next.js shell. *(current)*
- **M1 — Connect:** installation callback, repo listing/selection, persistence,
  dashboard listing.
- **M2 — Understand:** ingestion worker, Tree-sitter index, doc discovery,
  doc↔code linking.
- **M3 — Detect:** PR webhook → analysis job → doc-drift verdict with evidence.
- **M4 — Propose:** doc-fix generation → branch/commit/PR via GitHub App.
- **M5 — Polish:** dashboard UX, error handling, observability, docs.

---

## 16. Testing strategy

- **Unit:** AI `ProviderManager` fallback ordering and error classification
  (mock providers — no network); config loading; GitHub webhook signature
  verification; Tree-sitter extraction on fixture files; prompt/context builders.
- **Integration:** API routes against a test PostgreSQL (transactional
  rollback per test); webhook receiver end-to-end with signed fixtures; GitHub
  service against recorded/mocked HTTP.
- **Contract:** Pydantic schema round-trips for API responses.
- **Frontend:** component tests for key views; typ/lint in CI.
- **CI gates:** `ruff` + `mypy` + `pytest` (backend); `eslint` + `tsc` +
  build (frontend). No feature is "done" until its tests pass locally and edge
  cases (missing keys, quota errors, malformed webhooks) are handled.
- **Golden rule:** never claim something works without running it.

---

## 17. Security considerations

- **Secrets:** never hardcoded; loaded from environment (`.env` git-ignored).
  `.env.example` documents required keys. GitHub App private key stored as a file
  path or base64 env var, never committed.
- **Webhooks:** verify `X-Hub-Signature-256` HMAC before processing; reject on
  mismatch; idempotency on delivery id.
- **GitHub tokens:** short-lived installation tokens minted on demand from the
  App JWT; least-privilege permission set; never logged.
- **AuthN/Z:** users only see their own installations/repos; server-side checks
  on every resource.
- **Least privilege GitHub App:** Contents (read/write for doc/test PRs), Pull
  requests (read/write), Issues (read, for history ingestion), Metadata (read),
  Webhooks. No admin scopes.
- **Human-in-the-loop:** generated changes land as PRs on non-protected branches;
  never auto-merge; never force-push.
- **Data handling:** send only selected, relevant code context to AI providers;
  log provider *metadata* (latency, success), not payloads.
- **Transport:** HTTPS everywhere; HSTS in production.
- **Input validation:** Pydantic at all boundaries.

---

## 18. Deployment strategy

- **Frontend:** Vercel (Next.js). Env vars via Vercel project settings.
- **Backend:** containerized FastAPI (Uvicorn/Gunicorn) on a container host
  (Fly.io / Render / Cloud Run acceptable); horizontal scale for API, separate
  worker process for background jobs.
- **Database:** managed PostgreSQL 17 (with `pgvector` when Phase 2 lands);
  migrations run on deploy via Alembic.
- **Config/secrets:** platform secret stores; distinct dev/staging/prod projects
  and GitHub Apps.
- **Local dev:** `docker-compose up` for PostgreSQL; backend via Uvicorn reload;
  frontend via `next dev`; GitHub webhooks tunneled (smee.io / cloudflared).
- **CI/CD:** GitHub Actions — lint/type/test on PR; deploy on merge to `main`.

---

## 19. Future scalability plan

- **Queue:** swap FastAPI `BackgroundTasks` for a durable queue (Redis/RQ, Celery,
  or a hosted queue) as ingestion volume grows.
- **Indexing at scale:** incremental re-index on diff (only changed files);
  content-hash caching; per-repo symbol store; shard large monorepos.
- **Semantic search:** `pgvector` with IVFFlat/HNSW indexes; batched embeddings
  with the same provider-abstraction + fallback pattern.
- **AI cost/latency:** response caching keyed on prompt+context hash; tiered
  routing (cheap model for triage, stronger model for generation); token
  budgeting per repo.
- **Multi-tenant:** row-level ownership now; org/team model and RBAC later.
- **Provider growth:** the `AIProvider` interface makes adding vendors additive.

---

## 20. Known limitations

- MVP supports **GitHub only**.
- Background work uses in-process `BackgroundTasks` — fine for MVP scale, not for
  high concurrency; documented as a deliberate trade-off.
- Doc-drift detection is heuristic + LLM-assisted; it proposes, humans decide.
  False positives are expected and mitigated by the review gate.
- Semantic search shipped (Phase 2): hybrid keyword + embedding retrieval, with an
  optional pgvector-accelerated path (auto-detected, `PGVECTOR_ENABLED`) that
  falls back to in-process cosine.
- Tree-sitter language coverage is limited to the grammars we bundle (start with
  Python, JS/TS; expand incrementally).
- Requires at least one working AI provider key; with none configured, analysis
  endpoints degrade gracefully and report a clear error.

---

## 21. Build log

Kept current as work lands. Newest first.

### Phase 0 — Foundation (complete)
- [x] Verified empty repo; confirmed toolchain (Node 24, Python 3.13, PG17,
      Docker).
- [x] Authored `PROJECT_PLAN.md`.
- [x] Root scaffold: `.gitignore`, `.env.example`, `docker-compose.yml`,
      `Makefile`, `README.md`.
- [x] Backend foundation: config, logging, DB session/base, 10 SQLAlchemy
      models, first Alembic migration (applied to PG17), FastAPI app + `/health`.
- [x] AI service layer: `AIProvider` interface, Gemini/DeepSeek/Perplexity
      providers, `ProviderManager` fallback + unit tests.
- [x] GitHub service: App JWT → installation token; webhook signature verify.
- [x] Frontend shell: Next.js 15 + Tailwind, landing + dashboard (production
      build passes).
- [x] Verification: 23 backend tests pass, ruff clean, ORM round-trip against
      live PostgreSQL, frontend `next build` succeeds.
- [x] Commit + push foundation.

**Local dev note:** the primary local DB is a **native PostgreSQL on 5432**
(role `variorum`). The bundled Docker PostgreSQL is an alternative published on
host port **5433** to avoid clashing with the native server.

### M1 — Connect (complete)
- [x] GitHub OAuth (user-to-server) login: authorize → callback → user upsert →
      session cookie; `/auth/me`, `/auth/logout`.
- [x] Session-based `get_current_user` / `get_optional_user` dependencies.
- [x] Installation-scoped GitHub REST client (App JWT + installation token),
      with injectable transport for testing.
- [x] Installation + repository persistence (upsert / prune / remove) and
      API-driven sync.
- [x] App setup-URL callback: links installation to the logged-in user and syncs
      repositories.
- [x] Webhook handlers for `installation` and `installation_repositories`
      (idempotent), plus acknowledgement of `pull_request`/`push` (M3).
- [x] User-scoped repositories API + `POST /repositories/{id}/connect` to queue
      indexing.
- [x] Frontend: Sign in with GitHub, auth-aware dashboard, connect flow, per-repo
      index action, post-install banner.
- [x] Tests: OAuth URL building, GitHub client (mocked transport + pagination),
      installation/repo persistence, webhook event routing, auth-scoped API —
      **48 tests**, mypy + ruff clean, frontend build passes.

### M2 — Understand (complete)
- [x] Tree-sitter structural indexer for Python/JS/TS/TSX: extracts functions,
      classes, methods, interfaces, and imports with line ranges + signatures;
      skips vendored dirs and oversized files.
- [x] Documentation discovery (Markdown/RST) with titles and content hashes.
- [x] Heuristic doc↔code linking (file-path and symbol-name mentions) with
      confidence + evidence, persisted as `doc_code_links`.
- [x] Repository archive fetch via installation token (tarball download +
      safe extraction).
- [x] Idempotent persistence pipeline (`reindex_repository`) that replaces a
      repo's symbols/docs/links atomically.
- [x] Background indexing worker tracking `AnalysisJob` + `Repository.indexing_status`
      (pending → indexing → indexed/failed); triggered from `POST
      /repositories/{id}/connect` via `BackgroundTasks`.
- [x] Repository detail (symbol/doc counts) and jobs-listing endpoints.
- [x] Tests: code extraction, doc discovery, linker, pipeline persistence +
      idempotency, job success/failure transitions — **62 tests**, mypy + ruff
      clean. Real-world smoke test on Variorum's own repo: 78 files, 583 symbols,
      38 doc↔code links.

### M3 — Detect (complete)
- [x] AIService.complete_structured returning parsed JSON **plus** provider/model
      provenance, so every verdict records which provider answered.
- [x] Drift assessor: prompt builder (doc content + relevant diffs + affected
      symbols, budget-truncated) and `assess_document_drift` → structured
      `DriftVerdict` (drifted?, severity, summary, evidence, suggested update).
- [x] PR context mapper: changed file paths → affected symbols → related
      documents via `doc_code_links` (path and symbol links).
- [x] GitHub client: `list_pull_request_files` (paginated) and `get_file_text`
      (contents at a ref).
- [x] PR analysis worker: fetch PR files → build candidates → fetch doc content
      at head → assess drift via the AI layer → persist `drift_findings` with
      evidence (PR#, trigger files, symbols, provider/model, suggested update);
      manages the `pr_analysis` AnalysisJob. Candidate count is capped and logged.
- [x] Webhook enqueues analysis on `pull_request` opened/synchronize/reopened
      for connected repos; unknown repos/actions are skipped.
- [x] API: job detail with findings, finding detail, per-repo findings list.
- [x] Frontend: "Documentation drift" panel on the dashboard (severity, summary,
      PR#, doc path).
- [x] Tests: context mapper, drift prompt + assessor (fake AI), PR worker
      (drift / no-drift / missing-content / no-provider), webhook enqueue —
      **77 tests**, mypy + ruff clean, frontend build passes.

### M4 — Propose (complete)
- [x] GitHub write operations on the client: `get_file` (content + blob sha),
      `get_branch_sha`, `create_branch`, `put_file` (Contents API), and
      `create_pull_request`.
- [x] AI doc-fix generation: `generate_updated_document` rewrites the full
      corrected file from the drift summary, suggested update, and evidence.
- [x] `create_doc_fix_pr` orchestration: fetch current doc → generate update →
      create branch → commit → open PR (body cites the drift + triggering PR) →
      record in `generated_prs` and mark the finding `pr_opened`. Idempotent per
      finding; skips when no change is produced or the doc is absent on base.
- [x] `POST /findings/{id}/open-pr` endpoint (graceful 503/502/409 handling).
- [x] Frontend: "Open doc-fix PR" action per finding with a resulting "View PR"
      link.
- [x] Tests: doc-fix generation (fake AI), create-PR orchestration with a fake
      GitHub client (branch/commit/PR recorded, `generated_prs` row, finding
      transition, no-change + missing-doc skips, idempotency), and client write
      ops via mocked transport — **84 tests**, mypy + ruff clean, frontend build
      passes.

### Hardening — demo readiness (complete)
- [x] Verified all four AI providers live with real keys; corrected model
      defaults to working IDs (`gemini-flash-latest`, `deepseek-v4-flash`,
      `sonar`) — see the discovery that `gemini-2.5-flash`/`deepseek-chat` were
      dead.
- [x] Failure isolation: one bad AI response or unfetchable doc no longer fails
      a whole PR-analysis job (per-candidate try/except); the open-PR endpoint
      maps AI/GitHub errors to clean 502/503/409s.
- [x] GitHub client hardening: URL-encoded content paths; `create_branch`
      tolerates an already-existing ref (idempotent retries).
- [x] **Manual PR analysis** (`POST /repositories/{id}/analyze-pr`) so a demo
      runs entirely on localhost without a webhook tunnel.
- [x] `GET /system/status` readiness (database, AI, GitHub App) surfaced as
      dashboard cards; dashboard auto-refreshes while indexing.
- [x] Diagnostics: `scripts/check_env.py` (config checklist) and
      `scripts/check_ai.py` (live provider ping); cross-platform start scripts
      (`scripts/start-*.ps1|.sh`).
- [x] `SETUP.md`: click-by-click GitHub App creation, every `.env` value
      explained, and a demo script.
- [x] Full suite green: **88 tests**, mypy + ruff clean, frontend build passes;
      backend + frontend verified serving locally.

## MVP complete 🎉

The Phase 1 loop is closed end-to-end: **connect → understand → detect drift
(with evidence) → propose a doc-fix pull request**. Variorum proposes; humans
review and merge — it never auto-merges or force-pushes. See
[`SETUP.md`](./SETUP.md) to configure and demo it.

To run it live, register a GitHub App (README → *GitHub App setup*), fill the
credentials + at least one AI key into `.env`, connect a repository, and open a
pull request that changes documented code.

**Next horizons (post-MVP):**
- Harden the live path (rate limits, large diffs, incremental re-index on push).
- Phase 2 — Engineering Memory: ingest commit/PR/issue history; evidence-cited
  Q&A over the repository (`pgvector`).
- Phase 3 — Testing Intelligence: risk scoring + coverage-gap → CI-verified test
  PRs.
- Durable job queue (replace `BackgroundTasks`), response caching, and
  observability dashboards.

### Post-MVP security & robustness review (complete)
An independent review pass hardened the live path:
- **Installation ownership** can no longer be hijacked — `upsert_installation`
  never reassigns an installation to a different owner, and `setup_callback`
  requires login and confirms ownership.
- **Session secret** is enforced (startup fails in production if left default);
  the session cookie sets `https_only` in production + explicit `SameSite`.
- **Account identity** is keyed strictly on `github_user_id` (no email-based
  linking, which could merge accounts).
- **Doc-fix PRs are idempotent**: unique constraint on
  `generated_prs.drift_finding_id`, blob sha read from the branch (not base),
  and an already-existing PR is reused instead of erroring.
- **Installation tokens are cached** until near expiry (fewer token mints / less
  rate-limit pressure).
- **Gemini API key** is sent via the `x-goog-api-key` header, never the URL, so
  it can't leak into logs.
- **Re-analysis no longer duplicates findings** — prior un-actioned findings for
  the same PR are superseded.
- Known limitations kept for later: malformed-provider-JSON isn't
  fallback-eligible (mitigated per-doc); background jobs are fire-and-forget
  (needs a durable queue for production).

**Verification:** 91 tests, mypy + ruff clean, all four AI providers confirmed
live.

---

## Phase 2 — Engineering Memory (design)

**Goal:** preserve engineering decisions and history so the team can ask *why*
the system is the way it is — answered from real artifacts, with citations, and
never an unsupported claim.

### Data model (new tables)
- **knowledge_entries** — `id`, `repository_id → repositories`, `kind`
  (commit | pull_request | issue | review), `source_ref` (sha / PR# / issue#),
  `title`, `body` (text), `url`, `author`, `occurred_at`, `content_hash`
  (dedupe/idempotent re-ingest), `created_at`. Indexed on
  `(repository_id, kind)` and a Postgres full-text `tsvector` (GIN) over
  `title || body`. A nullable `pgvector` embedding column is added in M7.
- **ask_queries** *(optional, observability)* — record questions asked, the
  entries retrieved, and which provider answered.

### Milestones
- **M5 — History ingestion:** `knowledge_entries` model + migration; GitHub
  client methods to list commits / pull requests / issues (paginated, capped);
  an ingestion service + background job (idempotent on `content_hash`); an API
  to trigger ingestion and report status. Reuses the installation-token client.
- **M6 — Retrieval + cited Q&A:** PostgreSQL full-text retrieval (ranked by
  relevance + recency); `POST /repositories/{id}/ask` → retrieve top-K entries →
  build a tightly-scoped prompt → AI answers **only** from the provided context
  **with citations** (each claim references an entry's `source_ref`/`url`); if
  the context is insufficient, it says so. Frontend "Ask" panel showing the
  answer + citation chips.
- **M7 — Semantic search:** add embeddings via the AI layer (Gemini embedding
  model) into a `pgvector` column; hybrid keyword + vector retrieval.

### Principles carried over
- Evidence-first: every answer cites its sources; refuse rather than fabricate.
- Provider-agnostic AI via the existing fallback layer.
- Bounded context sent to models (top-K retrieval, truncation), never whole
  histories.
- Human-in-the-loop remains for any write actions.

**Starting point:** M5 (history ingestion) — the data foundation the Q&A builds
on.

### Phase 2 delivered ✅
- **M5 — History ingestion:** `knowledge_entries` + GitHub commit/PR/issue
  client methods + idempotent ingestion worker + API. Verified live.
- **M6 — Cited Q&A:** full-text retrieval (tsvector + GIN) + `POST
  /repositories/{id}/ask` answering only from context with grounded citations;
  "Engineering memory" dashboard card. Verified live.
- **M7 — Semantic search:** embeddings via `gemini-embedding-001` (768-dim),
  stored as JSONB, blended with keyword search via in-process cosine similarity;
  graceful fallback to keyword-only when embeddings are unavailable.
  - **pgvector note (now implemented as an optional path):** embeddings are stored
    as JSONB and ranked in-process by default. A guarded migration
    (`c7d2f1a9b4e0`) adds a `vector` column + HNSW index + sync trigger **only
    where the `vector` extension is available**, and retrieval auto-detects this
    (`pgvector_active()`, `PGVECTOR_ENABLED`) to use an indexed `<=>` query,
    falling back to in-process cosine otherwise. `alembic upgrade head` never
    fails on a plain PostgreSQL.
  - Verified live: a paraphrased question with no keyword overlap retrieved the
    correct commit semantically, and the provider fallback recovered from a live
    Gemini 503 mid-answer.

**Status:** 113 tests, mypy + ruff clean. Phase 2 (Engineering Memory) is
functionally complete.

---

## Phase 3 — Testing Intelligence (in progress)

Help teams keep quality high: score the risk of a change and turn gaps into
CI-verified test PRs.

- **M8 — Risk analysis (complete):** `RiskFinding` model + migration; a scoring
  service that derives per-file signals (churn, symbol count, and a
  test-coverage heuristic over the code index) and asks the AI to assess risk
  and list *specific, testable* untested scenarios; `run_risk_analysis_job`
  (per-file failure isolation, supersede-on-re-run); `POST
  /repositories/{id}/analyze-risk` + `GET /repositories/{id}/risk-findings`; a
  "Testing intelligence" dashboard card. 121 tests, mypy + ruff clean. Verified
  live on variorum PR #1 (medium risk, concrete untested scenarios).
- **M9 — Test-PR generation (complete):** for a risk finding, the AI generates a
  test file (written to a non-colliding `*_variorum` path so it never overwrites
  real tests) and opens a test PR through the GitHub App (reusing the doc-fix PR
  machinery: branch → commit → PR, idempotent per finding via
  `generated_prs.risk_finding_id`). `POST /risk-findings/{id}/generate-tests` +
  a "Generate tests PR" button on each risk finding. The repository's existing
  CI verifies the PR; humans review and merge. 128 tests, mypy + ruff clean.
  Verified live: generated correct pytest tests for a real source file.

**Phase 3 complete.** All three product surfaces from the PRD are now built:
Documentation Intelligence (Phase 1), Engineering Memory (Phase 2), and Testing
Intelligence (Phase 3) — each following the same detect/answer → propose loop
with a human review gate.

### Enhancement — unified PR analysis
A single **"Analyze PR"** (the `POST /repositories/{id}/analyze-pr` endpoint and
the `pull_request` webhook) now fans out to **both** documentation-drift and
test-risk analysis in one action; the dashboard shows both result cards from
that one trigger. The granular `analyze-risk` endpoint remains for targeted runs.

### Post-MVP milestones

- **Frontend revamp:** landing page + full dashboard redesign (design-system
  tokens, `DashboardProvider` context, routed sub-pages, animations, toasts,
  skeletons, a11y, responsiveness).
- **Finding triage:** dismiss/restore for drift **and** risk findings
  (`RiskFinding.status` column + migration `ffac9be3ec48`; `POST
  /findings/{id}/dismiss|restore`, `POST /risk-findings/{id}/dismiss|restore`),
  with optimistic UI and a "show dismissed" filter.
- **Theme toggle** (no-flash, persisted, light+dark), **command palette**
  (Cmd/Ctrl-K navigation/search), and a **per-repository detail page**
  (`/dashboard/repositories/[id]`) with a jobs activity timeline.
- **Repository & team insights:** `GET /repositories/{id}/insights`
  (doc-health score, severity/risk breakdowns, activity, top risk files,
  knowledge coverage) and `GET /api/v1/teams` (per-installation rollups) with a
  Teams dashboard page.
- **Semantic search at scale:** optional pgvector path with auto-detection and
  fallback (see M7 note).
- **Repository Orientation:** `repository_guides` model + migration
  (`d5b8e3c07f21`); a service that fuses the code index, docs, and history into a
  cited onboarding guide via structured AI output; `GET`/`POST
  /repositories/{id}/orientation`; an Orientation card on the repo detail page.
- **Security & production hardening:** startup validation of production secrets
  (fail-fast), security-headers middleware + HSTS, generic client errors with a
  catch-all handler, in-process rate limiting, a defense-in-depth path-traversal
  guard, configurable session-cookie SameSite, DB pool tuning, a backend
  `Dockerfile`/entrypoint, and full docs (`SECURITY.md`, `CONTRIBUTING.md`,
  `PRODUCTION_CHECKLIST.md`, `PRODUCTION_DEPLOYMENT_GUIDE.md`, MIT `LICENSE`).

**Status:** 155 backend tests, mypy + ruff clean; frontend tsc + lint clean.
The full endpoint surface is browsable at `/docs` (OpenAPI) — treat that as the
authoritative API reference; §13 lists the original Phase-1 set.

---

## Post-MVP roadmap — Repository Analytics & Team Intelligence (complete)

With the three PRD product surfaces built, an approved follow-on roadmap turned
the accumulated code index + history into **actionable, cited analytics** for
individuals, repositories, and the whole portfolio. Delivered in three waves,
each fully tested and shipped (backend service + endpoint + tests, then frontend
UI, verify, commit, push). Same principle throughout: **surface evidence, link
to the source, recommend an action — never just show a number.**

### Wave 1 — Repository metrics
- **Change dataset:** `FileChange` churn table (migration `e9a1c4d7b350`),
  populated from commit-file history during ingestion; a reusable
  `services/metrics.py` (`hotspot_map`, `compute_ownership`, `compute_doc_coverage`,
  `compute_health`).
- **Change-risk hotspots:** per-file score (churn × changes × fix-commits ×
  missing-tests), paginated, colour-legended, each file deep-links to GitHub.
- **Ownership & bus-factor:** per-module author concentration; flags single-owner
  modules (`author_count == 1 or primary_share ≥ 0.8`).
- **Doc coverage & Knowledge Health Score:** documented-source ratio with
  *actionable* recommendations, plus a composite health score with subscores.
- In-card **"Ingest history"** button with auto-refresh polling so cards populate
  without leaving the page.

### Wave 2 — Knowledge & workflow
- **Decision Timeline:** `DecisionEntry` model (migration `f3c8a1e6d924`); AI
  distils history into cited "why" decisions.
- **PR Impact Briefing:** per-changed-file hotspot/ownership/risk rollup for a PR.
- **Unified Search:** one query across symbols, docs, decisions, and knowledge.
- **Weekly Digest:** trailing-window recap (new drift/risk/knowledge, health,
  single-owner count, top hotspots, recently ingested) — all items clickable.
- **Contradiction Detection:** flags recorded decisions/history a PR appears to
  contradict, with citations.

### Wave 3 — Org-level & access
- **Portfolio Health:** `GET /portfolio` — cross-repo health, at-risk count,
  clickable top hotspot per repo, plus a client-computed recommendations panel.
- **Expertise Directory:** `GET /experts` — authorship rollup with bus-factor
  banner, sole-owner areas, languages, and a "best person to ask" highlight.
- **API access & tokens:** additive bearer-token auth alongside session cookies;
  `ApiToken` model (migration `a2f7b1c93d05`, SHA-256 hash only, plaintext shown
  once); `/auth/tokens` CRUD; a Settings token manager with copy/revoke and a
  curl usage snippet.
- **Slack digest delivery:** per-user incoming-webhook config (`User.slack_webhook_url`,
  migration `b8e4d21a6c37`; status endpoint never returns the secret URL);
  `POST /repositories/{id}/digest/slack` formats and sends the weekly digest
  (409 if unconfigured, 502 if Slack rejects). Sending is **always** an explicit
  user action; tests mock the HTTP call — no live Slack traffic.

**Status:** 206 backend tests, mypy + ruff clean; frontend tsc + lint clean,
production build passes (13 routes). All resources remain ownership-scoped; the
human-review gate and $0 constraint are preserved (Slack incoming webhooks and
the AI free-tier fallback add no cost).

---

## Knowledge retrieval — embeddings & RAG foundation (complete)

Embeddings + RAG were already in place from Phase 2 (Gemini `gemini-embedding-001`
768-dim with dual-key fallback; JSONB vector storage plus a guarded, HNSW-indexed,
trigger-synced **pgvector** acceleration path; hybrid semantic ⊕ keyword retrieval
→ cited LLM answers; `embed_missing` backfill). Rather than rebuild a working
system, this pass **extended the foundation** so it's reusable and covers the
highest-signal "why" source.

- **Reusable RAG core (`ai/rag.py`):** extracted `cosine` and a generic
  `top_k_by_cosine(query_vec, items, get_vec, k, min_similarity)` — the shared
  in-process semantic-ranking primitive any embedded content type can use.
  `services/qa.py` now ranks through it (behaviour-preserving for history).
- **Decisions are now embedded and retrievable:** `DecisionEntry.embedding` JSONB
  column (migration `c4f9a2e17b83`); embeddings computed when a decision timeline
  is synthesized, with an `embed_missing_decisions` backfill. Decisions are few
  per repo, so JSONB + in-process cosine is used (no pgvector mirror needed).
- **Q&A blends both corpora:** `retrieve_decisions()` (semantic + keyword, with an
  ILIKE fallback) runs alongside history retrieval, and `answer_question` folds
  synthesized decisions into the same numbered, cited context (decisions default
  to none, so the existing history-only path is unchanged). Citations carry a
  `decision` kind. The Ask endpoint wires both.
- **Deliberate non-goals:** `Document` stores no body text (only path/title/hash),
  so embedding docs would be low-signal; code symbols (~900/repo) are high-volume
  and weak for "why" questions. Both stay on keyword search via unified search —
  a conscious scope decision, not an omission.

Verified live: all 8 of the demo repo's decisions embedded via the real Gemini
endpoint, and a semantic query ("why was the AI provider layer designed this
way") correctly surfaced the AI-provider-fallback decision as the top hit.

**Status:** 216 backend tests (+10), mypy + ruff clean. `alembic upgrade head`
still succeeds with or without pgvector. (ADR
[`0003`](./docs/adr/0003-decisions-in-rag-retrieval.md).)

---

## Phase 4 — from insight to workflow (in progress)

Phases 0–3 answered questions in the dashboard; Phase 4 pushes the answers into
where engineers already work.

### 4C — PR-native impact briefings (complete)

The PR Impact Briefing now posts to the pull request itself as a **single sticky
comment** (per-file hotspot risk, module owner / bus factor, tests, plus open
doc-drift and test-risk counts for the PR). A hidden marker makes it idempotent —
repeated runs update one comment instead of stacking.

- **GitHub client:** `list_issue_comments` / `create_issue_comment` /
  `update_issue_comment` (Pull requests: write — no new App permission).
- **`services/pr_comment.py`:** Markdown rendering + `upsert_pr_comment` (sticky
  by marker). **`workers/pr_comment.py`:** builds the briefing, counts PR
  findings, upserts — best-effort, never crashes the worker.
- **Opt-in:** `Repository.pr_comments_enabled` (migration `d1e5b7a34f96`, default
  false). The `pull_request` webhook enqueues the comment job *after* drift +
  risk (sequential BackgroundTasks) so it reflects their findings — but only when
  enabled. A manual endpoint (`POST /repositories/{id}/pr-comment/{pr_number}`)
  posts on the owner's explicit action regardless.
- **Frontend:** an auto-post toggle and a "Post to GitHub" button on the PR
  briefing panel.
- Posting stays within the human-review gate (guidance only) and $0 constraint.
  ADR [`0004`](./docs/adr/0004-pr-native-briefing-comments.md).

**Status:** 226 backend tests (+10), mypy + ruff clean; frontend tsc + lint
clean, production build passes.

### 4A — scheduled weekly digests (complete)

Digests can now be delivered to Slack on a weekly cadence, not just on-demand.

- **`DigestSchedule`** model (migration `e2c8f4b19d70`, one row per repo:
  UTC day-of-week + hour, `enabled`, `last_sent_at`).
- **`services/schedule.py`:** CRUD + `due_schedules` (matches UTC weekday+hour,
  de-duped by a 12h resend window) + `run_due_digests` (owner-scoped; builds the
  digest, sends to the owner's Slack webhook, stamps `last_sent_at`; best-effort
  per schedule). Injectable `sender` for tests — no live Slack traffic.
- **In-process scheduler:** a FastAPI-lifespan background loop ticks every
  `SCHEDULER_INTERVAL_SECONDS` (default 900) and runs due digests. Gated by
  `SCHEDULER_ENABLED` (default true; off in the test suite). No new dependency —
  consistent with the BackgroundTasks-for-MVP posture; a durable scheduler is the
  documented production upgrade.
- **Endpoints:** `GET/PUT/DELETE /repositories/{id}/digest/schedule`.
- **Frontend:** a weekly-schedule control (day + hour + Schedule/Pause) on the
  digest card, shown once Slack is connected.
- Sending remains automated *delivery of a recap* only — never an automated code
  or PR action — so the human-review gate is intact; $0 (Slack webhooks + free AI
  fallback).

**Status:** 233 backend tests (+7), mypy + ruff clean; frontend tsc + lint clean,
production build passes. Phase 4 tracks 4C + 4A delivered.

---

## Environment, skills & tooling

**Permanent memory:** [`CLAUDE.md`](./CLAUDE.md) is the entry point for every
session (stack, architecture, conventions, skills, library decisions, the $0
rule, dev commands, gotchas).

**Claude Code skills.** Rather than install unvetted third-party plugins (and to
honor the $0 / no-supply-chain-risk rule), the project uses:
- **Built-in skills**: `security-review`, `code-review`/`review`, `simplify`,
  `init`, `dataviz`, `artifact-design`, `ai-writing-tropes`.
- **Project skills** in `.claude/skills/` (versioned in the repo, auto-loaded):
  `variorum-frontend`, `variorum-ui-ux`, `variorum-backend`, `variorum-python`,
  `variorum-security`, `variorum-testing`, `variorum-git-github`,
  `variorum-docs` — each encodes Variorum's actual conventions for its domain.

**Libraries.** No new dependencies were added during environment prep — the
stack was evaluated and is already minimal and all-free. Chosen tools and
rejected alternatives (Celery/Redis, Supabase, vendor AI SDKs, numpy, pgvector-
for-now) are documented with rationale in `CLAUDE.md`.

**Cost:** $0 — open-source libraries, native PostgreSQL, free-tier AI keys
behind a fallback layer, and a free GitHub App.
