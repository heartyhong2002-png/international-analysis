#!/usr/bin/env bash
# Start local Airflow with loud secrets preflight + shared MySQL network.
# Never commits or prints secret values.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

echo "==> airflow preflight"
"$ROOT/scripts/ops/airflow_preflight.sh" "$ROOT/.env.airflow"

if ! docker network inspect intl_analysis_net >/dev/null 2>&1; then
  echo "==> creating Docker network intl_analysis_net (MySQL stack also creates this)"
  docker network create intl_analysis_net
fi

echo "==> airflow-init"
docker compose --env-file .env.airflow up airflow-preflight airflow-init

echo "==> airflow webserver + scheduler"
docker compose --env-file .env.airflow up -d

echo "OK: Airflow up. UI http://127.0.0.1:8080  (login from .env.airflow — not printed)"
