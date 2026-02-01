from __future__ import annotations

import pandas as pd

from core.constants import DEFAULT_GRADE_SMOOTH_WINDOW
from core.real_run_analysis import compute_grade_percent_series, compute_moving_mask
from registry.series_registry import SeriesRegistry


def _make_df() -> pd.DataFrame:
    # Minimal canonical-like DF for series endpoints.
    return pd.DataFrame(
        {
            "time": pd.date_range("2026-01-01", periods=6, freq="s"),
            "elapsed_time_s": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0],
            "delta_time_s": [0.0, 1.0, 1.0, 1.0, 1.0, 1.0],
            "distance_m": [0.0, 2.0, 4.0, 4.0, 6.0, 8.0],
            "delta_distance_m": [0.0, 2.0, 2.0, 0.0, 2.0, 2.0],
            "lat": [48.0] * 6,
            "lon": [2.0] * 6,
            "elevation": [10.0, 10.2, 10.4, 10.4, 10.6, 10.8],
            "speed_m_s": [0.0, 2.0, 2.0, 0.0, 2.0, 2.0],
            "pace_s_per_km": [300.0] * 6,
        }
    )


def test_series_registry_grade_uses_core() -> None:
    df = _make_df()
    registry = SeriesRegistry()

    out = registry.get_series_data(df=df, name="grade", x_axis="time", from_val=None, to_val=None, downsample=None)

    expected = compute_grade_percent_series(df, smooth_window=DEFAULT_GRADE_SMOOTH_WINDOW).fillna(0.0)
    assert len(out.x) == len(df)
    assert len(out.y) == len(df)
    assert out.y == expected.to_numpy().tolist()


def test_series_registry_moving_uses_core_and_is_numeric() -> None:
    df = _make_df()
    registry = SeriesRegistry()

    out = registry.get_series_data(df=df, name="moving", x_axis="time", from_val=None, to_val=None, downsample=None)

    expected = compute_moving_mask(df)
    assert len(out.x) == len(df)
    assert len(out.y) == len(df)
    # Pydantic schema expects List[float]; bools should serialize as 0/1.
    assert out.y == [float(v) for v in expected.to_numpy().tolist()]
