"""Statistiques de base (sans couche UI).

Ce module centralise les definitions de statistiques "socle" (distance, duree,
D+, etc.). Il reste volontairement leger pour etre reutilise dans d'autres
modules core sans tirer des dependances lourdes (plotting).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BasicStats:
    distance_m: float
    distance_km: float
    total_time_s: float
    moving_time_s: float
    elevation_gain_m: float
    elevation_loss_m: float
    start_time: pd.Timestamp | None
    end_time: pd.Timestamp | None


def _time_range_from_time_column(df: pd.DataFrame) -> tuple[pd.Timestamp | None, pd.Timestamp | None, float]:
    if "time" not in df:
        return None, None, 0.0
    times = pd.to_datetime(df["time"], errors="coerce").dropna()
    if len(times) < 2:
        return (times.iloc[0] if len(times) == 1 else None), None, 0.0
    start = times.iloc[0]
    end = times.iloc[-1]
    return start, end, float((end - start).total_seconds())


def _total_time_fallback_seconds(df: pd.DataFrame) -> float:
    if "elapsed_time_s" in df:
        elapsed = pd.to_numeric(df["elapsed_time_s"], errors="coerce").dropna()
        if not elapsed.empty:
            return float(elapsed.max())
    if "delta_time_s" in df:
        dt = pd.to_numeric(df["delta_time_s"], errors="coerce").fillna(0.0)
        dt = dt.clip(lower=0.0)
        return float(dt.sum())
    return 0.0


def _distance_m(df: pd.DataFrame) -> float:
    if "distance_m" not in df:
        return 0.0
    dist = pd.to_numeric(df["distance_m"], errors="coerce").dropna()
    return float(dist.max()) if not dist.empty else 0.0


def _elevation_gain_loss(df: pd.DataFrame) -> tuple[float, float]:
    if "elevation" not in df:
        return 0.0, 0.0
    elev = pd.to_numeric(df["elevation"], errors="coerce").dropna().to_numpy(dtype=float)
    if elev.size < 2:
        return 0.0, 0.0
    diffs = np.diff(elev)
    gain = float(np.clip(diffs, 0, None).sum())
    loss = float(np.abs(np.clip(diffs, None, 0)).sum())
    return gain, loss


def compute_basic_stats(df: pd.DataFrame, *, moving_mask: pd.Series | None = None) -> BasicStats:
    """Calcule les statistiques de base.

    La fonction est tolerante aux valeurs manquantes et retombe sur
    elapsed_time_s/delta_time_s si les timestamps ne sont pas disponibles.
    """

    distance_m = _distance_m(df)
    start, end, duration_s = _time_range_from_time_column(df)
    if duration_s <= 0:
        duration_s = _total_time_fallback_seconds(df)

    moving_time_s = 0.0
    if moving_mask is not None and ("delta_time_s" in df) and (not df.empty):
        dt = pd.to_numeric(df["delta_time_s"], errors="coerce").fillna(0.0)
        moving_time_s = float(dt.where(moving_mask, 0.0).sum())
    else:
        moving_time_s = float(duration_s)

    gain, loss = _elevation_gain_loss(df)
    return BasicStats(
        distance_m=float(distance_m),
        distance_km=float(distance_m / 1000.0) if distance_m > 0 else 0.0,
        total_time_s=float(duration_s),
        moving_time_s=float(moving_time_s),
        elevation_gain_m=float(gain),
        elevation_loss_m=float(loss),
        start_time=start,
        end_time=end,
    )
