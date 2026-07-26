#!/usr/bin/env bash
# Starts the Variorum backend (FastAPI). For macOS/Linux/Git Bash.
set -e
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root/backend"

# Resolve the venv python (Windows Git Bash uses Scripts/, Unix uses bin/).
if [ -x ".venv/Scripts/python.exe" ]; then PY=".venv/Scripts/python.exe"
elif [ -x ".venv/bin/python" ]; then PY=".venv/bin/python"
else
  echo "Creating virtual environment and installing dependencies..."
  python -m venv .venv
  if [ -x ".venv/Scripts/python.exe" ]; then PY=".venv/Scripts/python.exe"; else PY=".venv/bin/python"; fi
  "$PY" -m pip install --upgrade pip
  "$PY" -m pip install -r requirements.txt
fi

echo "Applying database migrations..."
"$PY" -m alembic upgrade head

echo "Starting backend on http://localhost:8000  (docs at /docs)"
"$PY" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
