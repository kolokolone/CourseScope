from __future__ import annotations

import unittest

import pandas as pd

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


class TestMovingMask(unittest.TestCase):
    def test_compute_moving_mask_flags_long_pause(self) -> None:
        from core.real_run_analysis import compute_moving_mask

        # 10 seconds: first 3 moving, then 6 seconds stopped, then moving again.
        df = pd.DataFrame(
            {
                "speed_m_s": [1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
                "delta_time_s": [1.0] * 10,
            }
        )
        mask = compute_moving_mask(df, pause_threshold_m_s=0.5, min_pause_duration_s=5.0)
        self.assertEqual(len(mask), len(df))
        # Middle segment should be marked as not moving.
        self.assertTrue(mask.iloc[0])
        self.assertFalse(mask.iloc[4])
        # Comportement historique: le premier point apres la pause est aussi marque.
        self.assertFalse(mask.iloc[-1])

    def test_compute_moving_mask_does_not_flag_short_pause(self) -> None:
        from core.real_run_analysis import compute_moving_mask

        df = pd.DataFrame(
            {
                "speed_m_s": [1.0, 1.0, 0.0, 0.0, 1.0],
                "delta_time_s": [1.0, 1.0, 1.0, 1.0, 1.0],
            }
        )
        mask = compute_moving_mask(df, pause_threshold_m_s=0.5, min_pause_duration_s=5.0)
        self.assertTrue(mask.all())

    def test_compute_moving_mask_keeps_pause_contiguous_across_dt_zero(self) -> None:
        from core.real_run_analysis import compute_moving_mask

        # dt==0 does not break historical pause accumulation.
        df = pd.DataFrame(
            {
                "speed_m_s": [1.0, 0.0, 0.0, 0.0, 1.0],
                "delta_time_s": [1.0, 2.0, 0.0, 3.0, 1.0],
            }
        )
        mask = compute_moving_mask(df, pause_threshold_m_s=0.5, min_pause_duration_s=5.0)
        # Pause duration = 2 + 3 = 5, should be detected and include the first index after.
        self.assertTrue(mask.iloc[0])
        self.assertFalse(mask.iloc[1])
        self.assertFalse(mask.iloc[2])
        self.assertFalse(mask.iloc[3])
        self.assertFalse(mask.iloc[4])

    def test_compute_moving_mask_pause_at_end(self) -> None:
        from core.real_run_analysis import compute_moving_mask

        df = pd.DataFrame(
            {
                "speed_m_s": [1.0, 1.0, 0.0, 0.0, 0.0],
                "delta_time_s": [1.0, 1.0, 2.0, 2.0, 2.0],
            }
        )
        mask = compute_moving_mask(df, pause_threshold_m_s=0.5, min_pause_duration_s=5.0)
        self.assertTrue(mask.iloc[0])
        self.assertFalse(mask.iloc[2])
        self.assertFalse(mask.iloc[-1])


if __name__ == "__main__":
    unittest.main()
