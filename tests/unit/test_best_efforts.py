from __future__ import annotations

import math

import numpy as np
import pandas as pd

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


def _build_linear_df(n: int, speed_m_s: float) -> pd.DataFrame:
    delta_time_s = np.ones(n, dtype=float)
    elapsed_time_s = np.cumsum(delta_time_s)
    distance_m = elapsed_time_s * float(speed_m_s)
    return pd.DataFrame(
        {
            "distance_m": distance_m,
            "elapsed_time_s": elapsed_time_s,
            "delta_time_s": delta_time_s,
        }
    )


def test_best_efforts_by_duration_linear() -> None:
    from core.real_run_analysis import compute_best_efforts_by_duration

    df = _build_linear_df(n=301, speed_m_s=2.0)
    out = compute_best_efforts_by_duration(df, durations_s=[60, 120])
    assert set(out["duration_s"].tolist()) == {60.0, 120.0}

    row_60 = out[out["duration_s"] == 60.0].iloc[0]
    row_120 = out[out["duration_s"] == 120.0].iloc[0]
    assert math.isclose(float(row_60["distance_km"]), 0.12, rel_tol=1e-9)
    assert math.isclose(float(row_60["time_s"]), 60.0, rel_tol=1e-9)
    assert math.isclose(float(row_120["distance_km"]), 0.24, rel_tol=1e-9)
    assert math.isclose(float(row_120["time_s"]), 120.0, rel_tol=1e-9)


def test_best_efforts_by_distance_linear() -> None:
    from core.real_run_analysis import compute_best_efforts

    df = _build_linear_df(n=1001, speed_m_s=2.0)
    out = compute_best_efforts(df)
    row_1k = out[out["distance_km"] == 1.0].iloc[0]
    assert math.isclose(float(row_1k["time_s"]), 500.0, rel_tol=1e-9)
    assert math.isclose(float(row_1k["pace_s_per_km"]), 500.0, rel_tol=1e-9)
