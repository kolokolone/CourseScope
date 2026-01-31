#!/usr/bin/env bash
set -euo pipefail

# CourseScope launcher (v1.1.24+)
# Starts FastAPI (uvicorn) + Next.js dev server.

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN=python
else
  echo "Python n'est pas installe (python3/python introuvable)." >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "Node.js (npm) n'est pas installe. Installe Node.js pour lancer le frontend." >&2
  exit 1
fi

# Create/activate venv
if [ ! -f ".venv/bin/activate" ]; then
  rm -rf .venv
  "$PYTHON_BIN" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt

API_PID=""
cleanup() {
  if [ -n "${API_PID}" ] && kill -0 "${API_PID}" >/dev/null 2>&1; then
    echo "[INFO] Arret API (uvicorn pid=${API_PID})..."
    kill "${API_PID}" >/dev/null 2>&1 || true
    wait "${API_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "[INFO] Demarrage API: http://localhost:8000"
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000 &
API_PID=$!

echo "[INFO] Demarrage Frontend: http://localhost:3000"
cd frontend
if [ ! -d "node_modules" ]; then
  if [ -f "package-lock.json" ]; then
    npm ci
  else
    npm install
  fi
fi

echo "[INFO] Ouvre: http://localhost:3000"
npm run dev
