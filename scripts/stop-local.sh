#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
pids_dir="$repo_root/.local/pids"

stop_pid_file() {
  local name="$1"
  local pid_file="$pids_dir/$name.pid"

  if [[ ! -f "$pid_file" ]]; then
    return
  fi

  local pid
  pid="$(cat "$pid_file")"
  if [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1; then
    kill "$pid"
    echo "Stopped $name process $pid"
  fi
  rm -f "$pid_file"
}

stop_pid_file backend
stop_pid_file frontend

echo "Local managed processes stopped."
