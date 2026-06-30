import math

import numpy as np
import pandas as pd

from core.grade_table import grade_factor
from core.real_activity_bins import format_pace_bucket_label


def interp_pro_pace_s_per_km(grade: float, pro_ref_rows: list[dict[str, float]]) -> float | None:
    if not pro_ref_rows:
        return None

    # Expect rows sorted by grade_percent.
    first_g = float(pro_ref_rows[0]["grade_percent"])
    last_g = float(pro_ref_rows[-1]["grade_percent"])

    if grade <= first_g:
        try:
            return float(pro_ref_rows[0]["pace_s_per_km_pro"])
        except Exception:
            return None
    if grade >= last_g:
        try:
            return float(pro_ref_rows[-1]["pace_s_per_km_pro"])
        except Exception:
            return None

    for i in range(len(pro_ref_rows) - 1):
        a = pro_ref_rows[i]
        b = pro_ref_rows[i + 1]
        ga = float(a["grade_percent"])
        gb = float(b["grade_percent"])
        if ga <= grade <= gb and gb != ga:
            pa = float(a["pace_s_per_km_pro"])
            pb = float(b["pace_s_per_km_pro"])
            treshold = (grade - ga) / (gb - ga)
            return pa + treshold * (pb - pa)
    return None


def interp_pro_pace_vectorized(grades: np.ndarray, pro_rows: list[dict[str, float]]) -> np.ndarray:
    if grades.size == 0:
        return np.array([], dtype=float)
    if not pro_rows:
        return np.full_like(grades, np.nan, dtype=float)
    x = np.array([float(r["grade_percent"]) for r in pro_rows], dtype=float)
    y = np.array([float(r["pace_s_per_km_pro"]) for r in pro_rows], dtype=float)
    return np.interp(grades, x, y, left=y[0], right=y[-1])


def minetti_cost_ratio_from_grade(grade_pct: np.ndarray) -> np.ndarray:
    grade_decimal = np.asarray(grade_pct, dtype=float) / 100.0
    grade_decimal = np.clip(grade_decimal, -0.30, 0.30)

    cost = (
        155.4 * np.power(grade_decimal, 5)
        - 30.4 * np.power(grade_decimal, 4)
        - 43.3 * np.power(grade_decimal, 3)
        + 46.3 * np.power(grade_decimal, 2)
        + 19.5 * grade_decimal
        + 3.6
    )
    flat_cost = 3.6
    ratio = cost / flat_cost

    ratio = np.clip(ratio, 0.84, 2.4)
    return ratio


def constant_effort_target_pace(
    *,
    target_pace_flat_s_per_km: float,
    vma_kmh: float,
    grade_pct: np.ndarray,
) -> np.ndarray:
    vma_safe = float(vma_kmh if math.isfinite(vma_kmh) and vma_kmh > 0 else 16.0)
    base_pace = float(target_pace_flat_s_per_km if math.isfinite(target_pace_flat_s_per_km) and target_pace_flat_s_per_km > 0 else 300.0)

    base_speed_kmh = 3600.0 / base_pace
    raw_effort_ratio = base_speed_kmh / vma_safe
    effort_ratio = min(max(raw_effort_ratio, 0.45), 0.98)
    effort_speed_kmh = vma_safe * effort_ratio

    cost_ratio = minetti_cost_ratio_from_grade(grade_pct)
    slope_speed_kmh = effort_speed_kmh / cost_ratio
    slope_speed_kmh = np.clip(slope_speed_kmh, 3.0, 30.0)

    target_pace = 3600.0 / slope_speed_kmh
    return np.clip(target_pace, 120.0, 1200.0)


def build_theoretical_segments(
    activity_df: pd.DataFrame,
    *,
    target_pace_flat_s_per_km: float,
    vma_kmh: float,
    grade_model: str,
) -> pd.DataFrame:
    required = {"distance_m", "elevation"}
    if not required.issubset(set(activity_df.columns)):
        return pd.DataFrame(
            columns=[
                "distance_km",
                "target_pace_s_per_km",
                "elevation_m",
                "segment_time_s",
                "segment_grade_percent",
                "segment_distance_km",
                "cumulative_time_s",
            ]
        )

    distance = pd.to_numeric(activity_df["distance_m"], errors="coerce").to_numpy(dtype=float)
    elevation = pd.to_numeric(activity_df["elevation"], errors="coerce").to_numpy(dtype=float)
    if distance.size < 2:
        return pd.DataFrame(
            columns=[
                "distance_km",
                "target_pace_s_per_km",
                "elevation_m",
                "segment_time_s",
                "segment_grade_percent",
                "segment_distance_km",
                "cumulative_time_s",
            ]
        )

    d0 = distance[:-1]
    d1 = distance[1:]
    dist_delta_m = d1 - d0
    valid = np.isfinite(d0) & np.isfinite(d1) & (dist_delta_m > 0)
    if not valid.any():
        return pd.DataFrame(
            columns=[
                "distance_km",
                "target_pace_s_per_km",
                "elevation_m",
                "segment_time_s",
                "segment_grade_percent",
                "segment_distance_km",
                "cumulative_time_s",
            ]
        )

    seg_distance_m = dist_delta_m[valid]
    seg_distance_km = seg_distance_m / 1000.0

    e0 = elevation[:-1][valid]
    e1 = elevation[1:][valid]
    elev_delta = np.where(np.isfinite(e0) & np.isfinite(e1), e1 - e0, 0.0)
    grade_pct = (elev_delta / seg_distance_m) * 100.0

    if grade_model == "pro_ref":
        target_pace = constant_effort_target_pace(
            target_pace_flat_s_per_km=target_pace_flat_s_per_km,
            vma_kmh=vma_kmh,
            grade_pct=grade_pct,
        )
    else:
        grade_factor_arr = grade_factor(grade_pct)
        target_pace = np.asarray(target_pace_flat_s_per_km * grade_factor_arr, dtype=float)
        target_pace = np.clip(target_pace, 120.0, 1200.0)
    segment_time_s = target_pace * seg_distance_km
    cumulative_time_s = np.cumsum(segment_time_s)

    return pd.DataFrame(
        {
            "distance_km": d1[valid] / 1000.0,
            "target_pace_s_per_km": target_pace,
            "elevation_m": e1,
            "segment_time_s": segment_time_s,
            "segment_grade_percent": grade_pct,
            "segment_distance_km": seg_distance_km,
            "cumulative_time_s": cumulative_time_s,
        }
    )


def build_grade_time_bins(df_segments: pd.DataFrame) -> list[dict[str, float | str]]:
    if df_segments.empty:
        return []
    grades = df_segments["segment_grade_percent"].to_numpy(dtype=float)
    time_s = df_segments["segment_time_s"].to_numpy(dtype=float)
    grades = np.clip(grades, -20.0, 20.0)
    centers = np.round(grades * 2.0) / 2.0
    table: dict[float, float] = {}
    for center, t in zip(centers, time_s):
        if not (math.isfinite(center) and math.isfinite(t) and t > 0):
            continue
        table[float(center)] = table.get(float(center), 0.0) + float(t)
    out = []
    for center in sorted(table.keys()):
        out.append(
            {
                "grade_bin_center_pct": center,
                "label": f"{center:.1f}%",
                "time_s": table[center],
            }
        )
    return out


def build_pace_time_bins(df_segments: pd.DataFrame) -> list[dict[str, float | str]]:
    if df_segments.empty:
        return []
    pace = df_segments["target_pace_s_per_km"].to_numpy(dtype=float)
    time_s = df_segments["segment_time_s"].to_numpy(dtype=float)
    bin_width_s = 15.0
    floors = np.floor(pace / bin_width_s) * bin_width_s
    table: dict[float, float] = {}
    for floor_s, t in zip(floors, time_s):
        if not (math.isfinite(floor_s) and math.isfinite(t) and t > 0):
            continue
        table[float(floor_s)] = table.get(float(floor_s), 0.0) + float(t)
    out = []
    for floor_s in sorted(table.keys()):
        out.append(
            {
                "pace_bin_floor_s_per_km": floor_s,
                "label": format_pace_bucket_label(floor_s, bin_width_s),
                "time_s": table[floor_s],
            }
        )
    return out


def compute_secondary_metrics(df_segments: pd.DataFrame) -> dict:
    if df_segments.empty:
        return {}

    grades = df_segments["segment_grade_percent"].to_numpy(dtype=float)
    dist = df_segments["segment_distance_km"].to_numpy(dtype=float)
    time_s = df_segments["segment_time_s"].to_numpy(dtype=float)
    elev = pd.to_numeric(df_segments["elevation_m"], errors="coerce").to_numpy(dtype=float)

    total_dist = float(np.nansum(dist)) if dist.size else 0.0
    weighted_grade = float(np.nansum(grades * dist) / total_dist) if total_dist > 0 else math.nan

    finite_grades = grades[np.isfinite(grades)]
    robust_min = float(np.quantile(finite_grades, 0.01)) if finite_grades.size else math.nan
    robust_max = float(np.quantile(finite_grades, 0.99)) if finite_grades.size else math.nan

    bins = {
        "climb": grades > 0.5,
        "flat": (grades >= -0.5) & (grades <= 0.5),
        "descent": grades < -0.5,
    }

    terrain = {}
    for key, mask in bins.items():
        d = float(np.nansum(dist[mask]))
        t = float(np.nansum(time_s[mask]))
        pace = (t / d) if d > 0 else math.nan
        terrain[key] = {
            "distance_km": d,
            "time_s": t,
            "avg_pace_s_per_km": pace,
        }

    grade_bins = build_grade_time_bins(df_segments)
    top3 = sorted(grade_bins, key=lambda r: float(r["time_s"]), reverse=True)[:3]

    return {
        "weighted_avg_grade_pct": weighted_grade,
        "robust_grade_min_pct": robust_min,
        "robust_grade_max_pct": robust_max,
        "terrain_breakdown": terrain,
        "time_by_grade_top3": top3,
        "elevation_min_m": float(np.nanmin(elev)) if elev.size else None,
        "elevation_max_m": float(np.nanmax(elev)) if elev.size else None,
    }
