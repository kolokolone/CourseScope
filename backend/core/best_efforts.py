import math

import numpy as np
import pandas as pd


def prepare_effort_arrays(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    if df.empty:
        return np.array([]), np.array([])

    working = df[["distance_m", "elapsed_time_s", "delta_time_s"]].copy()
    if working["elapsed_time_s"].isna().all():
        working["elapsed_time_s"] = working["delta_time_s"].fillna(0).cumsum()
    working = working.dropna(subset=["distance_m", "elapsed_time_s"])
    if working.empty:
        return np.array([]), np.array([])

    distances_m = working["distance_m"].to_numpy(dtype=float)
    times_s = working["elapsed_time_s"].to_numpy(dtype=float)
    return distances_m, times_s


def compute_best_efforts(df: pd.DataFrame) -> pd.DataFrame:
    """Detecte les meilleurs temps sur des distances cibles (1k, 5k, 10k, semi, marathon)."""
    distances_m, times_s = prepare_effort_arrays(df)
    if distances_m.size == 0 or times_s.size == 0:
        return pd.DataFrame(columns=["distance_km", "time_s", "pace_s_per_km"])

    targets_km = [1, 5, 10, 21.097, 42.195]
    results = []

    for target_km in targets_km:
        target_m = target_km * 1000.0
        best_time = math.nan
        start_idx = 0
        for end_idx in range(len(distances_m)):
            # Avance le debut tant que la fenetre depasse la distance cible
            while start_idx < end_idx and (distances_m[end_idx] - distances_m[start_idx]) >= target_m:
                current_time = times_s[end_idx] - times_s[start_idx]
                if current_time > 0 and (math.isnan(best_time) or current_time < best_time):
                    best_time = current_time
                start_idx += 1
        pace = best_time / target_km if target_km > 0 and not math.isnan(best_time) else math.nan
        results.append({"distance_km": target_km, "time_s": best_time, "pace_s_per_km": pace})

    return pd.DataFrame(results)


def compute_best_efforts_by_duration(
    df: pd.DataFrame, durations_s: list[int] | None = None
) -> pd.DataFrame:
    """Detecte les meilleures distances sur des durées cibles (ex: 1, 5, 10, 20, 30 min)."""
    durations_s = durations_s or [60, 300, 600, 1200, 1800]
    distances_m, times_s = prepare_effort_arrays(df)
    if distances_m.size == 0 or times_s.size == 0:
        return pd.DataFrame(columns=["duration_s", "distance_km", "time_s", "pace_s_per_km"])

    results = []
    for duration_s in durations_s:
        best_distance = 0.0
        best_time = math.nan
        start_idx = 0
        for end_idx in range(len(times_s)):
            while start_idx < end_idx and (times_s[end_idx] - times_s[start_idx]) >= duration_s:
                time_window = times_s[end_idx] - times_s[start_idx]
                dist_window = distances_m[end_idx] - distances_m[start_idx]
                if time_window > 0 and dist_window > best_distance:
                    best_distance = float(dist_window)
                    best_time = float(time_window)
                start_idx += 1
        distance_km = best_distance / 1000.0 if best_distance > 0 else math.nan
        pace = best_time / distance_km if distance_km > 0 and best_time == best_time else math.nan
        results.append(
            {
                "duration_s": float(duration_s),
                "distance_km": float(distance_km),
                "time_s": float(best_time) if best_time == best_time else math.nan,
                "pace_s_per_km": float(pace) if pace == pace else math.nan,
            }
        )

    return pd.DataFrame(results)


def compute_race_predictions(
    best_efforts_df: pd.DataFrame,
    targets_km: list[float] | None = None,
    exponent: float = 1.06,
) -> list[dict[str, float]]:
    """Predictions temps via formule de Riegel a partir des best efforts."""
    if best_efforts_df is None or best_efforts_df.empty:
        return []

    targets_km = targets_km or [5.0, 10.0, 21.097, 42.195]
    base = best_efforts_df.dropna(subset=["distance_km", "time_s"])
    if base.empty:
        return []

    out: list[dict[str, float]] = []
    for target in targets_km:
        best_time = math.nan
        best_base_dist = math.nan
        best_base_time = math.nan
        for _, row in base.iterrows():
            dist_km = float(row["distance_km"])
            time_s = float(row["time_s"])
            if dist_km <= 0 or time_s <= 0:
                continue
            predicted = time_s * (target / dist_km) ** exponent
            if predicted > 0 and (math.isnan(best_time) or predicted < best_time):
                best_time = predicted
                best_base_dist = dist_km
                best_base_time = time_s
        if best_time == best_time:
            out.append(
                {
                    "target_distance_km": float(target),
                    "predicted_time_s": float(best_time),
                    "base_distance_km": float(best_base_dist),
                    "base_time_s": float(best_base_time),
                    "exponent": float(exponent),
                }
            )

    return out
