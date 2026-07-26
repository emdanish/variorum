# Local bootstrap

A quick end-to-end setup for a fresh checkout.

```bash
# From the repo root
cp .env.example .env                     # fill in AI keys + GitHub App later

docker compose up -d db                  # PostgreSQL 17 on :5432

cd backend
python -m venv .venv
# Windows PowerShell:  .venv\Scripts\Activate.ps1
# Git Bash / macOS / Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head                     # create the schema
pytest -q                                # 23 tests should pass
uvicorn app.main:app --reload --port 8000

# New terminal
cd frontend
cp .env.example .env.local
npm install
npm run dev                              # http://localhost:3000
```

Health check: <http://localhost:8000/health> and <http://localhost:8000/docs>.
