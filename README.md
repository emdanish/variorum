# Variorum

**The memory system for software teams.** Variorum is an AI-powered engineering
knowledge layer that continuously understands a GitHub repository and keeps the
*context* around the code — decisions, history, and rationale — accurate over
time.

It is **not** a code generator. Coding assistants answer *"what code should I
write?"* Variorum answers *"why does this code exist and how does the whole
system fit together?"*

The first product surface (MVP, Phase 1) is **Documentation Intelligence**: when a
pull request changes code, Variorum detects when documentation has drifted out of
sync and proposes a doc-fix pull request — with evidence for every claim.

See [`PROJECT_PLAN.md`](./PROJECT_PLAN.md) for the full PRD, architecture, and
roadmap.

---

## Repository layout

```
backend/    FastAPI + SQLAlchemy + AI provider layer + GitHub App service
frontend/   Next.js + Tailwind + shadcn/ui
docs/       architecture decision records
scripts/    dev/setup helpers
```

## Prerequisites

- Python 3.11+ (developed on 3.13)
- Node.js 20+ (developed on 24)
- Docker (for local PostgreSQL 17)
- A GitHub App (see below) — only needed for the GitHub-integration features

## Quick start (local)

```bash
# 1. Environment
cp .env.example .env         # then fill in values

# 2. Database (PostgreSQL 17 via Docker)
docker compose up -d db

# 3. Backend
cd backend
python -m venv .venv
# Windows PowerShell:  .venv\Scripts\Activate.ps1
# macOS/Linux/Git Bash: source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
# API docs: http://localhost:8000/docs

# 4. Frontend (separate terminal)
cd frontend
npm install
npm run dev
# App: http://localhost:3000
```

> On Windows without `make`, run the commands above directly. The `Makefile`
> targets assume a POSIX shell (Git Bash / WSL).

## Configuration

All configuration is via environment variables documented in
[`.env.example`](./.env.example). Highlights:

- `DATABASE_URL` — PostgreSQL connection (defaults match `docker-compose.yml`).
- AI provider keys — at least one is required for analysis features. Fallback
  order: **Gemini key 1 → Gemini key 2 → DeepSeek → Perplexity**.
- GitHub App credentials — see below.

Secrets are **never** committed. `.env`, `*.pem`, and `secrets/` are git-ignored.

## AI provider layer

Application code never talks to a provider directly. It depends on the
`AIService` interface; a `ProviderManager` selects providers and falls back
automatically when a key is missing, out of quota, or erroring. Adding or
reordering providers is a configuration change, not a code change. See
[`backend/app/ai/`](./backend/app/ai/).

## GitHub App setup

Variorum uses a **GitHub App** (not an OAuth App) so it can read code and open
pull requests with least-privilege, per-installation tokens.

1. Go to **https://github.com/settings/apps** and click **New GitHub App**.
2. **GitHub App name:** e.g. `variorum-dev`.
3. **Homepage URL:** `http://localhost:3000`.
4. **Callback URL** (user sign-in / OAuth): your public backend URL +
   `/api/v1/auth/github/callback`.
5. **Setup URL** (where GitHub sends users after install): your public backend
   URL + `/api/v1/github/setup`, and tick **Redirect on update**.
6. **Webhook URL:** your public backend URL + `/webhooks/github`. For local
   development, tunnel it with [smee.io](https://smee.io) or `cloudflared` and
   paste the tunnel URL.
7. **Webhook secret:** generate a long random string; put the same value in
   `.env` as `GITHUB_WEBHOOK_SECRET`.
8. **Repository permissions:** Contents = *Read & write*, Pull requests =
   *Read & write*, Metadata = *Read-only*.
9. **Subscribe to events:** *Pull request*, *Push*, *Installation*, and
   *Installation repositories*.
10. Click **Create GitHub App**.
11. On the App page, copy the **App ID** → `.env` `GITHUB_APP_ID`. Copy the
    **Client ID** → `GITHUB_APP_CLIENT_ID`, generate a **client secret** →
    `GITHUB_APP_CLIENT_SECRET`, and note the **slug** (from the App URL) →
    `GITHUB_APP_SLUG`.
12. Under **Private keys**, click **Generate a private key**. A `.pem` file
    downloads. Save it to `backend/secrets/github-app.pem` (git-ignored) and set
    `GITHUB_APP_PRIVATE_KEY_PATH` accordingly — or base64-encode it into
    `GITHUB_APP_PRIVATE_KEY_BASE64`.

## Testing

```bash
cd backend && pytest -q        # backend unit/integration tests
cd frontend && npm run lint    # frontend lint
```

## Status

Phase 0 (foundation). Track progress in the build log at the end of
[`PROJECT_PLAN.md`](./PROJECT_PLAN.md).
