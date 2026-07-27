<div align="center">

# Variorum

**The AI-powered engineering knowledge layer for software teams.**

Variorum connects to your GitHub repositories and preserves the knowledge *around*
your code — the decisions, the history, and the rationale — so context never leaves
with the people who wrote it.

<sub>Next.js · React · TypeScript · Tailwind · FastAPI · Python · PostgreSQL · GitHub App · Multi-provider AI</sub>

</div>

---

## The problem

Code is only half the story. The context around it — *why* a decision was made, *why*
a workaround exists, which documentation is stale, what changed and why — is fragile.
It lives in people's heads, scattered commits, and old pull requests, and it erodes as
teams grow and engineers move on.

The result: docs drift out of date, onboarding drags for weeks, and the answer to
"why is the system built this way?" is lost.

## The solution

Variorum continuously understands a repository and turns that scattered context into
shared, trustworthy, **cited** knowledge. It is **not** a code generator — coding
assistants answer *"what code should I write?"*; Variorum answers *"why does this code
exist, and how does the whole system fit together?"*

Every surface follows the same loop: **detect or answer → propose → human review.**
Variorum proposes; your team reviews and merges. It never auto-merges and never
force-pushes.

## Features

Variorum ships three product surfaces:

| Surface | What it does |
|---|---|
| 📄 **Documentation Intelligence** | When a pull request changes code, Variorum detects when documentation has drifted out of sync — with evidence for every claim — and can open a doc-fix pull request for review. |
| 🧠 **Engineering Memory** | Ingests commit, PR, and issue history into a searchable knowledge store and answers *"why is the system this way?"* with citations. Keyword + semantic retrieval. |
| 🛡️ **Testing Intelligence** | Scores the risk of each pull request, surfaces scenarios that look untested, and can open a test pull request for review. |
| 🧭 **Repository Orientation** | Auto-generates a cited onboarding guide — what the repo is, its key areas, where to start, and the decisions behind it — by fusing the code index, documentation, and engineering history. |

Plus **repository & team insights** — documentation-health scores, risk breakdowns, activity, and per-organization rollups across every connected repository.

Underpinning all three:

- **Codebase understanding** — a structural map of files, functions, classes, and how documentation relates to code (via [tree-sitter](https://tree-sitter.github.io/tree-sitter/)).
- **Provider-agnostic AI** — a fallback chain across multiple providers so a single provider's quota or outage never breaks the product.
- **Least-privilege GitHub App** — per-installation tokens, verified webhooks, scoped repository access.

## How it works

1. **Connect** your repository by installing the Variorum GitHub App.
2. Variorum **understands it** — mapping the code, discovering documentation, and ingesting the history behind it.
3. On every pull request, it surfaces **insights** — documentation drift, risky changes, and untested scenarios — each with evidence.
4. Your team **stays in sync** — ask why the system is the way it is, and merge proposed fixes with one review.

## Tech stack

**Frontend** — Next.js 15 (App Router), React 19, TypeScript (strict), Tailwind CSS,
shadcn-style components, framer-motion, recharts.

**Backend** — FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, Uvicorn, httpx, PyJWT.

**Database** — PostgreSQL 17.

**Code analysis** — tree-sitter + tree-sitter-language-pack.

**AI** — a provider-agnostic layer over Google Gemini, DeepSeek, and Perplexity, called
over REST with automatic fallback. Embeddings via Gemini.

**Integration** — a GitHub App (not an OAuth App) for least-privilege, per-installation
repository access.

## Local development

### Prerequisites

- Python 3.11+ (developed on 3.13)
- Node.js 20+ (developed on 24)
- PostgreSQL 17 (native, or via the bundled `docker-compose.yml`)
- A GitHub App — only needed for the GitHub-integration features (see [`SETUP.md`](./SETUP.md))

### Setup

```bash
# 1. Environment — copy the template and fill in values (never commit .env)
cp .env.example .env

# 2. Database (optional Docker Postgres; publishes on host port 5433)
docker compose up -d db

# 3. Backend
cd backend
python -m venv .venv
# Windows PowerShell:   .venv\Scripts\Activate.ps1
# macOS / Linux / Git Bash:  source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
# API docs: http://localhost:8000/docs

# 4. Frontend (separate terminal)
cd frontend
npm install
npm run dev
# App: http://localhost:3000/dashboard
```

> On Windows, run the commands directly — the `Makefile` targets assume a POSIX shell
> (Git Bash / WSL). A `scripts/start-all.ps1` helper starts both services together.

### Verify your setup

```bash
cd backend && ./.venv/Scripts/python.exe scripts/check_env.py   # config sanity
cd backend && ./.venv/Scripts/python.exe scripts/check_ai.py    # AI providers reachable
```

## Environment variables

All configuration is via environment variables. Copy [`.env.example`](./.env.example) to
`.env` and fill in the values — every variable is documented there. Highlights:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `SESSION_SECRET` | Signs auth session cookies — set a long random value |
| `CORS_ORIGINS` | Comma-separated allowlist of frontend origins |
| `GEMINI_API_KEY_1` / `_2`, `DEEPSEEK_API_KEY`, `PERPLEXITY_API_KEY` | AI providers (at least one required); fallback order is Gemini 1 → Gemini 2 → DeepSeek → Perplexity |
| `GITHUB_APP_ID`, `GITHUB_APP_CLIENT_ID/SECRET`, `GITHUB_WEBHOOK_SECRET`, `GITHUB_APP_PRIVATE_KEY_*` | GitHub App credentials — see [`SETUP.md`](./SETUP.md) |

**Secrets are never committed.** `.env`, `*.pem`, `*.key`, and `secrets/` are git-ignored.
In production the backend refuses to start if `SESSION_SECRET`, `GITHUB_WEBHOOK_SECRET`,
`DATABASE_URL`, or `CORS_ORIGINS` are left at insecure defaults.

## Project structure

```
backend/
  app/
    api/routes/     auth, github, repositories, analysis, teams, webhooks, system
    ai/             provider-agnostic AI layer (base, manager, providers, service, embeddings)
    services/       github/ · indexer/ · analysis/ · knowledge · qa · insights · orientation
    workers/        background jobs (indexing, PR analysis, risk, ingestion)
    core/           config, logging, rate limiting
    db/ · models/ · schemas/
  alembic/          database migrations
  tests/            pytest suite
  Dockerfile        production backend image (+ entrypoint.sh)
frontend/
  src/app/          Next.js routes (landing + dashboard: overview, repositories, [id],
                    insights, teams, memory)
  src/components/    UI, dashboard, theme (provider/toggle), command palette, charts
  src/lib/          API client, utilities
docs/adr/           architecture decision records
scripts/            dev / setup helpers
```

Deployment: the frontend runs on Vercel and the backend as a Docker web service
(the repo ships a `backend/Dockerfile` + `entrypoint.sh`) against a managed
PostgreSQL, with `/health/ready` as the readiness probe.

See [`PROJECT_PLAN.md`](./PROJECT_PLAN.md) for the full product requirements,
architecture, and build log, and [`SETUP.md`](./SETUP.md) for the GitHub App walkthrough.

## Security

Variorum is built for repository access, so security is a first-class concern:

- No secrets are committed; environment handling is documented and validated at startup.
- Every resource is ownership-scoped to the authenticated user.
- The GitHub App uses least-privilege, per-installation tokens; webhook signatures are
  verified with a constant-time HMAC comparison.
- Generated changes always go to a dedicated branch and open a pull request — never a
  direct write to the default branch, never an auto-merge, never a force-push.
- Baseline security headers, CORS allowlisting, rate limiting on sensitive endpoints, and
  generic client-facing errors (full detail logged server-side only).

See [`SECURITY.md`](./SECURITY.md) for the security model and how to report a
vulnerability.

## Contributing

Contributions are welcome. See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for the development
setup, coding standards, and the pull request process.

## Roadmap

- **Phase 1 — Documentation Intelligence** ✅ *shipped*
- **Phase 2 — Engineering Memory** ✅ *shipped*
- **Phase 3 — AI Testing Intelligence** ✅ *shipped*
- **Repository & team insights** ✅ *shipped*
- **Semantic search at scale (optional pgvector, auto-detected with fallback)** ✅ *shipped*
- **Repository Orientation (onboarding guides)** ✅ *shipped*
- **Next** — a durable background-job queue for horizontal scale, incremental re-indexing, more language grammars, and a shared/edge rate limiter.

## Author

**Muhammad Danish** — Computer Scientist & Software Engineer
[emdanish.dev](https://emdanish.dev)

Computer scientist and software engineer focused on building practical SaaS products
and AI-powered engineering tools. Built with Next.js, React, TypeScript, Tailwind CSS,
FastAPI, Python, PostgreSQL, and AI/GitHub integrations.

## License

Released under the [MIT License](./LICENSE).
