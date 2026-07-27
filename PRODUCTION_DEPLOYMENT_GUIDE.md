# Production Deployment Guide

How to deploy Variorum as a public SaaS: a **Next.js frontend** (e.g. Vercel) and
a **FastAPI backend** (a long-lived container or VM) backed by **PostgreSQL**.

Read alongside [`PRODUCTION_CHECKLIST.md`](./PRODUCTION_CHECKLIST.md) (the
pre-flight checklist) and [`SECURITY.md`](./SECURITY.md).

---

## 0. Architecture decision: how the frontend reaches the backend

Pick **one** before you deploy — it dictates your cookie and CORS settings.

- **Option A — same-origin proxy (recommended, simplest).** Route browser calls
  through Next's rewrite so the frontend and backend share an origin. Set
  `api.ts`'s base to `/api/backend` (via `NEXT_PUBLIC_BACKEND_URL=/api/backend`)
  and set server-side `BACKEND_URL` on Vercel to the backend's URL. Cookies stay
  same-origin (`SESSION_COOKIE_SAMESITE=lax` is fine) and **CORS is irrelevant**.
- **Option B — split domain (direct cross-origin).** The browser calls the
  backend directly (`NEXT_PUBLIC_BACKEND_URL=https://api.example.com`). You must
  then set `SESSION_COOKIE_SAMESITE=none` (cookies are Secure automatically in
  prod), list the exact frontend origin in `CORS_ORIGINS`, and serve both over
  HTTPS. `credentials: "include"` is already used by the client.

> Why it matters: the session cookie carries auth. With `SameSite=Lax` a
> cross-site XHR does **not** send the cookie, so a split-domain deploy that
> leaves the default `lax` will make users appear logged out. Option A sidesteps
> this entirely.

---

## 1. Backend (container or VM)

A production `Dockerfile` and `entrypoint.sh` are in `backend/`. The entrypoint
runs `alembic upgrade head` then serves with uvicorn workers, honoring `$PORT`.

```bash
docker build -t variorum-backend backend/
docker run --env-file .env -e PORT=8000 -e WEB_CONCURRENCY=2 -p 8000:8000 variorum-backend
```

- **Do not deploy the backend to a scale-to-zero / ephemeral platform.** Analysis,
  indexing, and ingestion run as in-process `BackgroundTasks`; they only live on
  the instance that received the request and are lost on restart. Run **one
  always-on instance** (or a few with the caveats in §5), with generous request
  timeouts.
- **Migrations:** the entrypoint applies them on boot — fine for a single
  instance. For multiple replicas, run `alembic upgrade head` once as a separate
  release step and remove it from the entrypoint to avoid concurrent-migration
  races.
- **Health checks:** liveness → `GET /health` (200 if the process is up);
  readiness → `GET /health/ready` (**200 only when the database is reachable,
  503 otherwise** — safe for a plain HTTP uptime check). `GET /api/v1/system/status`
  is the rich JSON status (DB + AI + GitHub App) for dashboards.
- **Workers/pooling:** tune `WEB_CONCURRENCY` and the DB pool (`DB_POOL_SIZE`,
  `DB_MAX_OVERFLOW`, `DB_POOL_RECYCLE`) against your Postgres `max_connections`
  (roughly `replicas × workers × pool_size` connections).

## 2. Database

- Managed PostgreSQL 17 with automated backups and TLS.
- Run `alembic upgrade head` on deploy (entrypoint or release step).
- **pgvector is optional.** If the instance has the `vector` extension, the guarded
  migration creates an HNSW-indexed vector column and semantic search uses it
  automatically. Without it, retrieval falls back to JSONB + in-process cosine —
  `alembic upgrade head` still succeeds. Set `PGVECTOR_ENABLED=false` to force the
  fallback.

## 3. Required production environment variables

Set `ENVIRONMENT=production`. The backend **refuses to start** if any of these are
insecure (default/empty):

| Variable | Notes |
|---|---|
| `SESSION_SECRET` | Long random string; signs auth cookies |
| `DATABASE_URL` | Production DB, non-default credentials |
| `CORS_ORIGINS` | Explicit frontend origin(s); never `*` |
| `GITHUB_WEBHOOK_SECRET` | Must match the GitHub App |

Also set (not fail-fast enforced, but required to function correctly):

| Variable | Notes |
|---|---|
| `BACKEND_PUBLIC_URL`, `FRONTEND_URL` | Real HTTPS URLs; used to build GitHub callback/webhook URLs |
| `GITHUB_APP_ID` / `_SLUG` / `_CLIENT_ID` / `_CLIENT_SECRET` | From the GitHub App |
| `GITHUB_APP_PRIVATE_KEY_BASE64` (or `_PATH`) | Prefer base64 in containers |
| At least one AI key | `GEMINI_API_KEY_1/2`, `DEEPSEEK_API_KEY`, `PERPLEXITY_API_KEY` |
| `SESSION_COOKIE_SAMESITE` | `lax` (Option A) or `none` (Option B) |

Optional (safe defaults): `RATE_LIMIT_ENABLED`, `PGVECTOR_ENABLED`, `DB_POOL_*`,
`APP_NAME`, `BACKEND_HOST/PORT`, model overrides. All variables are documented in
[`.env.example`](./.env.example).

## 4. Frontend (Vercel)

- Set `NEXT_PUBLIC_BACKEND_URL` (**baked in at build time** — rebuild to change).
  Option A: `/api/backend` + set `BACKEND_URL` (server env) to the backend URL.
  Option B: the backend's public URL.
- Standard `next build` / `next start`; no exotic build config. Security response
  headers ship via `next.config.mjs`.
- After changing backend URL env, **redeploy** so the value is re-baked.

## 5. Monitoring & alerting

Minimum viable, $0. Two hooks: a readiness probe and structured logs.

- **Uptime + DB/backend down:** point a free uptime monitor (UptimeRobot,
  BetterStack free tier, or your platform's built-in check) at
  `GET /health/ready` on a 1–5 min interval. It returns **503 when the database
  is unreachable or the process is down**, so a plain HTTP check alerts you.
- **Alertable log signals** — each critical failure emits a greppable line;
  forward stdout to your platform's log drain and alert on these:
  - Backend crash / unhandled error → `logger.exception` `"unhandled error on …"` (ERROR).
  - **AI fully down** (all providers failed) → `"ai all providers failed …"` (ERROR);
    per-provider fallbacks log `"ai provider failed …"` (WARNING).
  - GitHub API failure → worker/endpoint WARNING logs (e.g. `"pr analysis failed …"`,
    `"… GitHub request failed"`).
  - Database error → the readiness probe logs `"readiness check failed …"`, and any
    unhandled DB error surfaces via the catch-all ERROR above.
- **Optional next step (not installed, to stay $0/no-dep):** Sentry has a free
  tier; adding `sentry-sdk`'s FastAPI integration gives error aggregation and
  alerting on the same events with minimal code. Wire it only if you want managed
  alerting beyond log-drain rules.

## 6. Scaling notes (post-launch)

The MVP is built to run comfortably as a single always-on backend instance. To
scale horizontally you need the deferred work tracked in `PROJECT_PLAN.md`:

- A **durable job queue** (replace in-process `BackgroundTasks`) so analysis
  survives restarts and runs off the web process.
- A **shared/edge rate limiter** (the in-process limiter is per-process and
  resets on deploy).
- A DB **connection pooler** (PgBouncer / provider pooler) if running many
  replicas.

## 7. GitHub App

Follow [`SETUP.md`](./SETUP.md). For production, point the App's callback, setup,
and webhook URLs at `BACKEND_PUBLIC_URL`, and grant least-privilege permissions:
Contents R/W, Pull requests R/W, Issues read, Metadata read; subscribe to Pull
request, Push, Issues, Installation, Installation repositories.
