import math
from typing import List, Dict

import numpy as np
import pandas as pd

from core._shared import _unique_xy


def compute_climbs(
    df: pd.DataFrame,
    min_grade: float = 3.0,
    min_distance_m: float = 150.0,
    grade_series: pd.Series | None = None,
) -> List[Dict]:
    """Détecte les montées de façon robuste (fenêtre de distance + hystérésis + gap bridging).

    Contrat (API): retourne une liste de dicts avec les mêmes champs qu'historiquement:
    - distance_km, elevation_gain_m, avg_grade_percent, pace_s_per_km, vam_m_h,
      start_idx, end_idx, distance_m_end.

    Principe:
    - On construit une grille de distance régulière (step_m) et on interpole elevation et moving_time dessus.
    - La pente est calculée sur une fenêtre de distance (grade_window_m) pour limiter le bruit.
    - Détection via machine d'état:
      - start: grade >= start_grade_percent (min_grade) sur une distance minimale (start_confirm_distance_m)
      - continue: grade >= continue_grade_percent
      - gap: tolère un replat si grade >= gap_grade_percent tant que gap <= (gap_max_distance_m / gap_max_time_s)
      - stop: gap trop long ou descente nette (grade <= stop_down_grade_percent sur stop_down_distance_m)
    - Les métriques sont calculées sur le segment complet (incluant les replats tolérés).
    """

    if df.empty:
        return []
    required = {"distance_m", "delta_distance_m", "elevation", "delta_time_s", "pace_s_per_km"}
    if not required.issubset(set(df.columns)):
        return []

    # Tunables (conservative defaults).
    step_m = 5.0
    grade_window_m = 50.0
    elev_smooth_window_m = 25.0

    start_grade_percent = float(min_grade)
    continue_grade_percent = 1.0
    gap_grade_percent = 0.2
    gap_max_distance_m = 120.0
    gap_max_time_s = 30.0
    stop_down_grade_percent = -1.0
    stop_down_distance_m = 30.0
    start_confirm_distance_m = 20.0

    min_gain_m = 15.0
    min_duration_s = 45.0
    min_distance_m = float(min_distance_m)

    # Prepare arrays on original index order (keep start_idx/end_idx semantics stable).
    distance_m = pd.to_numeric(df["distance_m"], errors="coerce").fillna(0.0).astype(float)
    distance_m = distance_m.cummax()  # ensure non-decreasing
    delta_d = pd.to_numeric(df["delta_distance_m"], errors="coerce").fillna(0.0).astype(float)
    delta_t = pd.to_numeric(df["delta_time_s"], errors="coerce").fillna(0.0).astype(float)
    elev = pd.to_numeric(df["elevation"], errors="coerce").ffill().bfill().astype(float)
    pace = pd.to_numeric(df["pace_s_per_km"], errors="coerce").astype(float)

    # Moving time as a function of distance (injective even with pauses).
    moving = (delta_t > 0) & (delta_d > 0.5)
    moving_time_s = delta_t.where(moving, 0.0).cumsum()

    # Use grade_series if provided (already in %). Else compute robust grade from elevation.
    # For the detection, we always operate on the resampled grade (distance-windowed) for stability.
    base_grade = grade_series.reindex(df.index) if grade_series is not None else None

    dist_x, elev_y = _unique_xy(distance_m, elev)
    if dist_x.size < 2:
        return []
    _, time_y = _unique_xy(distance_m, moving_time_s)

    d0 = float(dist_x[0])
    d1 = float(dist_x[-1])
    if not (math.isfinite(d0) and math.isfinite(d1) and d1 > d0):
        return []

    step_m = float(step_m)
    grid = np.arange(d0, d1 + step_m, step_m)
    if grid.size < 2:
        return []

    elev_grid = np.interp(grid, dist_x, elev_y)
    time_grid = np.interp(grid, dist_x, time_y)

    # Optional: if grade_series is provided, we can interpolate it to the grid and smooth similarly.
    if base_grade is not None:
        dist_g, grade_g = _unique_xy(distance_m, pd.to_numeric(base_grade, errors="coerce"))
        grade_grid_raw = np.interp(grid, dist_g, grade_g) if dist_g.size >= 2 else np.full_like(grid, np.nan)
    else:
        grade_grid_raw = np.full_like(grid, np.nan)

    # Smooth elevation on a distance window.
    smooth_pts = max(1, int(round(elev_smooth_window_m / step_m)))
    elev_smooth = pd.Series(elev_grid).rolling(window=smooth_pts, center=True, min_periods=1).mean().to_numpy(dtype=float)

    # Compute robust grade using a distance lag.
    lag_pts = max(1, int(round(grade_window_m / step_m)))
    grade_grid = np.full_like(elev_smooth, np.nan, dtype=float)
    if lag_pts < elev_smooth.size:
        de = elev_smooth[lag_pts:] - elev_smooth[:-lag_pts]
        grade_grid[lag_pts:] = (de / float(grade_window_m)) * 100.0

    # If grade_series was provided, blend it lightly only where our computed grade is NaN.
    if np.isfinite(grade_grid_raw).any():
        missing = ~np.isfinite(grade_grid)
        grade_grid = np.where(missing, grade_grid_raw, grade_grid)

    # State machine over the grid.
    segments: list[tuple[int, int]] = []
    in_seg = False
    seg_start = 0
    start_run_m = 0.0
    gap_m = 0.0
    gap_t = 0.0
    downhill_m = 0.0
    last_ok = 0
    downhill_start = 0

    for i in range(len(grid)):
        g = grade_grid[i]
        if not math.isfinite(g):
            # Treat as a gap point.
            if in_seg:
                gap_m += step_m
                gap_t += float(time_grid[i] - time_grid[i - 1]) if i > 0 else 0.0
                if gap_m > gap_max_distance_m or gap_t > gap_max_time_s:
                    end = int(last_ok)
                    if end > seg_start:
                        segments.append((seg_start, end))
                    in_seg = False
                    start_run_m = 0.0
                continue
            start_run_m = 0.0
            continue

        if not in_seg:
            if g >= start_grade_percent:
                start_run_m += step_m
                if start_run_m >= start_confirm_distance_m:
                    in_seg = True
                    # grade[i] is computed over a lag window; shift the segment start back so
                    # the returned segment covers the full climb onset.
                    raw_start = max(0, i - int(round(start_run_m / step_m)) + 1)
                    seg_start = max(0, raw_start - lag_pts)
                    last_ok = i
                    gap_m = 0.0
                    gap_t = 0.0
                    downhill_m = 0.0
                    downhill_start = i
            else:
                start_run_m = 0.0
            continue

        # in segment
        if g <= stop_down_grade_percent:
            if downhill_m == 0.0:
                downhill_start = i
            downhill_m += step_m
        else:
            downhill_m = 0.0

        if downhill_m >= stop_down_distance_m:
            end = int(downhill_start - 1)
            if end > seg_start:
                segments.append((seg_start, end))
            in_seg = False
            start_run_m = 0.0
            gap_m = 0.0
            gap_t = 0.0
            downhill_m = 0.0
            continue

        if g >= continue_grade_percent:
            gap_m = 0.0
            gap_t = 0.0
            last_ok = i
            continue

        if g >= gap_grade_percent:
            gap_m += step_m
            gap_t += float(time_grid[i] - time_grid[i - 1]) if i > 0 else 0.0
            last_ok = i
            continue

        # g < gap_grade_percent
        gap_m += step_m
        gap_t += float(time_grid[i] - time_grid[i - 1]) if i > 0 else 0.0
        if gap_m > gap_max_distance_m or gap_t > gap_max_time_s:
            end = int(last_ok)
            if end > seg_start:
                segments.append((seg_start, end))
            in_seg = False
            start_run_m = 0.0
            gap_m = 0.0
            gap_t = 0.0
            downhill_m = 0.0

    if in_seg:
        end = int(last_ok)
        if end > seg_start:
            segments.append((seg_start, end))

    if not segments:
        return []

    # Build output items from segments.
    dist_arr = distance_m.to_numpy(dtype=float)
    time_arr = moving_time_s.to_numpy(dtype=float)
    dt_arr = delta_t.to_numpy(dtype=float)
    moving_arr = moving.to_numpy(dtype=bool)
    pace_arr = pace.to_numpy(dtype=float)

    climbs: list[dict[str, float | int]] = []
    for gs, ge in segments:
        seg_start_m = float(grid[gs])
        seg_end_m = float(grid[ge])
        if not (math.isfinite(seg_start_m) and math.isfinite(seg_end_m) and seg_end_m > seg_start_m):
            continue

        start_idx = int(np.searchsorted(dist_arr, seg_start_m, side="left"))
        end_idx = int(np.searchsorted(dist_arr, seg_end_m, side="right") - 1)
        start_idx = max(0, min(start_idx, len(df) - 1))
        end_idx = max(0, min(end_idx, len(df) - 1))
        if end_idx <= start_idx:
            continue

        seg_dist_m = float(dist_arr[end_idx] - dist_arr[start_idx])
        if not math.isfinite(seg_dist_m) or seg_dist_m < min_distance_m:
            continue

        # Moving time spent inside the segment (excludes pauses where dd~0).
        seg_dt = dt_arr[start_idx : end_idx + 1]
        seg_moving = moving_arr[start_idx : end_idx + 1]
        seg_time_s = float(np.nansum(seg_dt[(seg_moving) & (seg_dt > 0)]))
        if not math.isfinite(seg_time_s) or seg_time_s < min_duration_s:
            continue

        start_km = float(dist_arr[start_idx] / 1000.0) if math.isfinite(dist_arr[start_idx]) else math.nan
        end_km = float(dist_arr[end_idx] / 1000.0) if math.isfinite(dist_arr[end_idx]) else math.nan
        start_end_km = (
            f"{start_km:.2f} -> {end_km:.2f}" if math.isfinite(start_km) and math.isfinite(end_km) else "-"
        )

        # Gain from smoothed elevation on the grid for robustness.
        seg_elev = elev_smooth[gs : ge + 1]
        if seg_elev.size < 2:
            continue
        gain_m = float(np.clip(np.diff(seg_elev), 0, None).sum())
        if not math.isfinite(gain_m) or gain_m < min_gain_m:
            continue

        avg_grade = (gain_m / seg_dist_m) * 100.0 if seg_dist_m > 0 else math.nan
        vam = (gain_m / seg_time_s) * 3600.0 if seg_time_s > 0 else math.nan

        seg_pace = pace_arr[start_idx : end_idx + 1]
        seg_pace = seg_pace[np.isfinite(seg_pace) & (seg_pace > 0)]
        pace_med = float(np.median(seg_pace)) if seg_pace.size else math.nan

        climbs.append(
            {
                "start_idx": int(start_idx),
                "end_idx": int(end_idx),
                "distance_km": float(seg_dist_m / 1000.0),
                "elevation_gain_m": float(gain_m),
                "avg_grade_percent": float(avg_grade) if math.isfinite(avg_grade) else math.nan,
                "vam_m_h": float(vam) if math.isfinite(vam) else math.nan,
                "pace_s_per_km": float(pace_med) if math.isfinite(pace_med) else math.nan,
                "distance_m_end": float(dist_arr[end_idx]) if math.isfinite(dist_arr[end_idx]) else math.nan,

                # Additional UI-friendly fields (optional):
                "start_km": float(start_km),
                "end_km": float(end_km),
                "start_end_km": start_end_km,
                "duration_s": float(seg_time_s),
            }
        )

    if not climbs:
        return []

    # Keep deterministic ordering: largest gain first, then earlier start.
    climbs = sorted(climbs, key=lambda c: (-float(c.get("elevation_gain_m", 0.0)), float(c.get("start_idx", 0.0))))
    return climbs
