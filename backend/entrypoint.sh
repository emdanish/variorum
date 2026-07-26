#!/bin/sh
# Apply database migrations, then serve. For multi-replica deploys, run
# `alembic upgrade head` once as a separate release step and remove it here to
# avoid concurrent-migration races.
set -e

alembic upgrade head

exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-2}"
