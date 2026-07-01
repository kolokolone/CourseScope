#!/usr/bin/env bash
set -euo pipefail

# CourseScope launcher (dev + docker)
# - Dev mode (default): venv + pip install + uvicorn --reload + next dev
# - Docker mode (--docker or COURSESCOPE_MODE=docker): runtime only, no installs

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

MODE="dev"
if [ "${COURSESCOPE_MODE:-}" = "docker" ]; then
  MODE="docker"
fi

for arg in "$@"; do
  case "$arg" in
    --docker)
      MODE="docker"
      ;;
    --dev)
      MODE="dev"
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      echo "Usage: ./run_linux.sh [--dev|--docker]" >&2
      exit 1
      ;;
  esac
done

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN=python
else
  echo "Python is not installed (python3/python not found)." >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "Node.js (npm) is not installed. Install Node.js to run the frontend." >&2
  exit 1
fi

API_PID=""
cleanup() {
  if [ -n "${API_PID}" ] && kill -0 "${API_PID}" >/dev/null 2>&1; then
    echo "[INFO] Stopping API (uvicorn pid=${API_PID})..."
    kill "${API_PID}" >/dev/null 2>&1 || true
    wait "${API_PID}" >/dev/null 2>&1 || true
  fi
}

on_term() {
  echo "[INFO] Received termination signal, shutting down..."
  exit 0
}

trap cleanup EXIT
trap on_term INT TERM

wait_for_backend_health() {
  "$PYTHON_BIN" - <<'PY'
import sys
import time
import urllib.request

url = "http://127.0.0.1:8000/health"
deadline = time.time() + 45.0

while time.time() < deadline:
    try:
        with urllib.request.urlopen(url, timeout=2.0) as response:
            if response.status == 200:
                sys.exit(0)
    except Exception:
        pass
    time.sleep(0.5)

sys.exit(1)
PY
}

if [ "$MODE" = "docker" ]; then
  echo "[INFO] Running in docker mode"

  echo "[INFO] Starting API: http://127.0.0.1:8000"
  "$PYTHON_BIN" -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 --forwarded-allow-ips='*' &
  API_PID=$!

  if wait_for_backend_health; then
    echo "[INFO] API healthcheck is ready"
  else
    echo "[ERROR] API healthcheck did not become ready in time" >&2
    exit 1
  fi

  echo "[INFO] Starting Frontend (production): http://0.0.0.0:3000"
  cd frontend
  PORT=3000 node server.js
  exit 0
fi

echo "[INFO] Running in dev mode"

if [ ! -f ".venv/bin/activate" ]; then
  rm -rf .venv
  "$PYTHON_BIN" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt

echo "[INFO] Starting API (reload): http://localhost:8000"
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000 &
API_PID=$!

echo "[INFO] Starting Frontend (dev): http://localhost:3000"
cd frontend
if [ ! -d "node_modules" ]; then
  if [ -f "package-lock.json" ]; then
    npm ci
  else
    npm install
  fi
fi

echo "[INFO] Open: http://localhost:3000"
npm run dev
