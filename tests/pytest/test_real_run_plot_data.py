from __future__ import annotations

import numpy as np
import pandas as pd

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


def test_compute_pace_vs_grade_data_basic() -> None:
    from core.constants import MOVING_SPEED_THRESHOLD_M_S
    from core.real_run_analysis import compute_pace_vs_grade_data

    n = 12
    df = pd.DataFrame(
        {
            "speed_m_s": [MOVING_SPEED_THRESHOLD_M_S + 0.1] * n,
            "delta_time_s": [5.0] * n,
            "pace_s_per_km": np.linspace(300.0, 360.0, n),
        }
    )
    # Keep grades in a single bin so quality gating keeps output non-empty.
    grade_series = pd.Series([0.0] * n, index=df.index)

    out = compute_pace_vs_grade_data(df, pace_series=df["pace_s_per_km"], grade_series=grade_series)

    assert list(out.columns) == [
        "grade_center",
        "pace_med_s_per_km",
        "pace_std_s_per_km",
        "pace_n",
        "time_s_bin",
        "pace_mean_w_s_per_km",
        "pace_q25_w_s_per_km",
        "pace_q50_w_s_per_km",
        "pace_q75_w_s_per_km",
        "pace_iqr_w_s_per_km",
        "pace_std_w_s_per_km",
        "pace_n_eff",
        "outlier_clip_frac",
    ]
    assert not out.empty
    assert bool(out["grade_center"].is_monotonic_increasing)


def test_compute_pace_vs_grade_data_reports_mask() -> None:
    from core.constants import MOVING_SPEED_THRESHOLD_M_S
    from core.real_run_analysis import compute_pace_vs_grade_data
    from core.transform_report import TransformReport

    n = 5
    df = pd.DataFrame(
        {
            "speed_m_s": [MOVING_SPEED_THRESHOLD_M_S + 0.1] * n,
            "delta_time_s": [1.0] * n,
            "pace_s_per_km": [300.0] * n,
        }
    )
    grade_series = pd.Series([0.0] * n, index=df.index)
    report = TransformReport()
    _ = compute_pace_vs_grade_data(df, pace_series=df["pace_s_per_km"], grade_series=grade_series, report=report)
    names = [s.name for s in report.steps]
    assert "pace_vs_grade:mask_moving" in names


def test_compute_residuals_vs_grade_data_basic() -> None:
    from core.constants import MOVING_SPEED_THRESHOLD_M_S
    from core.real_run_analysis import compute_residuals_vs_grade_data

    n = 12
    df = pd.DataFrame(
        {
            "speed_m_s": [MOVING_SPEED_THRESHOLD_M_S + 0.1] * n,
            "delta_time_s": [1.0] * n,
            "pace_s_per_km": [300.0] * n,
        }
    )
    grade_series = pd.Series([0.0] * n, index=df.index)

    out = compute_residuals_vs_grade_data(df, pace_series=df["pace_s_per_km"], grade_series=grade_series)

    assert list(out.columns) == ["grade_center", "residual_med", "residual_q1", "residual_q3"]
    assert not out.empty
    assert abs(float(out["residual_med"].iloc[0])) < 1e-9


def test_compute_map_df_reports_dropna() -> None:
    from core.transform_report import TransformReport
    from services.models import RealRunDerived
    from services.real_activity_service import compute_map_df

    df = pd.DataFrame(
        {
            "lat": [1.0, np.nan, 1.2],
            "lon": [2.0, 2.1, 2.2],
            "distance_m": [0.0, 10.0, 20.0],
            "pace_s_per_km": [300.0, 310.0, 320.0],
        }
    )
    derived = RealRunDerived(
        grade_series=pd.Series([0.0, 0.0, 0.0], index=df.index),
        moving_mask=pd.Series([True, True, True], index=df.index),
        gap_series=pd.Series([300.0, 310.0, 320.0], index=df.index),
    )
    report = TransformReport()
    out = compute_map_df(df, derived=derived, map_color_mode="pace", report=report)
    assert out.shape[0] == 2
    step = next(s for s in report.steps if s.name == "map_payload:dropna_lat_lon_distance")
    assert step.rows_in == 3
    assert step.rows_out == 2
