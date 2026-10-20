#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ "${E2E_EXTERNAL_SERVICES:-0}" != "1" ]]; then
  docker compose up -d postgres redis
  until docker compose exec -T postgres pg_isready -U lexpilot -d lexpilot >/dev/null 2>&1; do
    sleep 1
  done
  until docker compose exec -T redis redis-cli ping >/dev/null 2>&1; do
    sleep 1
  done
fi

cd backend
uv run alembic upgrade head
uv run python -m app.cli seed-dev
exec uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
