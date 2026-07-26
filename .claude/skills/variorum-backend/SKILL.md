---
name: variorum-backend
description: Use when working on the Variorum backend — FastAPI routes, API design, SQLAlchemy models, Alembic migrations, services, or workers under backend/app. Covers API/DB design and clean backend patterns.
---

# Variorum backend conventions

Stack: **FastAPI · Pydantic v2 · SQLAlchemy 2.0 · Alembic · PostgreSQL 17 · httpx**. All free/open-source.

## Layering (keep it clean)
- `app/main.py` — app factory (`create_app`), middleware, health.
- `app/api/routes/` — thin HTTP handlers; `app/api/deps.py` — dependency providers (`get_db`, `get_current_user`, `get_ai_service`, `get_github_auth`).
- `app/services/` — business logic (GitHub, indexer, analysis, qa, knowledge). `app/workers/` — background jobs.
- `app/models/` — SQLAlchemy models; `app/schemas/` — Pydantic request/response; `app/ai/` — provider-agnostic AI layer.
- **Routes stay thin**; real logic lives in services/workers so it's unit-testable.

## API design
- Versioned under `/api/v1`. Pydantic models for every request and response (`response_model=`).
- Errors via `HTTPException` with correct status (400/401/403/404/409/502/503). Map upstream AI/GitHub failures to 502/503 (see the ask / open-pr endpoints).
- **Every resource is ownership-scoped** — filter by the current user's installations (`_get_owned_repo`, `_owned_finding`). Never trust an id from the client without an ownership check.

## Database & migrations
- SQLAlchemy 2.0 typed `Mapped[...]` columns. Enums are `StrEnum` (see `models/enums.py`).
- Migrations via Alembic (`alembic revision --autogenerate` → **review it**). Don't edit an already-applied migration.
- Shared PG enums: when a new table reuses an existing enum, set `create_type=False` on the column in the migration (otherwise it errors with "type already exists").
- Idempotency: unique constraints for "one X per Y" (e.g. `generated_prs.risk_finding_id`), and upsert-by-natural-key in services.

## Workers / background
- `BackgroundTasks` for now (documented limitation → durable queue later). Workers accept **injectable `db` / `client` / `ai`** so they're testable without network, and isolate per-item failures (one bad item never fails the whole job).

Uses `variorum-python` (typing/testing/tooling) and `variorum-security` conventions.
