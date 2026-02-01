import numpy as np
import pandas as pd

from backend.core.contracts.activity_df_contract import validate_activity_df


def test_validate_activity_df_running_dynamics_optional_when_none():
    # Minimal valid dataframe (required columns only), without running-dynamics columns.
    df = pd.DataFrame(
        {
            "distance_m": [0.0, 10.0, 20.0],
            "delta_distance_m": [np.nan, 10.0, 10.0],
            "delta_time_s": [np.nan, 1.0, 1.0],
            "elapsed_time_s": [0.0, 1.0, 2.0],
            "speed_m_s": [0.0, 10.0, 10.0],
            "pace_s_per_km": [np.nan, 100.0, 100.0],
            "elevation": [0.0, 0.0, 0.0],
        }
    )

    report = validate_activity_df(df, expect_running_dynamics_all_nan=None)
    assert report.ok


def test_validate_activity_df_running_dynamics_required_when_true():
    # Same dataframe, but now asking for running dynamics to be present/validated.
    df = pd.DataFrame(
        {
            "distance_m": [0.0, 10.0, 20.0],
            "delta_distance_m": [np.nan, 10.0, 10.0],
            "delta_time_s": [np.nan, 1.0, 1.0],
            "elapsed_time_s": [0.0, 1.0, 2.0],
            "speed_m_s": [0.0, 10.0, 10.0],
            "pace_s_per_km": [np.nan, 100.0, 100.0],
            "elevation": [0.0, 0.0, 0.0],
        }
    )

    report = validate_activity_df(df, expect_running_dynamics_all_nan=True)
    assert not report.ok
    assert any(issue.code == "missing_running_dynamics_columns" for issue in report.issues)
