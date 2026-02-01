"""Grade / slope correction table.

This is the v1.1 canonical location.
The root-level `grade_table.py` remains as a compatibility shim.
"""

from __future__ import annotations

import numpy as np


# Average factors per grade, derived from treadmill incline tables.
# Key: grade in % (integer 0..10)
# Value: multiplicative pace factor (time).
GRADE_FACTORS = {
    0: 1.000,
    1: 1.042,
    2: 1.082,
    3: 1.120,
    4: 1.157,
    5: 1.193,
    6: 1.228,
    7: 1.262,
    8: 1.295,
    9: 1.327,
    10: 1.358,
}

MIN_DOWNHILL_FACTOR = 0.70  # max ~30% faster than base pace


def _interp_factor(grade_abs: float) -> float:
    """Linear interpolation between integer grades (0..10%)."""

    if grade_abs <= 0:
        return GRADE_FACTORS[0]
    if grade_abs >= 10:
        return GRADE_FACTORS[10]

    lower = int(grade_abs)
    upper = lower + 1
    frac = grade_abs - lower

    f_lower = GRADE_FACTORS[lower]
    f_upper = GRADE_FACTORS[upper]
    return f_lower * (1 - frac) + f_upper * frac


def grade_factor(grade_percent: float | np.ndarray) -> float | np.ndarray:
    """Return multiplicative pace factor for a given grade.

    > 1: slower uphill, < 1: faster downhill.
    """

    grade_arr = np.asarray(grade_percent, dtype=float)
    grade_abs = np.clip(np.abs(grade_arr), 0.0, 10.0)

    keys = np.array(sorted(GRADE_FACTORS.keys()), dtype=float)
    vals = np.array([GRADE_FACTORS[k] for k in keys], dtype=float)
    factors = np.interp(grade_abs, keys, vals)

    downhill = 1.0 / factors
    downhill = np.maximum(downhill, MIN_DOWNHILL_FACTOR)
    out = np.where(grade_arr >= 0, factors, downhill)

    out = np.where(np.isfinite(grade_arr), out, np.nan)

    if np.isscalar(grade_percent):
        return float(out)
    return out


def adjust_pace(pace_s_per_km: float, grade_percent: float) -> float:
    """Adjust a base pace (s/km) by grade."""

    factor = grade_factor(grade_percent)
    return pace_s_per_km * factor


def pace_to_mmss(pace_s_per_km: float) -> str:
    """Convert s/km to 'M:SS' string (display helper)."""

    total_seconds = int(round(pace_s_per_km))
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:02d}"
