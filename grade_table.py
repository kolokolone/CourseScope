"""Compatibility shim.

The canonical implementation lives in `core/grade_table.py`.
Keep this module to preserve existing imports: `from grade_table import grade_factor`.
"""

from __future__ import annotations

from core.grade_table import (  # noqa: F401
    GRADE_FACTORS,
    MIN_DOWNHILL_FACTOR,
    _interp_factor,
    adjust_pace,
    grade_factor,
    pace_to_mmss,
)


__all__ = [
    "GRADE_FACTORS",
    "MIN_DOWNHILL_FACTOR",
    "_interp_factor",
    "grade_factor",
    "adjust_pace",
    "pace_to_mmss",
]
