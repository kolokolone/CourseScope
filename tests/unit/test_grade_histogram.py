import numpy as np

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


def test_grade_histogram_keeps_exact_overflow_boundaries_and_totals() -> None:
    from core.time_histograms import build_grade_histogram

    histogram = build_grade_histogram(
        np.array([-20.0, -4.0, 5.0, 20.0]),
        np.array([0.1, 0.2, 0.3, 0.4]),
        np.array([10.0, 20.0, 30.0, 40.0]),
    )
    rows = histogram["complete_classes"]

    assert rows[0]["is_overflow"] is True
    assert rows[0]["grade_bin_center_pct"] == -20.0
    assert rows[-1]["is_overflow"] is True
    assert rows[-1]["grade_bin_center_pct"] == 20.0
    assert sum(float(row["time_s"]) for row in rows) == 100.0
    assert sum(float(row["distance_km"]) for row in rows) == 1.0
