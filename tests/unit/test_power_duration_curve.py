from __future__ import annotations

import pandas as pd

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


def test_build_power_peak_durations_expands_beyond_one_hour() -> None:
    from core.metrics import _build_power_peak_durations

    durations = _build_power_peak_durations(7260)

    assert 3600 in durations
    assert durations[-1] == 7260
    assert any(d > 3600 for d in durations)


def test_build_power_peak_durations_keeps_short_activity_end() -> None:
    from core.metrics import _build_power_peak_durations

    durations = _build_power_peak_durations(50)

    assert durations[-1] == 50
    assert all(d <= 50 for d in durations)


def test_power_duration_curve_uses_dynamic_max_window() -> None:
    from core.metrics import _build_power_peak_durations, _compute_power_duration_curve_from_series

    series = pd.Series([250.0] * 5400, index=pd.to_timedelta(range(5400), unit="s"))
    durations = _build_power_peak_durations(len(series))
    curve = _compute_power_duration_curve_from_series(series, durations)

    assert curve
    assert int(curve[-1]["duration_s"]) == 5400
