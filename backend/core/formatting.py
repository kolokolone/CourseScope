from __future__ import annotations

"""Formatting helpers shared across UI and backend.

Keep this module Streamlit-free to allow reuse in a future API.
"""

import math
from typing import Any

import pandas as pd


def format_duration_compact(seconds: float | None) -> str:
    """Format duration like ui/layout.py (e.g. 3h05m02s / 5m02s / '-')."""

    if seconds is None:
        return "-"
    if isinstance(seconds, float) and math.isnan(seconds):
        return "-"
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}m{s:02d}s"
    return f"{m}m{s:02d}s"


def format_duration_clock(seconds: float | None) -> str:
    """Format duration like ui/*_view.py (e.g. 1:02:03 / 5:02 / '-')."""

    if seconds is None:
        return "-"
    if isinstance(seconds, float) and math.isnan(seconds):
        return "-"
    total_seconds = int(round(seconds))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_time_of_day(value: Any) -> str:
    """Format a timestamp-like value as HH:MM:SS for UI."""

    if value is None:
        return "-"
    if isinstance(value, float) and math.isnan(value):
        return "-"
    try:
        ts = pd.to_datetime(value)
        if pd.isna(ts):
            return "-"
        return ts.strftime("%H:%M:%S")
    except Exception:
        return "-"
