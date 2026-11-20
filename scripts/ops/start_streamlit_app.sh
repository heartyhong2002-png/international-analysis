#!/usr/bin/env bash
# Start root Streamlit control center on loopback only (127.0.0.1:8501).
# Matches scripts/console/app.py HOST binding — not for public deploy.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

PYTHON="${ROOT}/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="$(command -v python3 || command -v python)"
fi

echo "OK: Streamlit control center → http://127.0.0.1:8501 (loopback only)"
exec "$PYTHON" -m streamlit run app.py \
  --server.address 127.0.0.1 \
  --server.headless true \
  --browser.serverAddress 127.0.0.1
