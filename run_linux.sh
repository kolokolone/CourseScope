#!/usr/bin/env bash
set -e

# Active un environnement virtuel local puis lance l'app Streamlit.
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN=python
else
  echo "Python n'est pas installé (python3/python introuvable)." >&2
  exit 1
fi

# Recrée l'environnement si absent ou incomplet (pas de script d'activation)
if [ ! -f ".venv/bin/activate" ]; then
  rm -rf .venv
  "$PYTHON_BIN" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

exec streamlit run CourseScope.py
