from __future__ import annotations

import unittest

import pandas as pd

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


class TestActivityDfContract(unittest.TestCase):
    def test_validate_missing_columns(self) -> None:
        from core.contracts.activity_df_contract import validate_activity_df

        df = pd.DataFrame({"distance_m": [0.0, 1.0]})
        report = validate_activity_df(df)
        self.assertFalse(report.ok)
        self.assertTrue(any(i.code == "missing_columns" for i in report.issues))

    def test_validate_monotonic_distance(self) -> None:
        from core.contracts.activity_df_contract import coerce_activity_df, validate_activity_df

        df = pd.DataFrame(
            {
                "distance_m": [0.0, 10.0, 5.0],
                "delta_distance_m": [0.0, 10.0, -5.0],
                "delta_time_s": [1.0, 1.0, 1.0],
                "elapsed_time_s": [0.0, 1.0, 2.0],
                "speed_m_s": [1.0, 1.0, 1.0],
                "pace_s_per_km": [1000.0, 1000.0, 1000.0],
                "elevation": [0.0, 0.0, 0.0],
                "time": [None, None, None],
            }
        )
        df = coerce_activity_df(df)
        report = validate_activity_df(df)
        self.assertFalse(report.ok)
        self.assertTrue(any(i.code == "distance_non_monotone" for i in report.issues))

    def test_activity_service_load_validates(self) -> None:
        from pathlib import Path

        from services import activity_service

        project_dir = Path(__file__).resolve().parents[2]
        gpx_path = project_dir / "tests" / "course.gpx"
        data = gpx_path.read_bytes()
        loaded = activity_service.load_activity_from_bytes(data, gpx_path.name)
        self.assertFalse(loaded.df.empty)


if __name__ == "__main__":
    unittest.main()
