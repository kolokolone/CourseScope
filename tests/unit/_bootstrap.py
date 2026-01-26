from __future__ import annotations

import sys
from pathlib import Path


def ensure_project_on_path() -> None:
    project_dir = Path(__file__).resolve().parents[2]
    if str(project_dir) not in sys.path:
        sys.path.insert(0, str(project_dir))
