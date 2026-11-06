#!/usr/bin/env bash
# Ensure shared Docker network for MySQL + Airflow (both compose files use external: true).
set -euo pipefail
NET="${1:-intl_analysis_net}"
if docker network inspect "$NET" >/dev/null 2>&1; then
  echo "OK [network]: $NET already exists"
  exit 0
fi
echo "==> creating Docker network $NET (external for mysql + airflow compose)"
docker network create "$NET"
echo "OK [network]: created $NET"
