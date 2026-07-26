# Production Readiness Checklist

Work through this checklist before deploying Variorum to a public/production
environment. It complements [`SECURITY.md`](./SECURITY.md) and
[`SETUP.md`](./SETUP.md).

## Environment & configuration

- [ ] `ENVIRONMENT=production` is set.
- [ ] `SESSION_SECRET` is a long, random value (not the dev default). *The backend
      refuses to start in production otherwise.*
- [ ] `DATABASE_URL` points at the production database with **non-default** credentials.
- [ ] `CORS_ORIGINS` is an explicit allowlist of your real frontend origin(s) — never
      `*`.
- [ ] `BACKEND_PUBLIC_URL` and `FRONTEND_URL` are the real HTTPS URLs.
- [ ] At least one AI provider key is set; verify with `scripts/check_ai.py`.
- [ ] `.env` and all secret files are present on the host but **not** in the image/repo.

## Security

- [ ] TLS terminates in front of the app (HSTS is emitted in production).
- [ ] Baseline security headers verified on responses (`X-Content-Type-Options`,
      `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`).
- [ ] Session cookies are `Secure` (automatic when `is_production`) and `HttpOnly`.
- [ ] Edge/gateway rate limiting configured in addition to the in-process limiter
      (the in-process limiter is single-process and resets on restart).
- [ ] `git log` / repository scanned — no secrets committed (`.env`, `*.pem`, `*.key`).
- [ ] Dependencies audited (`npm audit`, and a Python audit such as `pip-audit`); no
      known high/critical vulnerabilities left unaddressed.

## GitHub App

- [ ] App requests only least-privilege permissions:
      **Contents: R/W, Pull requests: R/W, Issues: Read, Metadata: Read**.
- [ ] Subscribed to the required events: *Pull request, Push, Issues, Installation,
      Installation repositories*.
- [ ] `GITHUB_WEBHOOK_SECRET` is set (production startup requires it) and matches the
      value configured on the App.
- [ ] Private key supplied via `GITHUB_APP_PRIVATE_KEY_BASE64` or a secured file path;
      the `.pem` is never committed.
- [ ] Webhook URL points at the production backend and is reachable.

## Database

- [ ] Migrations applied: `alembic upgrade head`.
- [ ] Automated backups configured.
- [ ] Connection over TLS; least-privilege database role.
- [ ] (Scale) Plan the pgvector upgrade path for semantic search — see
      `PROJECT_PLAN.md`. The MVP stores embeddings as JSONB and ranks in-process.

## Reliability & operations

- [ ] Structured logs shipped to a log store; no secrets/tokens/payloads in logs.
- [ ] Health check wired to `/health`; readiness reflected by `/api/v1/system/status`.
- [ ] Background work: the MVP uses FastAPI `BackgroundTasks` (in-process). For real
      load, plan a durable queue (documented as deferred in `PROJECT_PLAN.md`).
- [ ] Error monitoring/alerting in place.
- [ ] Uvicorn runs behind a process manager / reverse proxy; `backend_host` bound
      appropriately for the network topology.

## Testing & CI

- [ ] Backend green: `ruff check .`, `mypy app`, `pytest -q`.
- [ ] Frontend green: `npm run lint`, `tsc --noEmit`, `next build`.
- [ ] Smoke test the full flow: sign in → connect a repo → analyze a PR → review a
      generated PR.
- [ ] Verify no regression in existing user flows.

## Post-deploy

- [ ] Confirm sign-in works end-to-end against the production GitHub App.
- [ ] Confirm a webhook delivery is received and verified.
- [ ] Confirm AI fallback works if the primary provider is unavailable.
