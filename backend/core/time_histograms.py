"""Shared time histograms for theoretical traces and recorded activities."""

from __future__ import annotations

import math

import numpy as np


PACE_BIN_WIDTH_S = 15.0
DISPLAY_MIN_BIN_TIME_S = 90.0
DISPLAY_MAX_PACE_FACTOR = 1.75
GRADE_DISPLAY_LIMIT_PCT = 20.0


def _format_pace_bin(floor_s: float) -> str:
    end_s = floor_s + PACE_BIN_WIDTH_S
    return f"{int(floor_s // 60)}:{int(floor_s % 60):02d}-{int(end_s // 60)}:{int(end_s % 60):02d}/km"


def build_pace_histogram(
    pace_s_per_km: np.ndarray,
    segment_time_s: np.ndarray,
    reference_pace_s_per_km: float,
) -> dict[str, object]:
    pace = np.asarray(pace_s_per_km, dtype=float)
    times = np.asarray(segment_time_s, dtype=float)
    floors = np.floor(pace / PACE_BIN_WIDTH_S) * PACE_BIN_WIDTH_S
    grouped: dict[float, float] = {}
    for floor_s, seconds in zip(floors, times):
        if math.isfinite(float(floor_s)) and math.isfinite(float(seconds)) and seconds >= 0:
            grouped[float(floor_s)] = grouped.get(float(floor_s), 0.0) + float(seconds)
    complete = [
        {
            "pace_bin_floor_s_per_km": floor_s,
            "pace_bin_ceiling_s_per_km": floor_s + PACE_BIN_WIDTH_S,
            "label": _format_pace_bin(floor_s),
            "time_s": seconds,
        }
        for floor_s, seconds in sorted(grouped.items())
    ]
    display = [
        item
        for item in complete
        if float(item["time_s"]) >= DISPLAY_MIN_BIN_TIME_S
        and float(item["pace_bin_floor_s_per_km"])
        <= float(reference_pace_s_per_km) * DISPLAY_MAX_PACE_FACTOR
    ]
    total = float(sum(float(item["time_s"]) for item in complete))
    displayed = float(sum(float(item["time_s"]) for item in display))
    return {
        "unit": "s",
        "bin_width_s_per_km": PACE_BIN_WIDTH_S,
        "display_min_time_s": DISPLAY_MIN_BIN_TIME_S,
        "display_max_pace_factor": DISPLAY_MAX_PACE_FACTOR,
        "complete_classes": complete,
        "display_classes": display,
        "total_time_s": total,
        "displayed_time_s": displayed,
        "hidden_time_s": total - displayed,
    }


def build_grade_histogram(
    grade_pct: np.ndarray,
    segment_distance_km: np.ndarray,
    segment_time_s: np.ndarray,
) -> dict[str, object]:
    grades = np.asarray(grade_pct, dtype=float)
    distances = np.asarray(segment_distance_km, dtype=float)
    times = np.asarray(segment_time_s, dtype=float)
    keys: list[float | str] = []
    for grade in grades:
        if grade <= -GRADE_DISPLAY_LIMIT_PCT:
            keys.append("low_overflow")
        elif grade >= GRADE_DISPLAY_LIMIT_PCT:
            keys.append("high_overflow")
        else:
            keys.append(float(np.round(grade * 2.0) / 2.0))
    grouped: dict[float | str, dict[str, float]] = {}
    for key, distance, seconds in zip(keys, distances, times):
        if not (math.isfinite(float(distance)) and math.isfinite(float(seconds))):
            continue
        bucket = grouped.setdefault(key, {"time_s": 0.0, "distance_km": 0.0})
        bucket["time_s"] += float(seconds)
        bucket["distance_km"] += float(distance)
    ordered_keys = sorted(
        grouped,
        key=lambda value: -999.0 if value == "low_overflow" else 999.0 if value == "high_overflow" else float(value),
    )
    total = float(sum(bucket["time_s"] for bucket in grouped.values()))
    complete: list[dict[str, object]] = []
    for key in ordered_keys:
        center = (
            -GRADE_DISPLAY_LIMIT_PCT
            if key == "low_overflow"
            else GRADE_DISPLAY_LIMIT_PCT
            if key == "high_overflow"
            else float(key)
        )
        label = (
            f"≤ −{GRADE_DISPLAY_LIMIT_PCT:.0f} %"
            if key == "low_overflow"
            else f"≥ +{GRADE_DISPLAY_LIMIT_PCT:.0f} %"
            if key == "high_overflow"
            else f"{center:+.1f} %"
        )
        seconds = grouped[key]["time_s"]
        complete.append(
            {
                "grade_bin_center_pct": center,
                "label": label,
                "is_overflow": isinstance(key, str),
                "time_s": seconds,
                "distance_km": grouped[key]["distance_km"],
                "time_percent": seconds / total * 100.0 if total > 0 else 0.0,
            }
        )
    # Unlike pace bins, grade bins are not visually masked. Keeping every
    # non-empty class makes long and highly varied courses auditable and avoids
    # a second, implicit filtering rule in consumers.
    display = complete.copy()
    displayed = total
    return {
        "time_unit": "s",
        "distance_unit": "km",
        "bin_width_pct": 0.5,
        "visual_range_pct": [-GRADE_DISPLAY_LIMIT_PCT, GRADE_DISPLAY_LIMIT_PCT],
        "display_min_time_s": 0.0,
        "complete_classes": complete,
        "display_classes": display,
        "total_time_s": total,
        "displayed_time_s": displayed,
        "hidden_time_s": 0.0,
    }
