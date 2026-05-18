#!/usr/bin/env bash
# Production launcher for md-chat-ai under gunicorn.
#
# Usage:
#   ./scripts/gunicorn-run.sh                 # foreground
#   AI_LAYER_WORKERS=4 ./scripts/gunicorn-run.sh
#
# Designed to be the Docker CMD, the systemd ExecStart, or a manual launch.
# Resolves its own directory so symlinks / pwd surprises do not break paths.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONFIG_FILE="${APP_DIR}/gunicorn.conf.py"

if [[ ! -f "${CONFIG_FILE}" ]]; then
  echo "[gunicorn-run] FATAL: gunicorn.conf.py not found at ${CONFIG_FILE}" >&2
  exit 1
fi

# Activate local virtualenv if present and not already active.
if [[ -z "${VIRTUAL_ENV:-}" && -f "${APP_DIR}/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "${APP_DIR}/.venv/bin/activate"
fi

# Resolve gunicorn binary — prefer venv copy, fall back to PATH.
if [[ -x "${APP_DIR}/.venv/bin/gunicorn" ]]; then
  GUNICORN_BIN="${APP_DIR}/.venv/bin/gunicorn"
elif command -v gunicorn >/dev/null 2>&1; then
  GUNICORN_BIN="$(command -v gunicorn)"
else
  echo "[gunicorn-run] FATAL: gunicorn not found; pip install -e '.[dev]' first" >&2
  exit 1
fi

# `exec` so signals (SIGTERM from Docker / systemd) reach gunicorn directly
# without an extra shell intermediary swallowing them.
cd "${APP_DIR}"
exec "${GUNICORN_BIN}" \
  --config "${CONFIG_FILE}" \
  "md_chat_ai.api:create_app()"
