from __future__ import annotations

import unittest

import pandas as pd

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


class TestTheoreticalAnalysisHelpers(unittest.TestCase):
    def test_parse_pace_input(self) -> None:
        from api.routes.analysis import _parse_pace_to_seconds_per_km

        self.assertEqual(_parse_pace_to_seconds_per_km('4:30'), 270.0)
        self.assertEqual(_parse_pace_to_seconds_per_km(' 05:00 '), 300.0)
        self.assertIsNone(_parse_pace_to_seconds_per_km('1:30'))
        self.assertIsNone(_parse_pace_to_seconds_per_km('invalid'))

    def test_resolve_target_from_time(self) -> None:
        from api.routes.analysis import _resolve_target_pace_and_time

        df = pd.DataFrame({'distance_m': [0.0, 5000.0, 10000.0]})
        mode, pace_s, time_s = _resolve_target_pace_and_time(
            activity_df=df,
            target_mode='time',
            target_pace=None,
            target_time='00:50:00',
        )
        self.assertEqual(mode, 'time')
        self.assertAlmostEqual(time_s, 3000.0, places=6)
        self.assertAlmostEqual(pace_s, 300.0, places=6)


if __name__ == '__main__':
    unittest.main()
