"""Pretraitement simple des echantillons allure-FC de progression.

Le module nettoie les series par point avant que l'indexeur ne construise,
directement depuis ces echantillons, les bins Pace-HR definitifs.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


PACE_HR_BIN_STEPS_S_PER_KM: tuple[int, ...] = (5, 10, 20, 30)


@dataclass(frozen=True)
class PaceHrPreprocessingConfig:
    pace_window_s: float = 30.0
    hr_hampel_window_s: float = 11.0
    hr_hampel_sigma: float = 3.0
    hr_hampel_min_deviation_bpm: float = 8.0
    hr_median_window_s: float = 5.0
    warmup_moving_time_s: float = 600.0
    min_pace_s_per_km: float = 0.0
    max_pace_s_per_km: float = 1800.0
    min_hr_bpm: float = 40.0
    max_hr_bpm: float = 240.0


DEFAULT_PACE_HR_PREPROCESSING_CONFIG = PaceHrPreprocessingConfig()


def _empty_prepared_frame(index: pd.Index) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "delta_time_s": pd.Series(0.0, index=index, dtype=float),
            "pace_smoothed_s_per_km": pd.Series(np.nan, index=index, dtype=float),
            "heart_rate_clean_bpm": pd.Series(np.nan, index=index, dtype=float),
            "after_warmup": pd.Series(False, index=index, dtype=bool),
            "valid": pd.Series(False, index=index, dtype=bool),
        },
        index=index,
    )


def _rolling_pace(
    delta_time_s: np.ndarray,
    delta_distance_m: np.ndarray,
    *,
    window_s: float,
) -> np.ndarray:
    """Calcule temps/distance sur une fenetre glissante continue."""

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


def _clean_heart_rate(
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
    source = heart_rate.mask(deviation > hampel_threshold)
    smoothed = _time_rolling_median(
        source,
        elapsed_s,
        window_s=config.hr_median_window_s,
    )
    # Un point rejete ou absent reste absent : le filtre n'invente pas de FC.
    return smoothed.where(source.notna())


def prepare_pace_hr_samples(
    df: pd.DataFrame,
    *,
    config: PaceHrPreprocessingConfig = DEFAULT_PACE_HR_PREPROCESSING_CONFIG,
) -> pd.DataFrame:
    """Prepare les echantillons eligibles aux bins Pace-HR.

    Le pipeline est volontairement continu : il n'applique ni masque de
    mouvement, ni decoupage sur les pauses/trous, ni exclusion de transition.
    Les valeurs non finies ou negatives sont seulement neutralisees pour que
    les sommes temps/distance restent definies.
    """

    required = {"delta_time_s", "delta_distance_m", "heart_rate"}
    if df is None or df.empty or not required.issubset(df.columns):
        return _empty_prepared_frame(
            df.index if isinstance(df, pd.DataFrame) else pd.RangeIndex(0)
        )

    out = _empty_prepared_frame(df.index)
    dt_raw = pd.to_numeric(df["delta_time_s"], errors="coerce").astype(float)
    dd_raw = pd.to_numeric(df["delta_distance_m"], errors="coerce").astype(float)
    hr = pd.to_numeric(df["heart_rate"], errors="coerce").astype(float)

    dt = dt_raw.where(np.isfinite(dt_raw.to_numpy(dtype=float)) & (dt_raw > 0), 0.0)
    dd = dd_raw.where(np.isfinite(dd_raw.to_numpy(dtype=float)) & (dd_raw > 0), 0.0)

    pace_smoothed = pd.Series(
        _rolling_pace(
            dt.to_numpy(dtype=float),
            dd.to_numpy(dtype=float),
            window_s=config.pace_window_s,
        ),
        index=df.index,
        dtype=float,
    )

    plausible_hr = (
        np.isfinite(hr.to_numpy(dtype=float))
        & (hr > float(config.min_hr_bpm))
        & (hr < float(config.max_hr_bpm))
    )
    hr_clean = _clean_heart_rate(
        hr.where(plausible_hr),
        dt.to_numpy(dtype=float),
        config=config,
    )

    # Sans masque de mouvement lisse, une distance strictement positive est la
    # definition minimale du temps en mouvement pour l'exclusion initiale.
    moving_time_cumulative = dt.where(dd > 0, 0.0).cumsum()
    after_warmup = moving_time_cumulative > float(config.warmup_moving_time_s)

    pace_valid = (
        np.isfinite(pace_smoothed.to_numpy(dtype=float))
        & (pace_smoothed > float(config.min_pace_s_per_km))
        & (pace_smoothed < float(config.max_pace_s_per_km))
    )
    hr_valid = np.isfinite(hr_clean.to_numpy(dtype=float))
    valid = after_warmup & pace_valid & hr_valid & (dt > 0)

    out["delta_time_s"] = dt
    out["pace_smoothed_s_per_km"] = pace_smoothed
    out["heart_rate_clean_bpm"] = hr_clean
    out["after_warmup"] = after_warmup.astype(bool)
    out["valid"] = valid.astype(bool)
    return out
