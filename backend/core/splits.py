import math

import numpy as np
import pandas as pd

from core._shared import _unique_xy, compute_elevation_gain


def compute_splits(df: pd.DataFrame, split_distance_km: float = 1.0) -> pd.DataFrame:
    """Decoupe la course en splits de ~1 km.
    
    Retourne pour chaque split:
    - split_index: Numéro du split (commence à 1)
    - distance_km: Distance du split en km
    - time_s: Temps du split en secondes
    - pace_s_per_km: Allure du split (s/km)
    - elevation_gain_m: Dénivelé positif du split (m)
    - avg_hr_bpm: Fréquence cardiaque moyenne du split (bpm) si disponible
    - elev_delta_m: Variation d'altitude totale du split (m)
    """
    columns = [
        "split_index",
        "distance_km",
        "time_s",
        "pace_s_per_km",
        "elevation_gain_m",
        "avg_hr_bpm",
        "elev_delta_m",
    ]

    if df.empty:
        return pd.DataFrame(columns=columns)

    split_distance_m = float(split_distance_km) * 1000.0

    # We exclude pauses from split pace by using moving time.
    # Without a full moving-mask here, we approximate "paused" as dt>0 with no distance progress.
    # This is closer to how Strava's default pace behaves (moving time), vs elapsed time.
    base_cols = ["distance_m", "elapsed_time_s"]
    if "elevation" in df.columns:
        base_cols.append("elevation")
    working = df[base_cols].copy()
    if "heart_rate" in df.columns:
        working["heart_rate"] = df["heart_rate"]

    working = working.dropna(subset=["distance_m"]).copy()
    if working.empty:
        return pd.DataFrame(columns=columns)

    # Ensure elapsed_time_s exists.
    if "elapsed_time_s" not in working.columns or working["elapsed_time_s"].isna().all():
        if "delta_time_s" in df.columns:
            working["elapsed_time_s"] = df["delta_time_s"].fillna(0).cumsum()
        else:
            return pd.DataFrame(columns=columns)

    working["distance_m"] = pd.to_numeric(working["distance_m"], errors="coerce")
    working["elapsed_time_s"] = pd.to_numeric(working["elapsed_time_s"], errors="coerce")

    working = working.dropna(subset=["distance_m", "elapsed_time_s"]).copy()
    if working.empty:
        return pd.DataFrame(columns=columns)

    # Sort by time, enforce monotonic distance.
    working = working.sort_values("elapsed_time_s").copy()
    working["distance_m"] = working["distance_m"].cummax()

    dt = working["elapsed_time_s"].diff().fillna(0.0)
    dd = working["distance_m"].diff().fillna(0.0)
    moving = (dt > 0) & (dd > 0.5)
    working["moving_time_s"] = dt.where(moving, 0.0).cumsum()

    dist_x, moving_y = _unique_xy(working["distance_m"], working["moving_time_s"])
    if dist_x.size == 0:
        return pd.DataFrame(columns=columns)

    total_distance_m = float(dist_x[-1])
    if not math.isfinite(total_distance_m) or total_distance_m <= 0:
        return pd.DataFrame(columns=columns)

    # Build split boundaries at exact distances: 0, 1km, 2km, ..., last partial.
    n_full = int(total_distance_m // split_distance_m)
    boundaries: list[float] = [0.0]
    for k in range(1, n_full + 1):
        boundaries.append(float(k) * split_distance_m)
    if boundaries[-1] < total_distance_m:
        boundaries.append(total_distance_m)

    # Optional elevation interpolation for delta/gain.
    elev_x: np.ndarray | None = None
    elev_y: np.ndarray | None = None
    if "elevation" in working.columns and not working["elevation"].isna().all():
        elev_series = working["elevation"].ffill().bfill()
        elev_x, elev_y = _unique_xy(working["distance_m"], elev_series)

    splits: list[dict[str, float]] = []
    for i in range(len(boundaries) - 1):
        start_m = float(boundaries[i])
        end_m = float(boundaries[i + 1])
        if end_m <= start_m:
            continue

        distance_km = (end_m - start_m) / 1000.0
        if distance_km <= 0:
            continue

        t0 = float(np.interp(start_m, dist_x, moving_y))
        t1 = float(np.interp(end_m, dist_x, moving_y))
        time_s = t1 - t0
        pace_s_per_km = time_s / distance_km if time_s > 0 and math.isfinite(time_s) else math.nan

        elevation_gain_m = 0.0
        elev_delta_m = 0.0
        if elev_x is not None and elev_y is not None and elev_x.size:
            e0 = float(np.interp(start_m, elev_x, elev_y))
            e1 = float(np.interp(end_m, elev_x, elev_y))
            elev_delta_m = e1 - e0

            seg = working[(working["distance_m"] >= start_m) & (working["distance_m"] <= end_m)].copy()
            seg = seg.sort_values("distance_m")
            # Include boundary points for stable gain calculation.
            elevations = [e0]
            if "elevation" in seg.columns and not seg["elevation"].isna().all():
                elevations.extend(seg["elevation"].ffill().bfill().dropna().astype(float).tolist())
            elevations.append(e1)
            if len(elevations) > 1:
                elevation_gain_m = compute_elevation_gain(np.array(elevations, dtype=float))

        avg_hr_bpm = math.nan
        if "heart_rate" in working.columns and not working["heart_rate"].isna().all():
            hr_seg = working[(working["distance_m"] >= start_m) & (working["distance_m"] <= end_m)]["heart_rate"].dropna()
            if not hr_seg.empty:
                avg_hr_bpm = float(hr_seg.astype(float).mean())

        splits.append(
            {
                "split_index": float(i + 1),
                "distance_km": float(distance_km),
                "time_s": float(time_s) if math.isfinite(time_s) else math.nan,
                "pace_s_per_km": float(pace_s_per_km) if math.isfinite(pace_s_per_km) else math.nan,
                "elevation_gain_m": float(elevation_gain_m),
                "avg_hr_bpm": float(avg_hr_bpm) if math.isfinite(avg_hr_bpm) else math.nan,
                "elev_delta_m": float(elev_delta_m),
            }
        )

    out = pd.DataFrame(splits)
    if out.empty:
        return pd.DataFrame(columns=columns)

    # Ensure column order and numeric types.
    out = out[columns]
    out["split_index"] = out["split_index"].astype(int)
    return out
