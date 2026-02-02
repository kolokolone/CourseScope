from __future__ import annotations

import numpy as np
import pandas as pd

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


def _df_base(n: int) -> pd.DataFrame:
    # Minimal canonical columns needed by compute_derived_series / analyze_real_activity.
    dt = np.ones(n, dtype=float)
    dd = np.ones(n, dtype=float)
    elapsed = np.cumsum(dt)
    dist = np.cumsum(dd)
    speed = dd / dt
    pace = 1000.0 / speed
    return pd.DataFrame(
        {
            "lat": [np.nan] * n,
            "lon": [np.nan] * n,
            "elevation": np.zeros(n, dtype=float),
            "time": pd.NaT,
            "distance_m": dist,
            "delta_distance_m": dd,
            "elapsed_time_s": elapsed,
            "delta_time_s": dt,
            "speed_m_s": speed,
            "pace_s_per_km": pace,
        }
    )


def test_pace_vs_grade_binning_includes_minus20_and_plus20() -> None:
    from core.real_run_analysis import compute_pace_vs_grade_data

    n = 80
    df = _df_base(n)
    df["speed_m_s"] = 2.0
    df["pace_s_per_km"] = 500.0

    # Two clusters pinned exactly at the clip bounds.
    grade = pd.Series([-20.0] * (n // 2) + [20.0] * (n // 2), index=df.index)

    out = compute_pace_vs_grade_data(df, pace_series=df["pace_s_per_km"], grade_series=grade)
    assert -20.0 in set(np.round(out["grade_center"].to_numpy(dtype=float), 6))
    assert 20.0 in set(np.round(out["grade_center"].to_numpy(dtype=float), 6))


def test_pace_vs_grade_filters_pauses_but_keeps_walking() -> None:
    from core.real_run_analysis import compute_pace_vs_grade_data

    # Build enough duration to pass bin quality gating.
    n_move1 = 20
    n_pause = 6  # >= 5s => treated as a pause
    n_walk = 60
    n = n_move1 + n_pause + n_walk
    df = _df_base(n)

    df.loc[: n_move1 - 1, "speed_m_s"] = 2.5
    df.loc[: n_move1 - 1, "pace_s_per_km"] = 400.0

    # Pause block (very low speed).
    start = n_move1
    end = n_move1 + n_pause
    df.loc[start : end - 1, "speed_m_s"] = 0.1
    df.loc[start : end - 1, "pace_s_per_km"] = 5000.0

    # Walking block (kept as moving).
    df.loc[end:, "speed_m_s"] = 1.1
    df.loc[end:, "pace_s_per_km"] = 900.0

    grade = pd.Series([0.0] * n, index=df.index)

    out = compute_pace_vs_grade_data(df, pace_series=df["pace_s_per_km"], grade_series=grade)
    assert len(out) == 1

    # compute_moving_mask marks the pause window as non-moving, and also marks the first point after
    # the pause as non-moving (historic behavior).
    expected_time = float(n_move1 + n_walk - 1)  # dt=1 everywhere
    assert abs(float(out.loc[0, "time_s_bin"]) - expected_time) < 1e-6

    # Walking points are included, so the weighted median should be closer to walking pace.
    assert float(out.loc[0, "pace_q50_w_s_per_km"]) >= 800.0


def test_pace_vs_grade_time_weighting_affects_aggregates() -> None:
    from core.real_run_analysis import compute_pace_vs_grade_data

    # Two pace levels with different time weights.
    n_fast = 5
    n_slow = 5
    n = n_fast + n_slow
    df = _df_base(n)
    df["speed_m_s"] = 2.0
    df["pace_s_per_km"] = 300.0

    df.loc[: n_fast - 1, "pace_s_per_km"] = 300.0
    df.loc[n_fast:, "pace_s_per_km"] = 600.0

    df.loc[: n_fast - 1, "delta_time_s"] = 10.0
    df.loc[n_fast:, "delta_time_s"] = 30.0
    df["elapsed_time_s"] = df["delta_time_s"].cumsum()

    grade = pd.Series([10.0] * n, index=df.index)
    out = compute_pace_vs_grade_data(df, pace_series=df["pace_s_per_km"], grade_series=grade)
    assert len(out) == 1

    # Unweighted mean would be 450, weighted mean should be closer to 600.
    assert float(out.loc[0, "pace_mean_w_s_per_km"]) > 450.0
    # Weighted median should land on the slower pace level due to majority time weight.
    assert abs(float(out.loc[0, "pace_q50_w_s_per_km"]) - 600.0) < 1e-6


def test_pace_vs_grade_outlier_clipping_is_per_bin_and_non_flat() -> None:
    from core.real_run_analysis import compute_pace_vs_grade_data

    n = 120
    df = _df_base(n)
    df["speed_m_s"] = 2.0
    # Add some natural variation so IQR/MAD are non-zero.
    df["pace_s_per_km"] = np.linspace(405.0, 435.0, n)
    df["delta_time_s"] = 5.0
    df["elapsed_time_s"] = df["delta_time_s"].cumsum()

    # Non-flat bin (10%).
    grade = pd.Series([10.0] * n, index=df.index)

    # Inject a large outlier with meaningful weight.
    df.loc[n - 1, "pace_s_per_km"] = 5000.0
    df.loc[n - 1, "delta_time_s"] = 20.0
    df["elapsed_time_s"] = df["delta_time_s"].cumsum()

    out = compute_pace_vs_grade_data(df, pace_series=df["pace_s_per_km"], grade_series=grade)
    assert len(out) == 1
    assert float(out.loc[0, "outlier_clip_frac"]) > 0.0

    # Robust quantiles should stay in a sane range.
    assert float(out.loc[0, "pace_q75_w_s_per_km"]) < 1000.0


def test_pace_vs_grade_endpoint_and_figures_share_same_pace_defaults() -> None:
    from core.real_run_analysis import compute_derived_series, compute_pace_series
    from services.models import RealRunViewParams
    from services.real_activity_service import analyze_real_activity

    n = 150
    df = _df_base(n)
    df["speed_m_s"] = 2.0
    df["pace_s_per_km"] = 500.0
    df["delta_time_s"] = 2.0
    df["delta_distance_m"] = df["speed_m_s"] * df["delta_time_s"]
    df["distance_m"] = df["delta_distance_m"].cumsum()
    df["elapsed_time_s"] = df["delta_time_s"].cumsum()

    derived = compute_derived_series(df)
    view = RealRunViewParams()
    # Match analyze_real_activity's default cap logic: avg_pace * 1.4.
    cap_min_per_km = float((500.0 / 60.0) * 1.4)
    endpoint_pace = compute_pace_series(
        df,
        moving_mask=derived.moving_mask,
        pace_mode=view.pace_mode,
        smoothing_points=view.smoothing_points,
        cap_min_per_km=cap_min_per_km,
    )

    result = analyze_real_activity(df)
    # analyze_real_activity uses RealRunViewParams() defaults too.
    assert np.allclose(
        endpoint_pace.fillna(-1).to_numpy(dtype=float),
        result.pace_series.fillna(-1).to_numpy(dtype=float),
        atol=1e-6,
    )
