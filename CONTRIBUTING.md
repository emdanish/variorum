# Contributing to Variorum

Thanks for your interest in contributing! This guide covers the development setup,
coding standards, and the pull request process.

## Development setup

See the [README](./README.md#local-development) for full setup. In short:

```bash
cp .env.example .env          # fill in values

# Backend
cd backend
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

The backend needs a PostgreSQL 17 database. The test suite uses a separate
`variorum_test` database (see `backend/tests/conftest.py`); DB-dependent tests skip
automatically when it is not reachable.

## Coding standards

- **Self-documenting code.** Clear names over cleverness. Comments explain *why*, never
  restate *what* the code does.
- **Python** — line length 100, `from __future__ import annotations`, `StrEnum` for
  enums, full type hints. Typed SQLAlchemy models (`Mapped[...]`).
- **TypeScript** — strict mode, no `any` escapes, functional components, Tailwind for
  styling, shadcn-style components.
- **Security** — ownership-scope every resource; never commit or log secrets; verify
  webhook signatures; keep generated changes behind a human review gate.
- **Dependencies** — add one only when it clearly earns its place and is free/open
  source. This project has a hard **$0-cost** constraint (no paid APIs/SaaS/infra).

## The green gate

Before opening a pull request, both stacks must pass:

**Backend**
```bash
cd backend
ruff check .
mypy app
pytest -q
```

**Frontend**
```bash
cd frontend
npm run lint
npx tsc --noEmit
```

> Do **not** run `next build` while `next dev` is running — it corrupts the shared
> `.next` directory. Verify with `tsc --noEmit` + `npm run lint` instead.

Every behavioral change ships with tests.

## Database migrations

Schema changes go through Alembic:

```bash
cd backend
alembic revision -m "short description"   # then edit the generated migration
alembic upgrade head
```

For a new table that reuses an existing PG enum, set `create_type=False`. For a
`NOT NULL` column on an existing table, add it with a `server_default` first, then drop
the default.

## Pull request process

1. Branch from `main` (e.g. `feature/…`, `fix/…`, `docs/…`).
2. Make focused changes with clear, [conventional](https://www.conventionalcommits.org/)
   commit messages (`feat:`, `fix:`, `docs:`, `chore:`, `security:`, `test:`).
3. Ensure the green gate passes and add tests for new behavior.
4. Update documentation (README / `PROJECT_PLAN.md` / ADRs) when behavior or conventions
   change.
5. Open a pull request describing **what** changed and **why**. Link related issues.

## Reporting bugs and security issues

- **Bugs / features** — open a GitHub issue with clear reproduction steps.
- **Security vulnerabilities** — do **not** open a public issue; follow
  [`SECURITY.md`](./SECURITY.md).
