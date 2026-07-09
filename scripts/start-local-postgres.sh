#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

python_bin="${PYTHON_BIN:-}"
if [[ -z "$python_bin" ]]; then
  if command -v python3.12 >/dev/null 2>&1; then
    python_bin="python3.12"
  else
    python_bin="python3"
  fi
fi

export POSTGRES_SERVER="${POSTGRES_SERVER:-127.0.0.1}"
export POSTGRES_PORT="${POSTGRES_PORT:-5432}"
export POSTGRES_USER="${POSTGRES_USER:-$(whoami)}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"
export POSTGRES_DB="${POSTGRES_DB:-manage_factory}"
export PGPASSWORD="$POSTGRES_PASSWORD"
export DATABASE_URL=""
export JWT_SECRET_KEY="${JWT_SECRET_KEY:-local-dev-jwt-secret-change-me}"
export ADMIN_INITIAL_PASSWORD="${ADMIN_INITIAL_PASSWORD:-ChangeMe_123!}"
export CORS_ALLOW_ORIGINS="${CORS_ALLOW_ORIGINS:-http://127.0.0.1:5173,http://localhost:5173}"
export REDIS_URL="${REDIS_URL:-}"

backend_port="${BACKEND_PORT:-8000}"
frontend_port="${FRONTEND_PORT:-5173}"
logs_dir="$repo_root/.local/logs"
pids_dir="$repo_root/.local/pids"

mkdir -p "$logs_dir" "$pids_dir"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

port_is_listening() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

require_command "$python_bin"
require_command psql
require_command createdb
require_command npm

if [[ ! -x ".venv/bin/python" ]]; then
  "$python_bin" -m venv .venv
fi

if [[ "${SKIP_BACKEND_INSTALL:-0}" != "1" ]]; then
  .venv/bin/python -m pip install -r requirements.txt
fi

if [[ "${SKIP_FRONTEND_INSTALL:-0}" != "1" && ! -d "frontend/node_modules" ]]; then
  (cd frontend && npm install)
fi

if ! psql \
  -h "$POSTGRES_SERVER" \
  -p "$POSTGRES_PORT" \
  -U "$POSTGRES_USER" \
  -d postgres \
  -tAc "SELECT 1 FROM pg_database WHERE datname='${POSTGRES_DB}'" | grep -q 1; then
  createdb \
    -h "$POSTGRES_SERVER" \
    -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    "$POSTGRES_DB"
fi

.venv/bin/alembic upgrade head
.venv/bin/python -m app.db.seed

if port_is_listening "$backend_port"; then
  echo "Backend port $backend_port is already in use; leaving existing process running."
else
  nohup .venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port "$backend_port" \
    > "$logs_dir/backend.log" 2>&1 &
  echo "$!" > "$pids_dir/backend.pid"
  echo "Backend started: http://127.0.0.1:$backend_port"
fi

if port_is_listening "$frontend_port"; then
  echo "Frontend port $frontend_port is already in use; leaving existing process running."
else
  (
    cd frontend
    nohup npm run dev -- --port "$frontend_port" > "$logs_dir/frontend.log" 2>&1 &
    echo "$!" > "$pids_dir/frontend.pid"
  )
  echo "Frontend started: http://127.0.0.1:$frontend_port"
fi

echo "PostgreSQL database: ${POSTGRES_USER}@${POSTGRES_SERVER}:${POSTGRES_PORT}/${POSTGRES_DB}"
echo "Backend health: http://127.0.0.1:${backend_port}/health"
echo "API docs: http://127.0.0.1:${backend_port}/docs"
echo "Logs: $logs_dir"
