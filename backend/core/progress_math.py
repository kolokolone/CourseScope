"""Fonctions mathématiques utilitaires pour les endpoints progress."""

import math
from datetime import datetime, timedelta


def dedupe_xy(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Déduplique et moyenne les Y pour des X identiques. Trié par X."""
    if not points:
        return []
    grouped: dict[float, list[float]] = {}
    for x, y in points:
        grouped.setdefault(float(x), []).append(float(y))
    out = []
    for x in sorted(grouped.keys()):
        vals = grouped[x]
        out.append((x, float(sum(vals) / len(vals))))
    return out


def interp_linear(points: list[tuple[float, float]], target_x: float) -> float | None:
    """Interpolation linéaire entre les points (x, y) triés par X.

    Retourne None si target_x hors bornes ou si les données sont invalides.
    """
    if not points:
        return None
    pts = dedupe_xy(points)
    if not pts:
        return None
    x0 = pts[0][0]
    x1 = pts[-1][0]
    if target_x < x0 or target_x > x1:
        return None
    for i in range(len(pts) - 1):
        xa, ya = pts[i]
        xb, yb = pts[i + 1]
        if xa == xb:
            continue
        if xa <= target_x <= xb:
            ratio = (target_x - xa) / (xb - xa)
            y = ya + ratio * (yb - ya)
            return float(y) if math.isfinite(y) else None
    if target_x == pts[-1][0]:
        return float(pts[-1][1])
    return None


def compute_streaks(active_dates: set[str], reference_date: str) -> tuple[int, int]:
    """Calcule la plus longue streak et la streak courante.

    Retourne (longest_streak, current_streak).
    """
    if not active_dates:
        return (0, 0)

    parsed: set = set()
    for d in active_dates:
        try:
            parsed.add(datetime.strptime(str(d), "%Y-%m-%d").date())
        except ValueError:
            continue

    if not parsed:
        return (0, 0)

    sorted_dates = sorted(parsed)

    longest_streak = 1
    current_run = 1
    for i in range(1, len(sorted_dates)):
        if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
            current_run += 1
        else:
            current_run = 1
        if current_run > longest_streak:
            longest_streak = current_run

    current_streak = 0
    try:
        ref_date = datetime.strptime(reference_date, "%Y-%m-%d").date()
    except ValueError:
        return (longest_streak, 0)

    check_date = ref_date
    while check_date in parsed:
        current_streak += 1
        check_date = check_date - timedelta(days=1)

    return (longest_streak, current_streak)
