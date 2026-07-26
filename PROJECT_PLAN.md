# Variorum — Engineering Knowledge Infrastructure

> **Variorum** *(n.)* — an edition of a text annotated with notes and variant
> readings gathered from many sources. Variorum does the same for a codebase:
> it keeps the *context* around the code — the decisions, history, and rationale —
> alive and current.

This document is the single source of truth for the project. Any engineer (human
or agent) joining with zero prior context should be able to read this file and
understand **what** we are building, **why**, **how**, **what is done**, and
**what remains**.

- **Status:** Phase 0 (foundation) — in progress
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
| 0 | Foundation | Repo, architecture, AI layer, GitHub App skeleton, DB schema | current |
| 1 | Documentation Intelligence (MVP) | Doc-drift detection → doc-fix PRs | next |
| 2 | Engineering Memory | Evidence-cited Q&A over repo history | after MVP validation |
| 3 | Testing Intelligence | Risk + coverage → test PRs | later |

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
- **Least privilege GitHub App:** Contents (read/write for doc PRs), Pull requests
  (read/write), Metadata (read), Webhooks. No admin scopes.
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
- No semantic search until Phase 2 (`pgvector`).
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

**MVP status:** the Phase 1 loop is closed end-to-end except automated doc-fix
PRs — connect → understand → **detect drift with evidence**.

**Next up (M4 — Propose):** turn a `drift_finding` (with its AI-suggested update)
into a real pull request via the GitHub App — create a branch, commit the doc
change, open a PR referencing the triggering PR, and record it in `generated_prs`.
Human review + merge stays the gate; Variorum never auto-merges.
