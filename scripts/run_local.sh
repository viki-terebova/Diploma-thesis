#!/usr/bin/env bash
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

cd "$ROOT_DIR"

echo "Starting PostgreSQL via Docker Compose..."
docker compose up postgres -d

cd "$BACKEND_DIR"

echo "Running database migrations..."
alembic upgrade head

echo "Starting Ariadne locally on http://127.0.0.1:8000 ..."
uvicorn ariadne_doc_assistant.main:app --reload --port 8000
