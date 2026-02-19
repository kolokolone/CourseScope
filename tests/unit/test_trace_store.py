from __future__ import annotations

import unittest

import pandas as pd

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


class TestTraceStoreHelpers(unittest.TestCase):
    def test_route_fingerprint_is_stable(self) -> None:
        from storage.trace_store import compute_route_fingerprint

        df = pd.DataFrame(
            {
                'lat': [48.1, 48.1002, 48.1004],
                'lon': [2.3, 2.3002, 2.3004],
            }
        )
        a = compute_route_fingerprint(df)
        b = compute_route_fingerprint(df.copy())
        self.assertIsNotNone(a)
        self.assertEqual(a, b)

    def test_trace_metrics_compute_distance_and_elevation(self) -> None:
        from storage.trace_store import compute_trace_metrics

        df = pd.DataFrame(
            {
                'distance_m': [0.0, 500.0, 1000.0, 1500.0],
                'elevation': [100.0, 120.0, 110.0, 130.0],
            }
        )
        out = compute_trace_metrics(df)
        self.assertAlmostEqual(float(out['distance_km'] or 0.0), 1.5, places=6)
        self.assertAlmostEqual(float(out['elevation_gain_m'] or 0.0), 40.0, places=6)
        self.assertAlmostEqual(float(out['elevation_loss_m'] or 0.0), 10.0, places=6)
        self.assertEqual(float(out['elevation_min_m'] or 0.0), 100.0)
        self.assertEqual(float(out['elevation_max_m'] or 0.0), 130.0)


if __name__ == '__main__':
    unittest.main()
