# Production image for the Variorum backend (FastAPI).
# Build context is the backend/ directory:  docker build -t variorum-backend backend/
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first for better layer caching. All runtime deps ship manylinux
# wheels (psycopg[binary], tree-sitter, cryptography), so no build toolchain.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# entrypoint runs migrations then starts the server, honoring $PORT.
CMD ["sh", "./entrypoint.sh"]
