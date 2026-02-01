from __future__ import annotations

import math
from typing import Any, Dict

import numpy as np
import pandas as pd

from core.constants import MIN_DISTANCE_FOR_SPEED_M
from core.stats.basic_stats import compute_basic_stats
from core.utils import seconds_to_mmss

HR_ZONES = [
    ("Z1", 0.50, 0.60),
    ("Z2", 0.60, 0.70),
    ("Z3", 0.70, 0.80),
    ("Z4", 0.80, 0.90),
    ("Z5", 0.90, math.inf),
]

PACE_ZONES = [
    ("Z1", 1.29, math.inf),
    ("Z2", 1.14, 1.29),
    ("Z3", 1.06, 1.14),
    ("Z4", 0.99, 1.06),
    ("Z5", 0.00, 0.99),
]

POWER_ZONES = [
    ("Z1", 0.00, 0.55),
    ("Z2", 0.55, 0.75),
    ("Z3", 0.75, 0.90),
    ("Z4", 0.90, 1.05),
    ("Z5", 1.05, 1.20),
    ("Z6", 1.20, 1.50),
    ("Z7", 1.50, math.inf),
]

POWER_PEAK_DURATIONS_S = [5, 10, 30, 60, 120, 300, 600, 1200, 1800, 3600]


def _weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    mask = np.isfinite(values) & np.isfinite(weights) & (weights > 0)
    if not mask.any():
        return math.nan
    return float(np.nansum(values[mask] * weights[mask]) / np.nansum(weights[mask]))


def _build_zone_table(
    ratios: np.ndarray,
    weights: np.ndarray,
    zones: list[tuple[str, float, float]],
    label_func,
) -> pd.DataFrame:
    mask = np.isfinite(ratios) & np.isfinite(weights) & (weights > 0)
    if not mask.any():
        return pd.DataFrame(columns=["zone", "range", "time_s", "time_pct"])
    ratios = ratios[mask]
    weights = weights[mask]
    total_time = float(weights.sum())
    if total_time <= 0:
        return pd.DataFrame(columns=["zone", "range", "time_s", "time_pct"])

    rows = []
    for name, low, high in zones:
        if math.isinf(high):
            zone_mask = ratios >= low
        else:
            zone_mask = (ratios >= low) & (ratios < high)
        time_s = float(weights[zone_mask].sum())
        rows.append(
            {
                "zone": name,
                "range": label_func(low, high),
                "time_s": time_s,
                "time_pct": (time_s / total_time) * 100.0,
            }
        )
    return pd.DataFrame(rows)


def _time_and_distance(df: pd.DataFrame) -> tuple[float, float]:
    stats = compute_basic_stats(df)
    return float(stats.total_time_s), float(stats.distance_m)


def _pace_from_deltas(delta_time_s: np.ndarray, delta_distance_m: np.ndarray) -> np.ndarray:
    pace = np.full_like(delta_time_s, np.nan, dtype=float)
    np.divide(delta_time_s, delta_distance_m, out=pace, where=delta_distance_m > 0)
    pace *= 1000.0
    return pace


def _safe_percentile(values: np.ndarray, q: float) -> float:
    values = values[np.isfinite(values)]
    if values.size == 0:
        return math.nan
    return float(np.nanpercentile(values, q))


def _rolling_pace_s_per_km(
    delta_time_s: np.ndarray, delta_distance_m: np.ndarray, window_s: float
) -> np.ndarray:
    """Calcule une allure glissante (s/km) sur une fenetre de temps en mouvement.

    Les entrees doivent deja etre filtrees sur des segments "en mouvement" avec dt>0.
    """

    n = int(len(delta_time_s))
    if n == 0:
        return np.array([], dtype=float)

    dt = np.where(delta_time_s > 0, delta_time_s, 0.0)
    dd = np.where(delta_distance_m > 0, delta_distance_m, 0.0)

    cum_t = np.concatenate(([0.0], np.cumsum(dt)))
    cum_d = np.concatenate(([0.0], np.cumsum(dd)))

    pace = np.full(n, np.nan, dtype=float)
    j = 0
    for i in range(n):
        end_t = cum_t[i + 1]
        while j < i and end_t - cum_t[j + 1] >= window_s:
            j += 1
        time_win = end_t - cum_t[j]
        dist_win = cum_d[i + 1] - cum_d[j]
        if time_win >= window_s and dist_win > 0:
            pace[i] = time_win / (dist_win / 1000.0)
    return pace


def _robust_best_pace_s_per_km(
    delta_time_s: np.ndarray,
    delta_distance_m: np.ndarray,
    moving_mask: np.ndarray,
    *,
    window_s: float = 30.0,
) -> float:
    """Meilleure allure robuste basee sur un percentile d'allure glissante (anti-pics)."""

    dt = np.where(delta_time_s > 0, delta_time_s, 0.0)
    dd = np.where(delta_distance_m > 0, delta_distance_m, 0.0)

    valid = (dt > 0) & (dd >= MIN_DISTANCE_FOR_SPEED_M) & moving_mask
    dt_m = dt[valid]
    dd_m = dd[valid]
    if dt_m.size == 0 or dd_m.size == 0:
        return math.nan

    pace_roll = _rolling_pace_s_per_km(dt_m, dd_m, window_s=window_s)
    pace_roll = pace_roll[np.isfinite(pace_roll)]
    pace_roll = pace_roll[(pace_roll >= 120.0) & (pace_roll <= 1800.0)]
    if pace_roll.size == 0:
        pace_inst = _pace_from_deltas(dt_m, dd_m)
        pace_inst = pace_inst[np.isfinite(pace_inst)]
        pace_inst = pace_inst[(pace_inst >= 120.0) & (pace_inst <= 1800.0)]
        return _safe_percentile(pace_inst, 1)

    return _safe_percentile(pace_roll, 1)


def _compute_grade_percent_from_elevation(
    elevation_m: np.ndarray, delta_distance_m: np.ndarray
) -> np.ndarray:
    grade = np.full(len(elevation_m), np.nan, dtype=float)
    if len(elevation_m) < 2:
        return grade

    delta_elev = np.diff(elevation_m, prepend=np.nan)
    dist = np.where(delta_distance_m > 0, delta_distance_m, np.nan)
    np.divide(delta_elev, dist, out=grade, where=np.isfinite(delta_elev) & np.isfinite(dist) & (dist > 0))
    grade *= 100.0
    return grade


def _normalized_power_w(
    power_w: np.ndarray,
    delta_time_s: np.ndarray,
    mask: np.ndarray,
    *,
    rolling_window_s: int = 30,
) -> float:
    """Calcule la Normalized Power (NP) via resampling 1 Hz + moyenne glissante 30s."""
    if power_w.size == 0:
        return math.nan

    series_1hz = _resample_series_1hz(power_w, delta_time_s, mask)
    return _normalized_power_from_series(series_1hz, rolling_window_s=rolling_window_s)


def _resample_series_1hz(
    values: np.ndarray,
    delta_time_s: np.ndarray,
    mask: np.ndarray,
    *,
    ffill_limit: int = 5,
) -> pd.Series:
    dt = np.where(delta_time_s > 0, delta_time_s, 0.0)
    dt = np.where(mask, dt, 0.0)
    elapsed_s = np.cumsum(dt)

    valid = mask & (dt > 0) & np.isfinite(values)
    if int(valid.sum()) < 2:
        return pd.Series(dtype=float)

    idx = pd.to_timedelta(elapsed_s[valid], unit="s")
    s = pd.Series(values[valid], index=idx).sort_index()
    if s.empty:
        return pd.Series(dtype=float)

    s = s.groupby(level=0).mean()
    return s.resample("1s").mean().ffill(limit=ffill_limit)


def _normalized_power_from_series(
    series_1hz: pd.Series, *, rolling_window_s: int = 30
) -> float:
    if series_1hz is None or series_1hz.empty:
        return math.nan

    if int(series_1hz.dropna().shape[0]) < rolling_window_s:
        return math.nan

    roll = series_1hz.rolling(window=rolling_window_s, min_periods=rolling_window_s).mean().dropna()
    if roll.empty:
        return math.nan

    values = roll.to_numpy(dtype=float)
    mean_fourth = float(np.mean(np.power(values, 4)))
    if not np.isfinite(mean_fourth) or mean_fourth <= 0:
        return math.nan
    return float(np.power(mean_fourth, 0.25))


def _compute_power_duration_curve_from_series(
    series_1hz: pd.Series, durations_s: list[int]
) -> list[dict[str, float]]:
    if series_1hz is None or series_1hz.empty:
        return []

    out: list[dict[str, float]] = []
    for duration in durations_s:
        window = int(duration)
        if window <= 0:
            continue
        roll = series_1hz.rolling(window=window, min_periods=window).mean().dropna()
        peak = float(roll.max()) if not roll.empty else math.nan
        out.append({"duration_s": float(window), "power_w": float(peak)})
    return out


def _compute_power_duration_curve(
    power_w: np.ndarray,
    delta_time_s: np.ndarray,
    mask: np.ndarray,
    durations_s: list[int],
) -> list[dict[str, float]]:
    series_1hz = _resample_series_1hz(power_w, delta_time_s, mask)
    return _compute_power_duration_curve_from_series(series_1hz, durations_s)


def _edwards_trimp_from_zones(zones_df: pd.DataFrame) -> float:
    if zones_df is None or zones_df.empty:
        return math.nan
    if "zone" not in zones_df.columns or "time_s" not in zones_df.columns:
        return math.nan

    weights_map = {"Z1": 1, "Z2": 2, "Z3": 3, "Z4": 4, "Z5": 5}
    weights = zones_df["zone"].map(weights_map).to_numpy(dtype=float)
    time_s = pd.to_numeric(zones_df["time_s"], errors="coerce").to_numpy(dtype=float)
    mask = np.isfinite(time_s) & np.isfinite(weights) & (weights > 0)
    if not mask.any():
        return math.nan
    return float(np.nansum((time_s[mask] / 60.0) * weights[mask]))


def _negative_split(
    delta_time_s: np.ndarray, delta_distance_m: np.ndarray, mask: np.ndarray
) -> tuple[float, float, float]:
    dist = delta_distance_m * mask
    dt = delta_time_s * mask
    total_dist = float(dist.sum())
    if total_dist <= 0:
        return math.nan, math.nan, math.nan

    ratio = _half_overlap_ratio(dist)
    time_first = float(np.sum(dt * ratio))
    dist_first = float(np.sum(dist * ratio))
    time_second = float(dt.sum() - time_first)
    dist_second = float(total_dist - dist_first)

    pace_first = time_first / (dist_first / 1000.0) if dist_first > 0 else math.nan
    pace_second = time_second / (dist_second / 1000.0) if dist_second > 0 else math.nan
    return pace_first, pace_second, pace_second - pace_first


def _half_overlap_ratio(dist: np.ndarray) -> np.ndarray:
    total_dist = float(dist.sum())
    if total_dist <= 0:
        return np.zeros_like(dist, dtype=float)
    cum_dist = np.cumsum(dist)
    half = total_dist / 2.0
    prev = np.concatenate(([0.0], cum_dist[:-1]))
    overlap = np.clip(np.minimum(cum_dist, half) - prev, 0.0, dist)
    ratio = np.zeros_like(dist, dtype=float)
    np.divide(overlap, dist, out=ratio, where=dist > 0)
    return ratio


def compute_longest_pause(delta_time_s: np.ndarray, moving_mask: np.ndarray) -> float:
    longest = 0.0
    current = 0.0
    for dt, moving in zip(delta_time_s, moving_mask):
        if not moving and dt > 0:
            current += float(dt)
        else:
            if current > longest:
                longest = current
            current = 0.0
    if current > longest:
        longest = current
    return float(longest)


def estimate_zone_inputs(df: pd.DataFrame, moving_mask: pd.Series) -> Dict[str, Any]:
    values = {}
    mask = moving_mask.to_numpy(dtype=bool) if moving_mask is not None else np.ones(len(df), dtype=bool)
    delta_time = df["delta_time_s"].fillna(0).to_numpy() if "delta_time_s" in df else np.zeros(len(df))
    delta_time = np.where(delta_time > 0, delta_time, 0.0)

    if "heart_rate" in df and df["heart_rate"].notna().any():
        hr = df["heart_rate"].to_numpy(dtype=float)
        hr_mask = np.isfinite(hr) & (delta_time > 0) & mask
        values["hr_max"] = float(np.nanmax(hr[hr_mask])) if hr_mask.any() else math.nan
        values["hr_available"] = True
    else:
        values["hr_max"] = math.nan
        values["hr_available"] = False

    if "cadence" in df and df["cadence"].notna().any():
        values["cadence_available"] = True
        values["cadence_target"] = 170.0
    else:
        values["cadence_available"] = False
        values["cadence_target"] = math.nan

    if "power" in df and df["power"].notna().any():
        power = df["power"].to_numpy(dtype=float)
        power_mask = np.isfinite(power) & (delta_time > 0) & mask
        values["power_available"] = True
        values["ftp_estimated"] = True
        values["ftp_w"] = float(np.nanpercentile(power[power_mask], 95)) if power_mask.any() else math.nan
    else:
        values["power_available"] = False
        values["ftp_estimated"] = False
        values["ftp_w"] = math.nan

    if "delta_distance_m" in df and "delta_time_s" in df:
        delta_dist = df["delta_distance_m"].fillna(0).to_numpy()
        delta_dist = np.where(delta_dist > 0, delta_dist, 0.0)
        pace = _pace_from_deltas(delta_time, delta_dist)
        pace_mask = np.isfinite(pace) & (delta_time > 0) & mask
        values["pace_threshold_s_per_km"] = float(np.nanmedian(pace[pace_mask])) if pace_mask.any() else math.nan
    else:
        values["pace_threshold_s_per_km"] = math.nan

    return values


def compute_garmin_like_stats(
    df: pd.DataFrame,
    moving_mask: pd.Series,
    gap_series: pd.Series | None = None,
    grade_series: pd.Series | None = None,
    hr_max: float | None = None,
    hr_rest: float | None = None,
    use_hrr: bool = False,
    pace_threshold_s_per_km: float | None = None,
    ftp_w: float | None = None,
    cadence_target: float | None = None,
    use_moving_time: bool = True,
) -> Dict[str, Any]:
    if df.empty:
        return {
            "summary": {},
            "heart_rate": None,
            "cadence": None,
            "power": None,
            "pace_zones": None,
            "running_dynamics": None,
            "training_load": None,
            "power_advanced": None,
            "pacing": {},
        }

    total_time_s, total_distance_m = _time_and_distance(df)

    delta_time = df["delta_time_s"].fillna(0).to_numpy() if "delta_time_s" in df else np.zeros(len(df))
    delta_time = np.where(delta_time > 0, delta_time, 0.0)
    delta_dist = df["delta_distance_m"].fillna(0).to_numpy() if "delta_distance_m" in df else np.zeros(len(df))
    delta_dist = np.where(delta_dist > 0, delta_dist, 0.0)

    mask = moving_mask.to_numpy(dtype=bool) if moving_mask is not None else np.ones(len(df), dtype=bool)
    mask = mask if use_moving_time else np.ones(len(df), dtype=bool)

    weights = delta_time * mask
    moving_time_s = float(weights.sum())
    moving_distance_m = float((delta_dist * mask).sum())
    pause_time_s = float(max(total_time_s - moving_time_s, 0.0))

    pace = _pace_from_deltas(delta_time, delta_dist)
    pace = np.where(mask, pace, np.nan)
    pace_mask = np.isfinite(pace) & (weights > 0)

    speed_m_s = np.full_like(delta_time, np.nan, dtype=float)
    valid_speed = (delta_time > 0) & (delta_dist >= MIN_DISTANCE_FOR_SPEED_M) & mask
    np.divide(delta_dist, delta_time, out=speed_m_s, where=valid_speed)
    speed_m_s = np.where(mask, speed_m_s, np.nan)
    max_speed_kmh = float(np.nanmax(speed_m_s) * 3.6) if np.isfinite(speed_m_s).any() else math.nan

    best_pace_s_per_km = _robust_best_pace_s_per_km(delta_time, delta_dist, mask, window_s=30.0)

    avg_pace = moving_time_s / (moving_distance_m / 1000.0) if moving_distance_m > 0 else math.nan
    avg_speed = (moving_distance_m / 1000.0) / (moving_time_s / 3600.0) if moving_time_s > 0 else math.nan

    gap_mean = math.nan
    pace_for_ratio = pace
    if gap_series is not None:
        gap_values = gap_series.to_numpy(dtype=float)
        gap_mean = _weighted_mean(gap_values, weights)
        pace_for_ratio = np.where(np.isfinite(gap_values), gap_values, pace)

    elevation = None
    elevation_gain_m = 0.0
    elevation_loss_m = 0.0
    elevation_gain_filtered_m = math.nan
    elevation_loss_filtered_m = math.nan
    elevation_min_m = math.nan
    elevation_max_m = math.nan
    if "elevation" in df:
        elevation = df["elevation"].ffill().bfill().to_numpy(dtype=float)
        if np.isfinite(elevation).any():
            elevation_min_m = float(np.nanmin(elevation))
            elevation_max_m = float(np.nanmax(elevation))
        if len(elevation) > 1:
            diffs = np.diff(elevation)
            elevation_gain_m = float(np.clip(diffs, 0, None).sum())
            elevation_loss_m = float(np.abs(np.clip(diffs, None, 0)).sum())

            elev_smoothed = (
                pd.Series(elevation)
                .rolling(window=5, center=True, min_periods=1)
                .median()
                .to_numpy(dtype=float)
            )
            diffs_s = np.diff(elev_smoothed)
            diffs_s = np.where(np.abs(diffs_s) < 0.5, 0.0, diffs_s)
            elevation_gain_filtered_m = float(np.clip(diffs_s, 0, None).sum())
            elevation_loss_filtered_m = float(np.abs(np.clip(diffs_s, None, 0)).sum())

    pace_median = float(np.nanmedian(pace[pace_mask])) if pace_mask.any() else math.nan
    pace_p10 = float(np.nanpercentile(pace[pace_mask], 10)) if pace_mask.any() else math.nan
    pace_p90 = float(np.nanpercentile(pace[pace_mask], 90)) if pace_mask.any() else math.nan

    pace_first, pace_second, pace_delta = _negative_split(delta_time, delta_dist, mask)

    drift = math.nan
    if pace_mask.sum() >= 2:
        cum_dist = np.cumsum(delta_dist * mask) / 1000.0
        x = cum_dist[pace_mask]
        y = pace[pace_mask]
        if len(x) >= 2 and np.nanmax(x) > 0:
            drift = float(np.polyfit(x, y, 1)[0])

    stability_cv = math.nan
    stability_iqr = math.nan
    if pace_mask.any():
        pace_vals = pace[pace_mask]
        mean = float(np.nanmean(pace_vals))
        median = float(np.nanmedian(pace_vals))
        if mean > 0:
            stability_cv = float(np.nanstd(pace_vals) / mean)
        q1 = float(np.nanpercentile(pace_vals, 25))
        q3 = float(np.nanpercentile(pace_vals, 75))
        if median > 0:
            stability_iqr = float((q3 - q1) / median)

    gap_residual = math.nan
    if gap_series is not None:
        gap_values = gap_series.to_numpy(dtype=float)
        mask_gap = pace_mask & np.isfinite(gap_values)
        if mask_gap.any():
            gap_residual = float(np.nanmedian(pace[mask_gap] - gap_values[mask_gap]))

    vam_m_h = elevation_gain_m / (moving_time_s / 3600.0) if moving_time_s > 0 else math.nan

    grade_values = None
    if grade_series is not None:
        grade_values = grade_series.to_numpy(dtype=float)
    elif elevation is not None:
        grade_values = _compute_grade_percent_from_elevation(elevation, delta_dist)
        grade_values = (
            pd.Series(grade_values)
            .rolling(window=5, center=True, min_periods=1)
            .median()
            .to_numpy(dtype=float)
        )
    else:
        grade_values = np.full(len(df), np.nan, dtype=float)

    grade_values = np.where(mask, grade_values, np.nan)
    grade_weights = delta_dist * mask
    grade_mean_pct = _weighted_mean(grade_values, grade_weights)
    grade_clip = np.clip(grade_values, -30.0, 30.0)
    grade_valid = np.isfinite(grade_clip) & (grade_weights > 0)
    grade_min_pct = _safe_percentile(grade_clip[grade_valid], 1)
    grade_max_pct = _safe_percentile(grade_clip[grade_valid], 99)

    steps_total = math.nan
    step_length_est_m = math.nan
    if "cadence" in df and df["cadence"].notna().any():
        cad_values = df["cadence"].to_numpy(dtype=float)
        cad_valid = np.isfinite(cad_values) & (weights > 0) & (cad_values > 0)
        if cad_valid.any():
            steps_total = float(np.nansum(cad_values[cad_valid] * weights[cad_valid] / 60.0))
            step_len = np.full_like(cad_values, np.nan, dtype=float)
            valid_step_len = cad_valid & np.isfinite(speed_m_s) & (speed_m_s > 0)
            step_len[valid_step_len] = (speed_m_s[valid_step_len] * 60.0) / cad_values[valid_step_len]
            step_length_est_m = _weighted_mean(step_len, weights)

    running_dynamics = None
    stride_length_mean_m = math.nan
    vertical_oscillation_mean_cm = math.nan
    vertical_ratio_mean_pct = math.nan
    ground_contact_time_mean_ms = math.nan
    gct_balance_mean_pct = math.nan

    if "stride_length_m" in df and df["stride_length_m"].notna().any():
        stride_length_mean_m = _weighted_mean(df["stride_length_m"].to_numpy(dtype=float), weights)
    if stride_length_mean_m != stride_length_mean_m and step_length_est_m == step_length_est_m:
        stride_length_mean_m = float(step_length_est_m)

    if "vertical_oscillation_cm" in df and df["vertical_oscillation_cm"].notna().any():
        vertical_oscillation_mean_cm = _weighted_mean(df["vertical_oscillation_cm"].to_numpy(dtype=float), weights)

    if "vertical_ratio_pct" in df and df["vertical_ratio_pct"].notna().any():
        vertical_ratio_mean_pct = _weighted_mean(df["vertical_ratio_pct"].to_numpy(dtype=float), weights)
    elif (
        vertical_oscillation_mean_cm == vertical_oscillation_mean_cm
        and stride_length_mean_m == stride_length_mean_m
        and stride_length_mean_m > 0
    ):
        # vertical_ratio_pct ~= vertical_oscillation_cm / stride_length_m
        vertical_ratio_mean_pct = float(vertical_oscillation_mean_cm / stride_length_mean_m)

    if "ground_contact_time_ms" in df and df["ground_contact_time_ms"].notna().any():
        ground_contact_time_mean_ms = _weighted_mean(df["ground_contact_time_ms"].to_numpy(dtype=float), weights)

    if "gct_balance_pct" in df and df["gct_balance_pct"].notna().any():
        gct_balance_mean_pct = _weighted_mean(df["gct_balance_pct"].to_numpy(dtype=float), weights)

    if (
        stride_length_mean_m == stride_length_mean_m
        or vertical_oscillation_mean_cm == vertical_oscillation_mean_cm
        or vertical_ratio_mean_pct == vertical_ratio_mean_pct
        or ground_contact_time_mean_ms == ground_contact_time_mean_ms
        or gct_balance_mean_pct == gct_balance_mean_pct
    ):
        running_dynamics = {
            "stride_length_mean_m": float(stride_length_mean_m),
            "vertical_oscillation_mean_cm": float(vertical_oscillation_mean_cm),
            "vertical_ratio_mean_pct": float(vertical_ratio_mean_pct),
            "ground_contact_time_mean_ms": float(ground_contact_time_mean_ms),
            "gct_balance_mean_pct": float(gct_balance_mean_pct),
        }

    summary = {
        "total_time_s": float(total_time_s),
        "moving_time_s": float(moving_time_s),
        "pause_time_s": float(pause_time_s),
        "distance_km": float(total_distance_m / 1000.0) if total_distance_m > 0 else 0.0,
        "moving_distance_km": float(moving_distance_m / 1000.0) if moving_distance_m > 0 else 0.0,
        "average_pace_s_per_km": float(avg_pace),
        "average_speed_kmh": float(avg_speed),
        "max_speed_kmh": float(max_speed_kmh),
        "best_pace_s_per_km": float(best_pace_s_per_km),
        "gap_mean_s_per_km": float(gap_mean),
        "pace_median": float(pace_median),
        "pace_p10": float(pace_p10),
        "pace_p90": float(pace_p90),
        "pace_median_s_per_km": float(pace_median),
        "pace_p10_s_per_km": float(pace_p10),
        "pace_p90_s_per_km": float(pace_p90),
        "elevation_gain_m": float(elevation_gain_m),
        "elevation_loss_m": float(elevation_loss_m),
        "elevation_gain_filtered_m": float(elevation_gain_filtered_m),
        "elevation_loss_filtered_m": float(elevation_loss_filtered_m),
        "elevation_min_m": float(elevation_min_m),
        "elevation_max_m": float(elevation_max_m),
        "grade_mean_pct": float(grade_mean_pct),
        "grade_min_pct": float(grade_min_pct),
        "grade_max_pct": float(grade_max_pct),
        "vam_m_h": float(vam_m_h),
        "steps_total": float(steps_total),
        "step_length_est_m": float(step_length_est_m),
        "longest_pause_s": compute_longest_pause(delta_time, moving_mask.to_numpy(dtype=bool))
        if moving_mask is not None
        else math.nan,
    }

    heart_rate = None
    cardiac_drift_pct = math.nan
    cardiac_drift_slope_pct = math.nan
    if "heart_rate" in df and df["heart_rate"].notna().any():
        hr_values = df["heart_rate"].to_numpy(dtype=float)
        hr_mask = np.isfinite(hr_values) & (weights > 0)
        hr_max_obs = float(np.nanmax(hr_values[hr_mask])) if hr_mask.any() else math.nan
        hr_min_obs = float(np.nanmin(hr_values[hr_mask])) if hr_mask.any() else math.nan
        hr_max_used = float(hr_max) if hr_max and hr_max > 0 else hr_max_obs
        hr_mean = _weighted_mean(hr_values, weights)
        ratio_first = _half_overlap_ratio(delta_dist * mask)
        ratio_second = np.zeros_like(ratio_first, dtype=float)
        valid_dist = (delta_dist * mask) > 0
        ratio_second[valid_dist] = 1.0 - ratio_first[valid_dist]
        hr_pace_ratio = np.full_like(hr_values, np.nan, dtype=float)
        valid_ratio = np.isfinite(hr_values) & np.isfinite(pace_for_ratio) & (pace_for_ratio > 0)
        np.divide(hr_values, pace_for_ratio, out=hr_pace_ratio, where=valid_ratio)
        ratio_first_mean = _weighted_mean(hr_pace_ratio, weights * ratio_first)
        ratio_second_mean = _weighted_mean(hr_pace_ratio, weights * ratio_second)
        if ratio_first_mean == ratio_first_mean and ratio_first_mean > 0 and ratio_second_mean == ratio_second_mean:
            cardiac_drift_pct = ((ratio_second_mean - ratio_first_mean) / ratio_first_mean) * 100.0
        valid_slope = valid_ratio & (weights > 0) & mask
        if valid_slope.any():
            cum_dist = np.cumsum(delta_dist * mask) / 1000.0
            x = cum_dist[valid_slope]
            y = hr_pace_ratio[valid_slope]
            w = weights[valid_slope]
            if len(x) >= 2 and np.nanmax(x) > np.nanmin(x):
                slope = float(np.polyfit(x, y, 1, w=w)[0])
                mean_ratio = _weighted_mean(y, w)
                dist_span = float(np.nanmax(x) - np.nanmin(x))
                if mean_ratio > 0 and dist_span > 0:
                    cardiac_drift_slope_pct = (slope * dist_span / mean_ratio) * 100.0
        hr_ratio = np.full_like(hr_values, np.nan, dtype=float)
        if hr_max_used and hr_max_used > 0:
            if use_hrr and hr_rest is not None and hr_rest < hr_max_used:
                hr_ratio = (hr_values - hr_rest) / (hr_max_used - hr_rest)
            else:
                hr_ratio = hr_values / hr_max_used
        hr_ratio = np.where(hr_ratio < 0, np.nan, hr_ratio)
        hr_zones = _build_zone_table(
            hr_ratio,
            weights,
            HR_ZONES,
            lambda low, high: f">= {int(low*100)}%" if math.isinf(high) else f"{int(low*100)}-{int(high*100)}%",
        )
        heart_rate = {
            "mean_bpm": float(hr_mean),
            "max_bpm": float(hr_max_obs),
            "min_bpm": float(hr_min_obs),
            "hr_max_used": float(hr_max_used) if hr_max_used == hr_max_used else math.nan,
            "zones": hr_zones,
        }

    training_load = None
    if heart_rate is not None and heart_rate.get("zones") is not None:
        trimp = _edwards_trimp_from_zones(heart_rate["zones"])
        if trimp == trimp:
            training_load = {"trimp": float(trimp), "method": "edwards"}

    cadence = None
    if "cadence" in df and df["cadence"].notna().any():
        cad_values = df["cadence"].to_numpy(dtype=float)
        cad_mean = _weighted_mean(cad_values, weights)
        cad_max = float(np.nanmax(cad_values)) if np.isfinite(cad_values).any() else math.nan
        above_pct = math.nan
        if cadence_target is not None and cadence_target > 0:
            mask_target = np.isfinite(cad_values) & (weights > 0) & (cad_values >= cadence_target)
            total = float(weights[np.isfinite(cad_values) & (weights > 0)].sum())
            above = float(weights[mask_target].sum())
            above_pct = (above / total) * 100.0 if total > 0 else math.nan
        cadence = {
            "mean_spm": float(cad_mean),
            "max_spm": float(cad_max),
            "target_spm": float(cadence_target) if cadence_target else math.nan,
            "above_target_pct": float(above_pct),
        }

    power = None
    ftp_used = math.nan
    power_advanced = None
    if "power" in df and df["power"].notna().any():
        power_values = df["power"].to_numpy(dtype=float)
        power_mean = _weighted_mean(power_values, weights)
        power_max = float(np.nanmax(power_values)) if np.isfinite(power_values).any() else math.nan
        ftp_used = float(ftp_w) if ftp_w and ftp_w > 0 else math.nan
        if ftp_used != ftp_used:
            ftp_mask = np.isfinite(power_values) & (weights > 0)
            ftp_used = float(np.nanpercentile(power_values[ftp_mask], 95)) if ftp_mask.any() else math.nan
            ftp_estimated = True
        else:
            ftp_estimated = False
        power_ratio = np.full_like(power_values, np.nan, dtype=float)
        if ftp_used and ftp_used > 0:
            power_ratio = power_values / ftp_used
        power_zones = _build_zone_table(
            power_ratio,
            weights,
            POWER_ZONES,
            lambda low, high: f">= {int(low*100)}% FTP" if math.isinf(high) else f"{int(low*100)}-{int(high*100)}% FTP",
        )
        power = {
            "mean_w": float(power_mean),
            "max_w": float(power_max),
            "ftp_w": float(ftp_used),
            "ftp_estimated": ftp_estimated,
            "zones": power_zones,
        }

        power_series_1hz = _resample_series_1hz(power_values, delta_time, mask)
        normalized_power_w = _normalized_power_from_series(power_series_1hz)
        intensity_factor = (
            float(normalized_power_w / ftp_used)
            if normalized_power_w == normalized_power_w and ftp_used == ftp_used and ftp_used > 0
            else math.nan
        )
        tss = (
            (moving_time_s * normalized_power_w * intensity_factor) / (ftp_used * 3600.0) * 100.0
            if normalized_power_w == normalized_power_w
            and intensity_factor == intensity_factor
            and ftp_used == ftp_used
            and ftp_used > 0
            and moving_time_s > 0
            else math.nan
        )
        power_advanced = {
            "normalized_power_w": float(normalized_power_w),
            "intensity_factor": float(intensity_factor),
            "tss": float(tss),
        }
        power_curve = _compute_power_duration_curve_from_series(power_series_1hz, POWER_PEAK_DURATIONS_S)
        if power_curve:
            power_advanced["power_duration_curve"] = power_curve

    pace_zones = None
    pace_threshold = pace_threshold_s_per_km
    if pace_threshold is None or pace_threshold != pace_threshold:
        pace_threshold = pace_median
    if pace_threshold and pace_threshold > 0 and pace_mask.any():
        pace_ratio = pace / pace_threshold
        pace_zones = _build_zone_table(
            pace_ratio,
            weights,
            PACE_ZONES,
            lambda low, high: f">= {int(low*100)}% seuil"
            if math.isinf(high)
            else f"{int(low*100)}-{int(high*100)}% seuil",
        )

    pacing = {
        "pace_first_half_s_per_km": float(pace_first),
        "pace_second_half_s_per_km": float(pace_second),
        "pace_delta_s_per_km": float(pace_delta),
        "drift_s_per_km_per_km": float(drift),
        "cardiac_drift_pct": float(cardiac_drift_pct),
        "cardiac_drift_slope_pct": float(cardiac_drift_slope_pct),
        "stability_cv": float(stability_cv),
        "stability_iqr_ratio": float(stability_iqr),
        "gap_residual_median_s": float(gap_residual),
        "pace_threshold_s_per_km": float(pace_threshold) if pace_threshold == pace_threshold else math.nan,
    }

    return {
        "summary": summary,
        "heart_rate": heart_rate,
        "cadence": cadence,
        "power": power,
        "pace_zones": pace_zones,
        "running_dynamics": running_dynamics,
        "training_load": training_load,
        "power_advanced": power_advanced,
        "pacing": pacing,
    }


def format_zone_table(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["Zone", "Plage", "Temps", "% Temps"])
    formatted = df.copy()
    formatted["Temps"] = formatted["time_s"].apply(lambda v: seconds_to_mmss(v) if v == v else "-")
    formatted["% Temps"] = formatted["time_pct"].apply(lambda v: f"{v:.1f}%" if v == v else "-")
    return formatted[["zone", "range", "Temps", "% Temps"]].rename(
        columns={"zone": "Zone", "range": "Plage"}
    )
