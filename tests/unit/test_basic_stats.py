from __future__ import annotations

import unittest

import pandas as pd

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


class TestBasicStats(unittest.TestCase):
    def test_compute_basic_stats_simple(self) -> None:
        from core.stats.basic_stats import compute_basic_stats

        df = pd.DataFrame(
            {
                "distance_m": [0.0, 1000.0],
                "delta_time_s": [0.0, 300.0],
                "elapsed_time_s": [0.0, 300.0],
                "elevation": [0.0, 10.0],
                "time": ["2026-01-01 00:00:00", "2026-01-01 00:05:00"],
            }
        )
        stats = compute_basic_stats(df)
        self.assertAlmostEqual(stats.distance_km, 1.0)
        self.assertAlmostEqual(stats.total_time_s, 300.0)
        self.assertGreaterEqual(stats.elevation_gain_m, 0.0)


if __name__ == "__main__":
    unittest.main()
