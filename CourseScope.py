import sys
from pathlib import Path

import streamlit as st

backend_dir = Path(__file__).resolve().parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from ui.layout import render_app


if __name__ == "__main__":
    render_app()
