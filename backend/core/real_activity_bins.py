"""Backend distributions for recorded activities.

The activity keeps its recorded segment times and paces. Grades come from the
same distance-based robust course profile as theoretical traces, and the
histogram rules are shared with race planning.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from api.schemas import RealActivityBinsResponse
from core.course_profile import prepare_course_profile
from core.derived import compute_derived_series
from core.time_histograms import build_grade_histogram, build_pace_histogram


def _empty_response() -> RealActivityBinsResponse:
    empty_histogram = {
        "complete_classes": [],
        "display_classes": [],
        "total_time_s": 0.0,
        "displayed_time_s": 0.0,
        "hidden_time_s": 0.0,
    }
    return RealActivityBinsResponse(
        pace_elevation_series=[],
        pace_time_bins=[],
        grade_time_bins=[],
        pace_histogram=empty_histogram,
        grade_histogram=empty_histogram,
    )


def build_real_activity_bins(activity_df: pd.DataFrame) -> RealActivityBinsResponse:
    required = {"distance_m", "time", "elevation"}
    if not required.issubset(set(activity_df.columns)) or len(activity_df) < 2:
        return _empty_response()

    work = activity_df.copy()
    work["distance_m"] = pd.to_numeric(work["distance_m"], errors="coerce")
    work["elevation"] = pd.to_numeric(work["elevation"], errors="coerce")
    work["time"] = pd.to_datetime(work["time"], errors="coerce")

    source_distance = work["distance_m"].to_numpy(dtype=float)
    finite_distance = source_distance[np.isfinite(source_distance)]
    if finite_distance.size < 2:
        return _empty_response()
    source_distance = source_distance - float(finite_distance[0])
    d0 = source_distance[:-1]
    d1 = source_distance[1:]
    delta_m = d1 - d0

    t1 = work["time"].to_numpy()[1:]
    t0 = work["time"].to_numpy()[:-1]
    delta_t_s = ((t1 - t0) / np.timedelta64(1, "s")).astype(float)
    e1 = work["elevation"].to_numpy(dtype=float)[1:]

    derived = compute_derived_series(work)
    moving_mask = np.asarray(derived.moving_mask, dtype=bool)
    moving_seg = moving_mask[1:] if moving_mask.shape[0] == work.shape[0] else np.ones_like(delta_m, dtype=bool)

    try:
        profile = prepare_course_profile(work).dataframe
    except ValueError:
        return _empty_response()
    profile_distance = profile["distance_m"].to_numpy(dtype=float)
    robust_grade = profile["grade_robust_pct"].to_numpy(dtype=float)
    source_total_m = float(np.nanmax(source_distance))
    profile_total_m = float(profile_distance[-1])
    if source_total_m <= 0 or profile_total_m <= 0:
        return _empty_response()
    segment_mid_source_m = (d0 + d1) / 2.0
    segment_mid_profile_m = segment_mid_source_m * (profile_total_m / source_total_m)
    segment_grade = np.interp(segment_mid_profile_m, profile_distance, robust_grade)

    valid = (
        np.isfinite(delta_m)
        & np.isfinite(delta_t_s)
        & np.isfinite(segment_grade)
        & np.isfinite(e1)
        & np.isfinite(d1)
        & (delta_m > 1.0)
        & (delta_t_s > 0.0)
        & (delta_t_s < 120.0)
        & moving_seg
    )
    if not np.any(valid):
        return _empty_response()

    seg_dist_km = delta_m[valid] / 1000.0
    seg_time_s = delta_t_s[valid]
    seg_pace = seg_time_s / np.maximum(seg_dist_km, 1e-6)
    seg_grade = segment_grade[valid]
    realistic = np.isfinite(seg_pace) & (seg_pace >= 120.0) & (seg_pace <= 1200.0)
    if not np.any(realistic):
        return _empty_response()
    seg_dist_km = seg_dist_km[realistic]
    seg_time_s = seg_time_s[realistic]
    seg_pace = seg_pace[realistic]
    seg_grade = seg_grade[realistic]
    valid_indices = np.flatnonzero(valid)[realistic]

    reference_pace = float(np.sum(seg_time_s) / np.sum(seg_dist_km))
    pace_histogram = build_pace_histogram(seg_pace, seg_time_s, reference_pace)
    grade_histogram = build_grade_histogram(seg_grade, seg_dist_km, seg_time_s)

    series = [
        {
            "distance_km": float(d1[index]) / 1000.0,
            "pace_s_per_km": float(pace_s),
            "elevation_m": float(e1[index]),
        }
        for index, pace_s in zip(valid_indices, seg_pace)
    ]
    return RealActivityBinsResponse(
        pace_elevation_series=series,
        # Compatibility aliases for existing clients. New consumers use the
        # complete/display histogram contracts below.
        pace_time_bins=pace_histogram["display_classes"],
        grade_time_bins=grade_histogram["display_classes"],
        pace_histogram=pace_histogram,
        grade_histogram=grade_histogram,
    )
