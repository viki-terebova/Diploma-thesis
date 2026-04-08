#!/usr/bin/env bash
set -eu

cd "$(dirname "$0")/../backend"

if [ ! -d ".venv" ]; then
  python -m venv .venv
fi

if [ -f ".venv/bin/activate" ]; then
  . .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
  . .venv/Scripts/activate
else
  echo "Could not find a virtual environment activation script in .venv/"
  exit 1
fi

if ! python -c "import fastapi" >/dev/null 2>&1; then
  pip install --upgrade pip
  pip install -e ".[dev]"
fi

alembic upgrade head
uvicorn ariadne_doc_assistant.main:app --reload --port 8000
