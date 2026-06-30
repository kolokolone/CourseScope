import math

import numpy as np
import pandas as pd

from core.derived import compute_derived_series
from api.schemas import RealActivityBinsResponse


def build_real_activity_bins(activity_df: pd.DataFrame) -> RealActivityBinsResponse:
    required = {"distance_m", "time", "elevation"}
    if not required.issubset(set(activity_df.columns)):
        return RealActivityBinsResponse(pace_elevation_series=[], pace_time_bins=[], grade_time_bins=[])

    work = activity_df.copy()
    work["distance_m"] = pd.to_numeric(work["distance_m"], errors="coerce")
    work["elevation"] = pd.to_numeric(work["elevation"], errors="coerce")
    work["time"] = pd.to_datetime(work["time"], errors="coerce")

    d1 = work["distance_m"].to_numpy(dtype=float)[1:]
    d0 = work["distance_m"].to_numpy(dtype=float)[:-1]
    delta_m = d1 - d0

    t1 = work["time"].to_numpy()[1:]
    t0 = work["time"].to_numpy()[:-1]
    delta_t_s = ((t1 - t0) / np.timedelta64(1, "s")).astype(float)

    e1 = work["elevation"].to_numpy(dtype=float)[1:]
    e0 = work["elevation"].to_numpy(dtype=float)[:-1]
    grade_pct = ((e1 - e0) / np.maximum(delta_m, 1e-9)) * 100.0

    derived = compute_derived_series(work)
    moving_mask = np.asarray(derived.moving_mask, dtype=bool)
    if moving_mask.shape[0] == work.shape[0]:
        moving_seg = moving_mask[1:]
    else:
        moving_seg = np.ones_like(delta_m, dtype=bool)

    valid = (
        np.isfinite(delta_m)
        & np.isfinite(delta_t_s)
        & np.isfinite(grade_pct)
        & np.isfinite(e1)
        & np.isfinite(d1)
        & (delta_m > 1.0)
        & (delta_t_s > 0.0)
        & (delta_t_s < 120.0)
        & moving_seg
    )

    if not np.any(valid):
        return RealActivityBinsResponse(pace_elevation_series=[], pace_time_bins=[], grade_time_bins=[])

    seg_dist_km = delta_m[valid] / 1000.0
    seg_time_s = delta_t_s[valid]
    seg_pace = np.clip(seg_time_s / np.maximum(seg_dist_km, 1e-6), 120.0, 1200.0)
    seg_grade = np.clip(grade_pct[valid], -20.0, 20.0)

    pace_table: dict[float, float] = {}
    pace_bin_width = 15.0
    pace_floor = np.floor(seg_pace / pace_bin_width) * pace_bin_width
    for floor_s, t in zip(pace_floor, seg_time_s):
        if not (math.isfinite(floor_s) and math.isfinite(t) and t > 0):
            continue
        pace_table[float(floor_s)] = pace_table.get(float(floor_s), 0.0) + float(t)
    pace_time_bins = [
        {
            "pace_bin_floor_s_per_km": floor_s,
            "label": format_pace_bucket_label(floor_s, pace_bin_width),
            "time_s": pace_table[floor_s],
        }
        for floor_s in sorted(pace_table.keys())
    ]

    grade_table: dict[float, float] = {}
    grade_center = np.round(seg_grade * 2.0) / 2.0
    for center, t in zip(grade_center, seg_time_s):
        if not (math.isfinite(center) and math.isfinite(t) and t > 0):
            continue
        grade_table[float(center)] = grade_table.get(float(center), 0.0) + float(t)
    grade_time_bins = [
        {
            "grade_bin_center_pct": center,
            "label": f"{center:.1f}%",
            "time_s": grade_table[center],
        }
        for center in sorted(grade_table.keys())
    ]

    series = [
        {
            "distance_km": float(dist_m) / 1000.0,
            "pace_s_per_km": float(pace_s),
            "elevation_m": float(elev),
        }
        for dist_m, pace_s, elev in zip(d1[valid], seg_pace, e1[valid])
    ]

    return RealActivityBinsResponse(
        pace_elevation_series=series,
        pace_time_bins=pace_time_bins,
        grade_time_bins=grade_time_bins,
    )


def format_pace_bucket_label(start_s: float, width_s: float) -> str:
    a = int(round(start_s))
    b = int(round(start_s + width_s))
    return f"{a // 60}:{a % 60:02d}-{b // 60}:{b % 60:02d}/km"
