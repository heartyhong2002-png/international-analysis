#!/usr/bin/env bash
# Start analysis MySQL stack on shared external network intl_analysis_net.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [[ ! -f "$ROOT/.env" ]]; then
  echo "FATAL: missing .env — cp .env.example .env and set MYSQL_PASSWORD (never commit)" >&2
  exit 1
fi

"$ROOT/scripts/ops/ensure_intl_network.sh" intl_analysis_net

echo "==> mysql + phpmyadmin"
docker compose -f docker-compose.mysql.yml --env-file .env up -d

echo "OK: MySQL on 127.0.0.1 (host) / mysql (intl_analysis_net for Airflow)"
