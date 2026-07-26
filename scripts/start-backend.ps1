# Starts the Variorum backend (FastAPI). Creates the venv and installs deps on
# first run, applies DB migrations, then serves on http://localhost:8000.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location "$root\backend"

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment and installing dependencies..."
    python -m venv .venv
    .\.venv\Scripts\python.exe -m pip install --upgrade pip
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
}

Write-Host "Applying database migrations..."
.\.venv\Scripts\python.exe -m alembic upgrade head

Write-Host "Starting backend on http://localhost:8000  (docs at /docs)"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
