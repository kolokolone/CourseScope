from __future__ import annotations

"""Helpers de manipulation d'historique (fonctions pures).

Le stockage reste un sujet UI en v1.1.4 (ex: etat de session UI).
"""

from typing import Any


def upsert_history(history: list[dict[str, Any]], entry: dict[str, Any], max_items: int = 0) -> None:
    """Insere une entree en tete, dedupe par nom, et tronque optionnellement."""

    name = entry.get("name")
    if name is not None:
        history[:] = [item for item in history if item.get("name") != name]
    history.insert(0, entry)
    if max_items:
        del history[max_items:]
