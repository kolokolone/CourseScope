"""Paquet de series derivees (sans couche UI)."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class DerivedSeries:
    grade_series: pd.Series
    moving_mask: pd.Series
    gap_series: pd.Series
