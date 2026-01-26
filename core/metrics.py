from __future__ import annotations

import math
from typing import Any, Dict

import numpy as np
import pandas as pd

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
    distance_series = df["distance_m"].dropna() if "distance_m" in df else pd.Series(dtype=float)
    total_distance_m = float(distance_series.max()) if not distance_series.empty else 0.0

    times = df["time"].dropna() if "time" in df else pd.Series(dtype="datetime64[ns]")
    if len(times) >= 2:
        total_time_s = (times.iloc[-1] - times.iloc[0]).total_seconds()
    else:
        elapsed = df["elapsed_time_s"].dropna() if "elapsed_time_s" in df else pd.Series(dtype=float)
        total_time_s = float(elapsed.max()) if not elapsed.empty else 0.0
        if total_time_s == 0.0 and "delta_time_s" in df:
            total_time_s = float(df["delta_time_s"].fillna(0).clip(lower=0).sum())
    return total_time_s, total_distance_m


def _pace_from_deltas(delta_time_s: np.ndarray, delta_distance_m: np.ndarray) -> np.ndarray:
    pace = np.full_like(delta_time_s, np.nan, dtype=float)
    np.divide(delta_time_s, delta_distance_m, out=pace, where=delta_distance_m > 0)
    pace *= 1000.0
    return pace


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

    avg_pace = moving_time_s / (moving_distance_m / 1000.0) if moving_distance_m > 0 else math.nan
    avg_speed = (moving_distance_m / 1000.0) / (moving_time_s / 3600.0) if moving_time_s > 0 else math.nan

    gap_mean = math.nan
    pace_for_ratio = pace
    if gap_series is not None:
        gap_values = gap_series.to_numpy(dtype=float)
        gap_mean = _weighted_mean(gap_values, weights)
        pace_for_ratio = np.where(np.isfinite(gap_values), gap_values, pace)

    elevation_gain_m = 0.0
    elevation_loss_m = 0.0
    if "elevation" in df:
        elevation = df["elevation"].ffill().bfill().to_numpy(dtype=float)
        if len(elevation) > 1:
            diffs = np.diff(elevation)
            elevation_gain_m = float(np.clip(diffs, 0, None).sum())
            elevation_loss_m = float(np.abs(np.clip(diffs, None, 0)).sum())

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

    summary = {
        "total_time_s": float(total_time_s),
        "moving_time_s": float(moving_time_s),
        "pause_time_s": float(pause_time_s),
        "distance_km": float(total_distance_m / 1000.0) if total_distance_m > 0 else 0.0,
        "moving_distance_km": float(moving_distance_m / 1000.0) if moving_distance_m > 0 else 0.0,
        "average_pace_s_per_km": float(avg_pace),
        "average_speed_kmh": float(avg_speed),
        "gap_mean_s_per_km": float(gap_mean),
        "pace_median_s_per_km": float(pace_median),
        "pace_p10_s_per_km": float(pace_p10),
        "pace_p90_s_per_km": float(pace_p90),
        "elevation_gain_m": float(elevation_gain_m),
        "elevation_loss_m": float(elevation_loss_m),
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
            "hr_max_used": float(hr_max_used) if hr_max_used == hr_max_used else math.nan,
            "zones": hr_zones,
        }

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
