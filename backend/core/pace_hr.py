"""Pretraitement robuste des echantillons allure-FC de progression.

Le module reste independant de la persistance. Il nettoie et aligne les
series par point avant que l'indexeur ne construise les bins Pace-HR.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PaceHrPreprocessingConfig:
    gap_floor_s: float = 5.0
    gap_multiplier: float = 3.0
    gap_ceiling_s: float = 15.0
    pace_window_s: float = 30.0
    hr_hampel_window_s: float = 11.0
    hr_hampel_sigma: float = 3.0
    hr_hampel_min_deviation_bpm: float = 8.0
    hr_median_window_s: float = 5.0
    hr_max_slew_bpm_per_s: float = 5.0
    warmup_moving_time_s: float = 600.0
    transition_lookback_s: float = 15.0
    transition_min_change_s_per_km: float = 30.0
    transition_min_change_ratio: float = 0.08
    transition_exclusion_s: float = 30.0
    min_pace_s_per_km: float = 0.0
    max_pace_s_per_km: float = 1800.0
    min_hr_bpm: float = 40.0
    max_hr_bpm: float = 240.0


DEFAULT_PACE_HR_PREPROCESSING_CONFIG = PaceHrPreprocessingConfig()


def _empty_prepared_frame(index: pd.Index) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "delta_time_s": pd.Series(np.nan, index=index, dtype=float),
            "pace_smoothed_s_per_km": pd.Series(np.nan, index=index, dtype=float),
            "heart_rate_clean_bpm": pd.Series(np.nan, index=index, dtype=float),
            "time_interval_valid": pd.Series(False, index=index, dtype=bool),
            "after_warmup": pd.Series(False, index=index, dtype=bool),
            "transition_stable": pd.Series(False, index=index, dtype=bool),
            "valid": pd.Series(False, index=index, dtype=bool),
        },
        index=index,
    )


def _adaptive_max_gap_s(
    delta_time_s: pd.Series, config: PaceHrPreprocessingConfig
) -> float:
    positive = delta_time_s[
        np.isfinite(delta_time_s.to_numpy(dtype=float)) & (delta_time_s > 0)
    ]
    if positive.empty:
        return float(config.gap_floor_s)
    reference = float(positive.median())
    return float(
        min(
            float(config.gap_ceiling_s),
            max(float(config.gap_floor_s), reference * float(config.gap_multiplier)),
        )
    )


def _contiguous_segments(mask: pd.Series) -> list[np.ndarray]:
    values = mask.to_numpy(dtype=bool)
    positions = np.flatnonzero(values)
    if positions.size == 0:
        return []
    splits = np.flatnonzero(np.diff(positions) > 1) + 1
    return [part for part in np.split(positions, splits) if part.size > 0]


def _rolling_pace_for_segment(
    delta_time_s: np.ndarray,
    delta_distance_m: np.ndarray,
    *,
    window_s: float,
) -> np.ndarray:
    """Calcule temps/distance sur une fenetre glissante sans traverser de trou."""

    n = int(delta_time_s.size)
    out = np.full(n, np.nan, dtype=float)
    if n == 0:
        return out

    dt = np.asarray(delta_time_s, dtype=float)
    dd = np.asarray(delta_distance_m, dtype=float)
    cum_t = np.concatenate(([0.0], np.cumsum(dt)))
    cum_d = np.concatenate(([0.0], np.cumsum(dd)))
    left = 0
    required_window = max(0.001, float(window_s))

    for right in range(n):
        end_t = float(cum_t[right + 1])
        while left < right and end_t - float(cum_t[left + 1]) >= required_window:
            left += 1
        time_window = end_t - float(cum_t[left])
        distance_window = float(cum_d[right + 1]) - float(cum_d[left])
        if time_window >= required_window and distance_window > 0:
            out[right] = time_window / (distance_window / 1000.0)
    return out


def _time_rolling_median(
    values: pd.Series,
    elapsed_s: np.ndarray,
    *,
    window_s: float,
    min_periods: int = 3,
) -> pd.Series:
    time_index = pd.to_timedelta(np.asarray(elapsed_s, dtype=float), unit="s")
    timed = pd.Series(values.to_numpy(dtype=float), index=time_index, dtype=float)
    rolled = timed.rolling(
        pd.Timedelta(seconds=max(0.001, float(window_s))),
        center=True,
        min_periods=max(1, int(min_periods)),
    ).median()
    return pd.Series(rolled.to_numpy(dtype=float), index=values.index, dtype=float)


def _clean_heart_rate_segment(
    heart_rate: pd.Series,
    delta_time_s: np.ndarray,
    *,
    config: PaceHrPreprocessingConfig,
) -> pd.Series:
    elapsed_s = np.cumsum(np.asarray(delta_time_s, dtype=float))
    local_median = _time_rolling_median(
        heart_rate,
        elapsed_s,
        window_s=config.hr_hampel_window_s,
    )
    deviation = (heart_rate - local_median).abs()
    local_mad = _time_rolling_median(
        deviation,
        elapsed_s,
        window_s=config.hr_hampel_window_s,
    )
    hampel_threshold = (float(config.hr_hampel_sigma) * 1.4826 * local_mad).clip(
        lower=float(config.hr_hampel_min_deviation_bpm)
    )
    hampel_outlier = deviation > hampel_threshold

    previous = heart_rate.shift(1)
    slew = (heart_rate - previous).abs() / pd.Series(
        np.asarray(delta_time_s, dtype=float), index=heart_rate.index, dtype=float
    )
    slew_outlier = slew > float(config.hr_max_slew_bpm_per_s)

    source = heart_rate.mask(hampel_outlier.fillna(False) | slew_outlier.fillna(False))
    smoothed = _time_rolling_median(
        source,
        elapsed_s,
        window_s=config.hr_median_window_s,
    )
    # Ne pas inventer une mesure au point rejete ou manquant.
    return smoothed.where(source.notna())


def _transition_stability_for_segment(
    pace_s_per_km: np.ndarray,
    delta_time_s: np.ndarray,
    *,
    config: PaceHrPreprocessingConfig,
) -> np.ndarray:
    pace = np.asarray(pace_s_per_km, dtype=float)
    elapsed_s = np.cumsum(np.asarray(delta_time_s, dtype=float))
    stable = np.ones(pace.size, dtype=bool)
    excluded_until_s = float("-inf")

    for pos in range(pace.size):
        now_s = float(elapsed_s[pos])
        if now_s <= excluded_until_s:
            stable[pos] = False
            continue

        target_s = now_s - float(config.transition_lookback_s)
        previous_pos = int(np.searchsorted(elapsed_s, target_s, side="right") - 1)
        if previous_pos < 0 or previous_pos >= pos:
            continue
        previous_pace = float(pace[previous_pos])
        current_pace = float(pace[pos])
        if not (
            np.isfinite(previous_pace)
            and np.isfinite(current_pace)
            and previous_pace > 0
        ):
            continue

        threshold = max(
            float(config.transition_min_change_s_per_km),
            abs(previous_pace) * float(config.transition_min_change_ratio),
        )
        if abs(current_pace - previous_pace) >= threshold:
            # La fenetre de lissage revele la transition apres son debut.
            # Retirer aussi les points depuis la reference evite de conserver
            # les premieres secondes deja affectees par le changement d'allure.
            stable[previous_pos + 1 : pos + 1] = False
            excluded_until_s = now_s + float(config.transition_exclusion_s)

    return stable


def prepare_pace_hr_samples(
    df: pd.DataFrame,
    *,
    moving_mask: pd.Series,
    config: PaceHrPreprocessingConfig = DEFAULT_PACE_HR_PREPROCESSING_CONFIG,
) -> pd.DataFrame:
    """Prepare les echantillons eligibles aux bins Pace-HR.

    Les fenetres sont traitees separement pour chaque portion continue afin
    qu'aucun lissage ne traverse une pause ou un trou d'enregistrement.
    """

    required = {"delta_time_s", "delta_distance_m", "heart_rate"}
    if df is None or df.empty or not required.issubset(df.columns):
        return _empty_prepared_frame(
            df.index if isinstance(df, pd.DataFrame) else pd.RangeIndex(0)
        )

    out = _empty_prepared_frame(df.index)
    dt = pd.to_numeric(df["delta_time_s"], errors="coerce").astype(float)
    dd = pd.to_numeric(df["delta_distance_m"], errors="coerce").astype(float)
    hr = pd.to_numeric(df["heart_rate"], errors="coerce").astype(float)
    moving = moving_mask.reindex(df.index).fillna(False).astype(bool)

    max_gap_s = _adaptive_max_gap_s(dt, config)
    time_interval_valid = pd.Series(
        np.isfinite(dt.to_numpy(dtype=float)) & (dt > 0) & (dt <= max_gap_s),
        index=df.index,
        dtype=bool,
    )
    distance_valid = pd.Series(
        np.isfinite(dd.to_numpy(dtype=float)) & (dd > 0),
        index=df.index,
        dtype=bool,
    )
    segment_mask = moving & time_interval_valid & distance_valid

    moving_time_cumulative = dt.where(moving & time_interval_valid, 0.0).cumsum()
    after_warmup = moving_time_cumulative > float(config.warmup_moving_time_s)

    pace_smoothed = pd.Series(np.nan, index=df.index, dtype=float)
    hr_clean = pd.Series(np.nan, index=df.index, dtype=float)
    transition_stable = pd.Series(False, index=df.index, dtype=bool)

    for positions in _contiguous_segments(segment_mask):
        labels = df.index.take(positions)
        segment_dt = dt.iloc[positions].to_numpy(dtype=float)
        segment_dd = dd.iloc[positions].to_numpy(dtype=float)
        segment_pace = _rolling_pace_for_segment(
            segment_dt,
            segment_dd,
            window_s=config.pace_window_s,
        )
        pace_smoothed.loc[labels] = segment_pace

        segment_hr = hr.iloc[positions].copy()
        plausible_hr = (
            np.isfinite(segment_hr.to_numpy(dtype=float))
            & (segment_hr > float(config.min_hr_bpm))
            & (segment_hr < float(config.max_hr_bpm))
        )
        segment_hr = segment_hr.where(plausible_hr)
        hr_clean.loc[labels] = _clean_heart_rate_segment(
            segment_hr,
            segment_dt,
            config=config,
        ).to_numpy(dtype=float)
        transition_stable.loc[labels] = _transition_stability_for_segment(
            segment_pace,
            segment_dt,
            config=config,
        )

    pace_valid = (
        np.isfinite(pace_smoothed.to_numpy(dtype=float))
        & (pace_smoothed > float(config.min_pace_s_per_km))
        & (pace_smoothed < float(config.max_pace_s_per_km))
    )
    hr_valid = np.isfinite(hr_clean.to_numpy(dtype=float))
    valid = segment_mask & after_warmup & transition_stable & pace_valid & hr_valid

    out["delta_time_s"] = dt
    out["pace_smoothed_s_per_km"] = pace_smoothed
    out["heart_rate_clean_bpm"] = hr_clean
    out["time_interval_valid"] = time_interval_valid
    out["after_warmup"] = after_warmup.astype(bool)
    out["transition_stable"] = transition_stable
    out["valid"] = valid.astype(bool)
    return out
