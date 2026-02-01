from __future__ import annotations

"""Parsing helpers shared across UI and backend."""


def parse_km_list(raw: str) -> list[float]:
    """Parse comma-separated distances (km).

    Example inputs: "5,10,21.1", "5 km, 10km".
    """

    distances: list[float] = []
    for part in raw.split(","):
        text = part.strip().lower().replace("km", "")
        if not text:
            continue
        try:
            val = float(text)
        except ValueError:
            continue
        if val >= 0:
            distances.append(val)
    return distances
