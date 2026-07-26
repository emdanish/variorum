# Variorum developer commands.
# On Windows, run these from Git Bash / WSL, or invoke the underlying commands
# directly (see README).

.PHONY: help db-up db-down backend-install backend-dev migrate revision \
        backend-test backend-lint frontend-install frontend-dev fmt

help:
	@echo "Variorum make targets:"
	@echo "  db-up             Start local PostgreSQL 17 (docker compose)"
	@echo "  db-down           Stop local PostgreSQL"
	@echo "  backend-install   Create venv and install backend deps"
	@echo "  backend-dev       Run FastAPI with autoreload"
	@echo "  migrate           Apply Alembic migrations"
	@echo "  revision m=...    Autogenerate a migration"
	@echo "  backend-test      Run backend tests"
	@echo "  backend-lint      Run ruff + mypy"
	@echo "  frontend-install  Install frontend deps"
	@echo "  frontend-dev      Run Next.js dev server"

db-up:
	docker compose up -d db

db-down:
	docker compose down

backend-install:
	cd backend && python -m venv .venv && . .venv/bin/activate && \
		pip install -r requirements.txt

backend-dev:
	cd backend && . .venv/bin/activate && \
		uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

migrate:
	cd backend && . .venv/bin/activate && alembic upgrade head

revision:
	cd backend && . .venv/bin/activate && alembic revision --autogenerate -m "$(m)"

backend-test:
	cd backend && . .venv/bin/activate && pytest -q

backend-lint:
	cd backend && . .venv/bin/activate && ruff check . && mypy app

frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev
