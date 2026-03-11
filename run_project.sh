#!/usr/bin/env bash
set -euo pipefail

PYTHON="python"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON=".venv/bin/python"
fi

if [[ "${1:-}" == "--dev" ]]; then
  exec "$PYTHON" ./run_project.py --dev
else
  exec "$PYTHON" ./run_project.py
fi
