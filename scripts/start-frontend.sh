#!/usr/bin/env bash
# Starts the Variorum frontend (Next.js dev server). For macOS/Linux/Git Bash.
set -e
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root/frontend"

if [ ! -d node_modules ]; then
  echo "Installing frontend dependencies..."
  npm install
fi

echo "Starting frontend on http://localhost:3000"
npm run dev
