from __future__ import annotations

"""History manipulation helpers (pure functions).

Storage remains a UI concern in v1.1 (e.g., Streamlit session_state).
"""

from typing import Any


def upsert_history(history: list[dict[str, Any]], entry: dict[str, Any], max_items: int = 0) -> None:
    """Insert an entry at the front, dedupe by name, optionally trim."""

    name = entry.get("name")
    if name is not None:
        history[:] = [item for item in history if item.get("name") != name]
    history.insert(0, entry)
    if max_items:
        del history[max_items:]
