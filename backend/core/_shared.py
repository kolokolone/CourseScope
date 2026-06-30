from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    """Weighted mean robuste aux NaN et poids nuls/negatifs."""
    mask = np.isfinite(values) & np.isfinite(weights) & (weights > 0)
    if not mask.any():
        return math.nan
    return float(np.nansum(values[mask] * weights[mask]) / np.nansum(weights[mask]))


def _unique_xy(x: pd.Series, y: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    """Deduplique (x, y) en gardant la derniere valeur y pour chaque x unique."""
    tmp = pd.DataFrame({"x": x.to_numpy(dtype=float), "y": y.to_numpy(dtype=float)})
    tmp = tmp.dropna().groupby("x", as_index=False).last()
    return tmp["x"].to_numpy(dtype=float), tmp["y"].to_numpy(dtype=float)


def compute_elevation_gain(elevation: np.ndarray) -> float:
    """Denivele positif cumule (m) a partir d'un tableau d'altitudes."""
    if len(elevation) < 2:
        return 0.0
    return float(np.clip(np.diff(elevation), 0, None).sum())


def compute_elevation_loss(elevation: np.ndarray) -> float:
    """Denivele negatif cumule (m) a partir d'un tableau d'altitudes."""
    if len(elevation) < 2:
        return 0.0
    return float(np.abs(np.clip(np.diff(elevation), None, 0)).sum())
