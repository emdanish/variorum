---
name: variorum-testing
description: Use when writing or changing tests for Variorum, or adding a feature that needs coverage. Covers unit/integration/API testing, the test fixtures, mocking patterns, and TDD.
---

# Variorum testing conventions

Framework: **pytest** (`asyncio_mode=auto`). Tests live in `backend/tests/`. Every feature ships with tests; the suite + `mypy` + `ruff` must be green before commit.

## Layers
- **Unit** — pure logic with no I/O: AI fallback ordering, drift/risk assessors, retrieval, path helpers. Use fakes, not network.
- **Integration** — real Postgres test DB `variorum_test` (5432). `conftest.py` gives a `db_session` wrapped in an outer transaction that's **always rolled back** (`join_transaction_mode="create_savepoint"`), so tests are isolated even though services call `commit()`.
- **API** — `TestClient` with dependency overrides (`client`, `authed_client` fixtures). No true end-to-end yet (documented).

## Mocking patterns
- AI: `tests/_fakes.py::FakeAI` (implements `complete` / `complete_structured` / `available`).
- GitHub / embeddings: `httpx.MockTransport` passed via the client's `transport=` param (see `GitHubClient`, `EmbeddingService`).
- Workers accept injectable `db` / `pr_files` / `client` / `ai` / `items` so the full path runs without network.

## Rules & gotchas
- Hermetic config: build settings with `Settings(_env_file=None, ...)` so the real `.env` never leaks in.
- **Don't import a function named `test_*` into a test module** — pytest tries to collect it as a test. Alias it (e.g. `import ... as build_test_path`).
- Seed unique ids when a test creates multiple installations/repos (unique constraints).
- TDD is encouraged for pure services (assessors, retrieval, scoring); write the fake + assertion first.

## Commands
```bash
cd backend && ./.venv/Scripts/python.exe -m pytest -q
```
