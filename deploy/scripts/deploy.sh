#!/usr/bin/env sh
set -eu

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example. Review secrets before production use."
fi

mkdir -p logs/nginx logs/backend logs/postgres deploy/nginx/ssl

if [ ! -f deploy/nginx/ssl/server.crt ] || [ ! -f deploy/nginx/ssl/server.key ]; then
  openssl req -x509 -nodes -newkey rsa:4096 -days 3650 \
    -keyout deploy/nginx/ssl/server.key \
    -out deploy/nginx/ssl/server.crt \
    -subj "/CN=manage-factory.internal/O=Oilfield Internal/C=CN" \
    -addext "subjectAltName=DNS:manage-factory.internal,DNS:localhost,IP:127.0.0.1"
fi

docker compose -f docker-compose.yml up -d --build
docker compose -f docker-compose.yml ps

echo "DMZ HTTPS entry: https://localhost/"
echo "Grafana: https://localhost/grafana/"
echo "Backend health: https://localhost/health"
