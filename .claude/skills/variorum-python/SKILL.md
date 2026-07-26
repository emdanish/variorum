---
name: variorum-python
description: Use for Python engineering in the Variorum backend — typing, pytest, ruff/mypy, dependency management, and maintainable Python. Apply whenever writing or changing backend/ Python code.
---

# Variorum Python engineering

Python **3.11+**. Everything free/open-source.

## Typing
- `from __future__ import annotations` at the top of every module.
- Full type hints on all functions; no bare `Any` unless truly dynamic. Use `X | None`, `list[X]`, `StrEnum`.
- `mypy app` must stay **green** (config in `backend/pyproject.toml`, `pydantic.mypy` plugin on).

## Tooling (run before every commit)
```bash
cd backend
./.venv/Scripts/python.exe -m ruff check .     # lint + import order (line length 100)
./.venv/Scripts/python.exe -m mypy app         # types
./.venv/Scripts/python.exe -m pytest           # tests
```
- `ruff check --fix .` auto-fixes imports/format. Ruff config lives in `pyproject.toml` (note the deliberate `UP037` ignore for SQLAlchemy `Mapped["X"]` forward refs).

## Dependencies & environment
- `requirements.txt` (runtime, pinned) + `requirements-dev.txt` (adds pytest/ruff/mypy). venv at `backend/.venv`.
- **Add a dependency only when it earns its place.** Prefer the stdlib and what's already vendored. Everything must be free/open-source (see the $0 rule in CLAUDE.md).

## Style
- Self-documenting names; **no comments that restate the code**. Comments explain *why* / non-obvious decisions only.
- Small, pure, injectable functions; keep side effects (DB, HTTP) at the edges.

See `variorum-testing` for test structure and `variorum-backend` for architecture.
