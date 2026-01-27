from __future__ import annotations

import pandas as pd

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


def test_compute_theoretical_timing_reports_valid_segments() -> None:
    from core.theoretical_model import compute_theoretical_timing
    from core.transform_report import TransformReport

    df = pd.DataFrame(
        {
            # One zero-length segment (10 -> 10) should be filtered out.
            "distance_m": [0.0, 10.0, 10.0, 25.0],
            "elevation": [0.0, 0.0, 0.0, 0.0],
        }
    )
    report = TransformReport()
    out = compute_theoretical_timing(df, base_pace_s_per_km=300.0, report=report)
    assert out.shape[0] == 2

    names = [s.name for s in report.steps]
    assert "theoretical:point_to_segment" in names
    assert "theoretical:valid_segments" in names

    valid_step = next(s for s in report.steps if s.name == "theoretical:valid_segments")
    assert valid_step.rows_in == 3
    assert valid_step.rows_out == 2
