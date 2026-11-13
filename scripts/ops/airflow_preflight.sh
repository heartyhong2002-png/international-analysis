#!/usr/bin/env bash
# Loud preflight for local Airflow — never prints secret values.
# Parses KEY=VALUE without `source` (safe with unquoted multi-word values).
# Usage (from repo root):
#   ./scripts/ops/airflow_preflight.sh
#   ./scripts/ops/airflow_preflight.sh /path/to/.env.airflow
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${1:-$ROOT/.env.airflow}"
EXAMPLE="$ROOT/.env.airflow.example"

fail() {
  echo "FATAL [airflow-preflight]: $*" >&2
  echo "  Fix: cp .env.airflow.example .env.airflow  # then set real values (never commit)" >&2
  exit 1
}

if [[ ! -f "$ENV_FILE" ]]; then
  fail "missing $ENV_FILE (template: $EXAMPLE)"
fi

get_env() {
  local key="$1"
  local line raw
  line="$(grep -E "^[[:space:]]*${key}=" "$ENV_FILE" | tail -n1 || true)"
  [[ -n "$line" ]] || { echo ""; return 0; }
  raw="${line#*=}"
  raw="${raw%"${raw##*[![:space:]]}"}"
  raw="${raw#"${raw%%[![:space:]]*}"}"
  if [[ "$raw" == \"*\" || "$raw" == \'*\' ]]; then
    raw="${raw:1:${#raw}-2}"
  fi
  printf '%s' "$raw"
}

require_nonempty() {
  local key="$1"
  local val
  val="$(get_env "$key")"
  if [[ -z "$val" ]]; then
    fail "$key is empty or missing in $ENV_FILE"
  fi
}

reject_placeholder() {
  local key="$1"
  local val
  val="$(get_env "$key")"
  shift
  local p
  for p in "$@"; do
    if [[ "$val" == "$p" ]]; then
      fail "$key is still the example placeholder — set a real value in $ENV_FILE"
    fi
  done
}

require_nonempty MYSQL_PASSWORD
require_nonempty AIRFLOW__CORE__FERNET_KEY
require_nonempty POSTGRES_PASSWORD
require_nonempty _AIRFLOW_WWW_USER_PASSWORD
require_nonempty POSTGRES_USER
require_nonempty MYSQL_HOST

reject_placeholder MYSQL_PASSWORD \
  "replace-with-a-strong-password" "replace-me" "changeme" "password"
reject_placeholder AIRFLOW__CORE__FERNET_KEY \
  "replace-with-fernet-key" "replace-me"
reject_placeholder POSTGRES_PASSWORD \
  "replace-me-postgres" "airflow" "password"
reject_placeholder _AIRFLOW_WWW_USER_PASSWORD \
  "replace-me-airflow-admin" "airflow" "admin"

MYSQL_HOST_VAL="$(get_env MYSQL_HOST)"
if [[ "$MYSQL_HOST_VAL" == "host.docker.internal" || "$MYSQL_HOST_VAL" == "127.0.0.1" || "$MYSQL_HOST_VAL" == "localhost" ]]; then
  fail "MYSQL_HOST=$MYSQL_HOST_VAL will not reach compose MySQL from Airflow containers; use MYSQL_HOST=mysql on intl_analysis_net"
fi

echo "OK [airflow-preflight]: $ENV_FILE present; required secrets non-empty (values not shown)."
