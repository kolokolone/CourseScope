from __future__ import annotations

import numpy as np
import pandas as pd

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


def _build_df(distance_m: np.ndarray, elevation_m: np.ndarray, *, dt_s: float = 1.0, pace_s_per_km: float = 360.0) -> pd.DataFrame:
    assert distance_m.ndim == 1
    assert elevation_m.ndim == 1
    assert distance_m.size == elevation_m.size
    n = int(distance_m.size)

    dist = pd.Series(distance_m, dtype=float)
    dd = dist.diff().fillna(0.0)
    dt = pd.Series(np.full(n, float(dt_s)), dtype=float)

    # Avoid NaNs on first row for downstream code.
    dd.iloc[0] = dd.iloc[1] if n > 1 else 0.0

    return pd.DataFrame(
        {
            "distance_m": dist,
            "delta_distance_m": dd,
            "elevation": pd.Series(elevation_m, dtype=float),
            "delta_time_s": dt,
            "pace_s_per_km": pd.Series(np.full(n, float(pace_s_per_km)), dtype=float),
        }
    )


def _linear_profile(
    *,
    total_m: float,
    step_m: float,
    grade_percent: float,
    elev0: float = 0.0,
    noise_amp_m: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    d = np.arange(0.0, float(total_m) + float(step_m), float(step_m))
    slope = float(grade_percent) / 100.0
    elev = elev0 + slope * d
    if noise_amp_m:
        # Deterministic pseudo-noise.
        elev = elev + noise_amp_m * np.sin(d / 7.0) + (noise_amp_m * 0.5) * np.cos(d / 11.0)
    return d, elev


def test_climbs_continuous_climb_with_noise_is_single_segment() -> None:
    from core.real_run_analysis import compute_climbs

    step = 5.0
    d, elev = _linear_profile(total_m=500.0, step_m=step, grade_percent=8.0, noise_amp_m=0.3)
    df = _build_df(d, elev, dt_s=1.0)

    climbs = compute_climbs(df)
    assert len(climbs) == 1
    c = climbs[0]
    for key in [
        "distance_km",
        "elevation_gain_m",
        "avg_grade_percent",
        "pace_s_per_km",
        "vam_m_h",
        "start_idx",
        "end_idx",
        "distance_m_end",
    ]:
        assert key in c
    assert c["end_idx"] > c["start_idx"]
    assert c["elevation_gain_m"] >= 20.0


def test_climbs_climb_with_short_flat_gap_stays_one_segment() -> None:
    from core.real_run_analysis import compute_climbs

    step = 5.0
    # 200m @ 8%, 40m flat, 200m @ 8%
    d1, e1 = _linear_profile(total_m=200.0, step_m=step, grade_percent=8.0, elev0=0.0)
    d2 = np.arange(step, 40.0 + step, step)
    e2 = np.full_like(d2, e1[-1])
    d3, e3 = _linear_profile(total_m=200.0, step_m=step, grade_percent=8.0, elev0=float(e2[-1]))
    d3 = d3 + float(d1[-1] + d2[-1])

    d = np.concatenate([d1, d1[-1] + d2, d3])
    elev = np.concatenate([e1, e2, e3])
    df = _build_df(d, elev, dt_s=1.0)

    climbs = compute_climbs(df)
    assert len(climbs) == 1
    assert climbs[0]["distance_km"] > 0.35


def test_climbs_descent_net_splits_into_two_segments() -> None:
    from core.real_run_analysis import compute_climbs

    step = 5.0
    d1, e1 = _linear_profile(total_m=250.0, step_m=step, grade_percent=7.0, elev0=0.0)
    # 60m descent @ -5%
    d2 = np.arange(step, 60.0 + step, step)
    e2 = e1[-1] + (-0.05) * d2
    d3, e3 = _linear_profile(total_m=250.0, step_m=step, grade_percent=7.0, elev0=float(e2[-1]))
    d3 = d3 + float(d1[-1] + d2[-1])

    d = np.concatenate([d1, d1[-1] + d2, d3])
    elev = np.concatenate([e1, e2, e3])
    df = _build_df(d, elev, dt_s=1.0)

    climbs = compute_climbs(df)
    assert len(climbs) == 2


def test_climbs_pause_with_zero_delta_distance_does_not_break_detection() -> None:
    from core.real_run_analysis import compute_climbs

    step = 5.0
    d, elev = _linear_profile(total_m=500.0, step_m=step, grade_percent=8.0, elev0=0.0)
    df = _build_df(d, elev, dt_s=1.0)

    # Inject a stop: 10 seconds with no distance change.
    pause_len = 10
    insert_at = 30
    pause_rows = df.iloc[[insert_at]].copy()
    pause_rows = pd.concat([pause_rows] * pause_len, ignore_index=True)
    pause_rows["delta_distance_m"] = 0.0
    pause_rows["delta_time_s"] = 1.0
    pause_rows["distance_m"] = float(df.iloc[insert_at]["distance_m"])

    df2 = pd.concat([df.iloc[:insert_at], pause_rows, df.iloc[insert_at:]], ignore_index=True)
    # Recompute deltas after insertion.
    df2["distance_m"] = pd.to_numeric(df2["distance_m"], errors="coerce").fillna(0.0)
    df2["distance_m"] = df2["distance_m"].cummax()
    df2["delta_distance_m"] = df2["distance_m"].diff().fillna(df2["delta_distance_m"]).clip(lower=0.0)

    climbs = compute_climbs(df2)
    assert len(climbs) == 1
