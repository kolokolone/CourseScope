"""Paquet de series derivees (sans couche UI)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd

from core.constants import MOVING_SPEED_THRESHOLD_M_S, DEFAULT_MIN_PAUSE_DURATION_S, DEFAULT_GRADE_SMOOTH_WINDOW
from core.stats.basic_stats import compute_basic_stats
from core.utils import seconds_to_mmss
from core.pace_grade import compute_grade_percent_series, compute_gap_series


@dataclass(frozen=True)
class DerivedSeries:
    grade_series: pd.Series
    moving_mask: pd.Series
    gap_series: pd.Series


def compute_moving_mask(
    df: pd.DataFrame,
    pause_threshold_m_s: float = MOVING_SPEED_THRESHOLD_M_S,
    min_pause_duration_s: float = DEFAULT_MIN_PAUSE_DURATION_S,
) -> pd.Series:
    """
    Approche type Strava :
    - Lisse la vitesse instantanee (mediane glissante) pour eviter les a-coups GPS.
    - Declare une pause si la vitesse lissee reste sous le seuil pendant >= min_pause_duration_s.
    Retourne un masque booleen (True = en mouvement).
    """
    speed = df["speed_m_s"].fillna(0)
    delta_time = df["delta_time_s"].fillna(0).to_numpy()
    speed_med = speed.rolling(window=3, center=True, min_periods=1).median().to_numpy()

    dt = np.where(delta_time > 0, delta_time, 0.0)
    moving = np.ones(len(df), dtype=bool)

    # Preserve le comportement historique :
    # - l'accumulation de pause ne considere que les indices avec dt>0
    # - quand une pause se termine, le premier index apres la pause est aussi marque comme non-mouvant
    active = np.flatnonzero(dt > 0)
    if active.size:
        low_active = speed_med[active] < float(pause_threshold_m_s)
        if low_active.any():
            # Encodage RLE (run-length) des sequences contigues "low speed" sur l'espace des index actifs.
            starts = np.flatnonzero(
                np.concatenate(([low_active[0]], low_active[1:] & ~low_active[:-1]))
            )
            ends = np.flatnonzero(
                np.concatenate((low_active[:-1] & ~low_active[1:], [low_active[-1]]))
            )
            for s_pos, e_pos in zip(starts, ends):
                if not low_active[s_pos]:
                    continue
                duration = float(dt[active[s_pos : e_pos + 1]].sum())
                if duration >= float(min_pause_duration_s):
                    start_idx = int(active[s_pos])
                    if (e_pos + 1) < active.size:
                        stop_idx = int(active[e_pos + 1])
                    else:
                        stop_idx = int(len(df) - 1)
                    moving[start_idx : stop_idx + 1] = False

    return pd.Series(moving, index=df.index)


def compute_derived_series(
    df: pd.DataFrame,
    pace_series: pd.Series | None = None,
    grade_smooth_window: int = DEFAULT_GRADE_SMOOTH_WINDOW,
    pause_threshold_m_s: float = MOVING_SPEED_THRESHOLD_M_S,
    min_pause_duration_s: float = DEFAULT_MIN_PAUSE_DURATION_S,
) -> DerivedSeries:
    """Calcule un ensemble de derives reutilisables (pente, moving mask, GAP)."""
    grade_series = compute_grade_percent_series(df, smooth_window=grade_smooth_window)
    moving_mask = compute_moving_mask(
        df, pause_threshold_m_s=pause_threshold_m_s, min_pause_duration_s=min_pause_duration_s
    )
    pace_series = pace_series if pace_series is not None else df["pace_s_per_km"]
    gap_series = compute_gap_series(df, pace_series=pace_series, grade_series=grade_series)
    return DerivedSeries(grade_series=grade_series, moving_mask=moving_mask, gap_series=gap_series)


def compute_summary_stats(df: pd.DataFrame, moving_mask: pd.Series | None = None) -> Dict[str, float]:
    """Calcule les statistiques principales d'une sortie reelle."""
    moving_mask = moving_mask if moving_mask is not None else compute_moving_mask(df)
    stats = compute_basic_stats(df, moving_mask=moving_mask)

    average_pace_s_per_km = stats.total_time_s / stats.distance_km if stats.distance_km > 0 else math.nan
    average_speed_kmh = (stats.distance_km) / (stats.total_time_s / 3600.0) if stats.total_time_s > 0 else math.nan

    return {
        "distance_km": stats.distance_km,
        "total_time_s": stats.total_time_s,
        "moving_time_s": stats.moving_time_s,
        "average_pace_s_per_km": average_pace_s_per_km,
        "average_speed_kmh": average_speed_kmh,
        "elevation_gain_m": stats.elevation_gain_m,
    }


def compute_pace_series(
    df: pd.DataFrame,
    *,
    moving_mask: pd.Series | None = None,
    pace_mode: str = "real_time",
    smoothing_points: int = 0,
    cap_min_per_km: float | None = None,
) -> pd.Series:
    """Compute a pace series in s/km.

    - pace_mode='real_time': uses df['pace_s_per_km'] (per-point pace).
    - pace_mode='moving_time': uses cumulative moving time / cumulative moving distance.
    - smoothing_points: if >0, applies a centered rolling mean with window=smoothing_points+1.
    - cap_min_per_km: if set, clips pace to at most cap_min_per_km*60.
    """

    if df.empty:
        return pd.Series(dtype=float)

    if pace_mode == "moving_time":
        dt = df["delta_time_s"].fillna(0)
        dd = df["delta_distance_m"].fillna(0)
        mask = moving_mask.reindex(df.index).fillna(False) if moving_mask is not None else pd.Series(True, index=df.index)

        moving_time_cum = dt.where(mask, 0).cumsum()
        moving_dist_km_cum = (dd.where(mask, 0).cumsum() / 1000.0).replace({0: float("nan")})
        pace = moving_time_cum / moving_dist_km_cum
    else:
        pace = df["pace_s_per_km"]

    if smoothing_points and int(smoothing_points) > 0:
        window = int(smoothing_points) + 1
        pace = pace.rolling(window=window, min_periods=1, center=True).mean()

    if cap_min_per_km is not None and math.isfinite(float(cap_min_per_km)):
        pace = pace.clip(upper=float(cap_min_per_km) * 60.0)

    return pace


def compute_pause_markers(df: pd.DataFrame, moving_mask: pd.Series | None = None) -> List[Dict]:
    """Identifie les pauses (moving_mask False) et retourne des marqueurs carte."""
    if df.empty or "lat" not in df or "lon" not in df:
        return []
    moving_mask = moving_mask if moving_mask is not None else compute_moving_mask(df)
    delta_time = df["delta_time_s"].fillna(0)
    markers: List[Dict] = []
    in_pause = False
    start_idx = 0
    duration = 0.0
    for i, moving in enumerate(moving_mask):
        if not moving and delta_time.iloc[i] > 0:
            if not in_pause:
                start_idx = i
                duration = 0.0
                in_pause = True
            duration += delta_time.iloc[i]
        else:
            if in_pause and duration >= 5.0:
                markers.append(
                    {
                        "lat": df.iloc[start_idx]["lat"],
                        "lon": df.iloc[start_idx]["lon"],
                        "label": f"Pause {seconds_to_mmss(duration)}",
                    }
                )
            in_pause = False
    if in_pause and duration >= 5.0:
        markers.append(
            {
                "lat": df.iloc[start_idx]["lat"],
                "lon": df.iloc[start_idx]["lon"],
                "label": f"Pause {seconds_to_mmss(duration)}",
            }
        )
    return markers
