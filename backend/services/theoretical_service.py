from __future__ import annotations

"""Orchestration activite theorique (prediction) (sans Streamlit)."""

import math
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from core.formatting import format_time_of_day
from core.theoretical_model import (
    build_theoretical_plot,
    compute_passage_at_distances,
    compute_theoretical_splits,
    compute_theoretical_summary,
    compute_theoretical_timing,
)
from core.utils import seconds_to_mmss
from services.models import (
    TheoreticalAdvanced,
    TheoreticalBase,
    TheoreticalFigures,
    TheoreticalPassages,
    TheoreticalResult,
)


def prepare_base(df: pd.DataFrame, base_pace_s_per_km: float) -> tuple[pd.DataFrame, dict[str, Any]]:
    df_theoretical = compute_theoretical_timing(df, base_pace_s_per_km, start_datetime=None)
    summary_base = compute_theoretical_summary(df_theoretical)
    return df_theoretical, summary_base


def compute_display_df(
    df_theoretical: pd.DataFrame,
    *,
    smoothing_segments: int,
    cap_min_per_km: float | None,
) -> tuple[pd.DataFrame, float, float]:
    pace_series = df_theoretical["segment_pace_s_per_km"]
    if smoothing_segments > 0:
        window = int(smoothing_segments) + 1
        pace_series = pace_series.rolling(window=window, min_periods=1, center=True).mean()

    default_cap_min = (pace_series.mean() / 60.0) * 1.2 if len(pace_series.dropna()) else 8.0
    used_cap_min = float(cap_min_per_km) if cap_min_per_km is not None else float(min(max(default_cap_min, 2.0), 15.0))

    df_display = df_theoretical.copy()
    df_display["segment_pace_s_per_km"] = pace_series.clip(upper=used_cap_min * 60.0)
    return df_display, float(default_cap_min), float(used_cap_min)


def compute_passages(
    df_theoretical: pd.DataFrame,
    *,
    start_datetime: datetime | None,
    target_distances_km: list[float] | None,
) -> TheoreticalPassages:
    df_calc = df_theoretical.copy()
    if start_datetime is not None:
        start_ts = pd.to_datetime(start_datetime)
        df_calc["passage_datetime"] = start_ts + pd.to_timedelta(df_calc["cumulative_time_s"], unit="s")
    else:
        df_calc["passage_datetime"] = pd.NaT

    distances = target_distances_km or []
    if start_datetime is not None and distances:
        passages_df = compute_passage_at_distances(df_calc, distances, start_datetime=start_datetime)
    else:
        passages_df = pd.DataFrame(columns=["distance_km", "cumulative_time_s", "passage_datetime"])

    markers: list[dict[str, Any]] = []
    if start_datetime is not None and not passages_df.empty:
        elevations = np.interp(
            passages_df["distance_km"],
            df_calc["distance_km_cumulative"],
            df_calc["elevation_m"],
        )
        for dist, elev, cum_time, passage_dt in zip(
            passages_df["distance_km"],
            elevations,
            passages_df["cumulative_time_s"],
            passages_df["passage_datetime"],
        ):
            time_label = format_time_of_day(passage_dt)
            markers.append(
                {
                    "distance_km": float(dist),
                    "elevation_m": float(elev),
                    "label": f"km {dist:.1f} - {time_label}",
                }
            )

    return TheoreticalPassages(df_calc=df_calc, passages=passages_df, markers=markers)


def build_base_figure(df_display: pd.DataFrame, markers: list[dict[str, Any]] | None = None) -> Any:
    return build_theoretical_plot(df_display, markers=markers)


def compute_splits(
    df_calc: pd.DataFrame,
    *,
    start_datetime: datetime | None,
    split_distance_km: float = 1.0,
) -> pd.DataFrame:
    return compute_theoretical_splits(df_calc, split_distance_km=split_distance_km, start_datetime=start_datetime)


def compute_weather_factor(
    *,
    enabled: bool,
    temp_c: int,
    humidity_pct: int,
    wind_ms: float,
) -> float:
    if not enabled:
        return 1.0
    temp_adj = max(0, temp_c - 15) * 0.005
    humidity_adj = max(0, (humidity_pct - 50) / 10) * 0.002
    wind_adj = wind_ms * 0.01
    weather_factor = 1 + temp_adj + humidity_adj + wind_adj
    return float(min(max(weather_factor, 0.85), 1.3))


def compute_advanced(
    df_calc: pd.DataFrame,
    *,
    weather_factor: float,
    split_bias: float,
    smoothing_segments: int,
    cap_adv_min_per_km: float | None,
) -> tuple[TheoreticalAdvanced, float]:
    pace_adjusted = _compute_adjusted_pace_base(
        df_calc,
        weather_factor=weather_factor,
        split_bias=split_bias,
    )

    cap_adv_default = (
        (pace_adjusted.dropna().mean() / 60.0) * 1.4 if len(pace_adjusted.dropna()) else 8.0
    )
    used_cap_adv_min = float(cap_adv_min_per_km) if cap_adv_min_per_km is not None else float(min(max(cap_adv_default, 2.0), 15.0))
    pace_adjusted = pace_adjusted.clip(lower=120.0, upper=used_cap_adv_min * 60.0)

    df_adjusted = df_calc.copy()
    df_adjusted["segment_pace_s_per_km"] = pace_adjusted
    df_adjusted["segment_time_s"] = df_adjusted["segment_pace_s_per_km"] * df_adjusted["segment_distance_km"]
    df_adjusted["cumulative_time_s"] = df_adjusted["segment_time_s"].cumsum()

    pace_adv_display = pace_adjusted.copy()
    if smoothing_segments > 0:
        window = int(smoothing_segments) + 1
        pace_adv_display = pace_adv_display.rolling(window=window, min_periods=1, center=True).mean()

    df_adjusted_display = df_adjusted.copy()
    df_adjusted_display["segment_pace_s_per_km"] = pace_adv_display
    df_adjusted_display["segment_time_s"] = (
        df_adjusted_display["segment_pace_s_per_km"] * df_adjusted_display["segment_distance_km"]
    )
    df_adjusted_display["cumulative_time_s"] = df_adjusted_display["segment_time_s"].cumsum()

    fig_adv = build_theoretical_plot(df_adjusted_display)
    summary_adjusted = compute_theoretical_summary(df_adjusted)

    categories: list[dict[str, Any]] = []
    for label, mask in [
        ("Montées (>3 %)", df_adjusted["segment_grade_percent"] > 3),
        ("Plats (-3 % à 3 %)", df_adjusted["segment_grade_percent"].between(-3, 3)),
        ("Descentes (< -3 %)", df_adjusted["segment_grade_percent"] < -3),
    ]:
        subset = df_adjusted[mask]
        if subset.empty:
            pace = math.nan
            dist = 0.0
        else:
            dist = float(subset["segment_distance_km"].sum())
            total_time = float(subset["segment_time_s"].sum())
            pace = total_time / dist if dist > 0 else math.nan
        categories.append(
            {
                "Terrain": label,
                "Distance (km)": dist,
                "Allure cible (min/km)": seconds_to_mmss(pace) if pace == pace else "-",
            }
        )

    csv_data = df_adjusted.to_csv(index=False)
    return (
        TheoreticalAdvanced(
            df_adjusted=df_adjusted,
            df_adjusted_display=df_adjusted_display,
            summary_adjusted=summary_adjusted,
            categories=categories,
            figure=fig_adv,
            csv_data=csv_data,
        ),
        float(used_cap_adv_min),
    )


def compute_adv_cap_default(
    df_calc: pd.DataFrame,
    *,
    weather_factor: float,
    split_bias: float,
) -> float:
    pace_adjusted = _compute_adjusted_pace_base(
        df_calc,
        weather_factor=weather_factor,
        split_bias=split_bias,
    )
    cap_adv_default = (
        (pace_adjusted.dropna().mean() / 60.0) * 1.4 if len(pace_adjusted.dropna()) else 8.0
    )
    return float(cap_adv_default)


def _compute_adjusted_pace_base(
    df_calc: pd.DataFrame,
    *,
    weather_factor: float,
    split_bias: float,
) -> pd.Series:
    """Serie d'allure ajustee de base avant clip/lissage.

    Partage entre compute_adv_cap_default() et compute_advanced().
    """

    pace_adjusted = df_calc["segment_pace_s_per_km"].replace([np.inf, -np.inf], np.nan)
    total_distance = float(df_calc["distance_km_cumulative"].iloc[-1]) if not df_calc.empty else 0.0
    progress = (df_calc["distance_km_cumulative"] / total_distance) if total_distance > 0 else 0.0
    pace_adjusted = pace_adjusted * float(weather_factor)
    split_factor = 1 - (split_bias / 100.0) * (progress - 0.5) * 2
    return pace_adjusted * split_factor


def analyze_theoretical_activity(
    df: pd.DataFrame,
    *,
    base_pace_s_per_km: float,
    smoothing_segments: int,
    cap_min_per_km: float | None,
    start_datetime: datetime | None,
    passage_distances_km: list[float] | None,
    weather_enabled: bool,
    temp_c: int,
    humidity_pct: int,
    wind_ms: float,
    split_bias: float,
    cap_adv_min_per_km: float | None,
) -> tuple[TheoreticalResult, float, float]:
    df_base, summary_base = prepare_base(df, base_pace_s_per_km)
    df_display, default_cap_min, used_cap_min = compute_display_df(
        df_base,
        smoothing_segments=smoothing_segments,
        cap_min_per_km=cap_min_per_km,
    )

    base = TheoreticalBase(df_base=df_base, summary_base=summary_base, default_cap_min_per_km=default_cap_min)
    passages = compute_passages(
        df_base,
        start_datetime=start_datetime,
        target_distances_km=passage_distances_km,
    )
    fig_base = build_theoretical_plot(df_display, markers=passages.markers)

    splits = compute_theoretical_splits(
        passages.df_calc,
        split_distance_km=1.0,
        start_datetime=start_datetime,
    )

    weather_factor = compute_weather_factor(
        enabled=weather_enabled,
        temp_c=temp_c,
        humidity_pct=humidity_pct,
        wind_ms=wind_ms,
    )
    advanced, used_cap_adv = compute_advanced(
        passages.df_calc,
        weather_factor=weather_factor,
        split_bias=split_bias,
        smoothing_segments=smoothing_segments,
        cap_adv_min_per_km=cap_adv_min_per_km,
    )

    figures = TheoreticalFigures(base=fig_base, advanced=advanced.figure)
    return (
        TheoreticalResult(
            base=base,
            df_display=df_display,
            passages=passages,
            splits=splits,
            figures=figures,
            advanced=advanced,
        ),
        float(used_cap_min),
        float(used_cap_adv),
    )
