from __future__ import annotations

import math
import unittest
from dataclasses import replace

import numpy as np
import pandas as pd

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


def _activity_frame(
    paces_s_per_km: list[float],
    *,
    heart_rates: list[float] | None = None,
    delta_times_s: list[float] | None = None,
) -> pd.DataFrame:
    n = len(paces_s_per_km)
    dt = np.asarray(
        delta_times_s if delta_times_s is not None else [1.0] * n, dtype=float
    )
    pace = np.asarray(paces_s_per_km, dtype=float)
    speed = np.divide(
        1000.0, pace, out=np.zeros(n, dtype=float), where=np.isfinite(pace) & (pace > 0)
    )
    hr = np.asarray(
        heart_rates if heart_rates is not None else [140.0] * n, dtype=float
    )
    return pd.DataFrame(
        {
            "delta_time_s": dt,
            "delta_distance_m": speed * dt,
            "speed_m_s": speed,
            "pace_s_per_km": pace,
            "heart_rate": hr,
        }
    )


class TestPaceHrPreprocessing(unittest.TestCase):
    def _config(self, **overrides):
        from core.pace_hr import DEFAULT_PACE_HR_PREPROCESSING_CONFIG

        defaults = {
            "warmup_moving_time_s": 0.0,
            "pace_window_s": 3.0,
            "hr_hampel_window_s": 7.0,
            "hr_median_window_s": 5.0,
            "transition_min_change_s_per_km": 10_000.0,
            "transition_min_change_ratio": 10.0,
            "hr_max_slew_bpm_per_s": 50.0,
        }
        defaults.update(overrides)
        return replace(DEFAULT_PACE_HR_PREPROCESSING_CONFIG, **defaults)

    def test_reuses_the_real_moving_mask_and_restarts_windows_after_pause(self) -> None:
        from core.derived import compute_moving_mask
        from core.pace_hr import prepare_pace_hr_samples

        paces = [300.0] * 25
        df = _activity_frame(paces)
        df.loc[8:14, ["delta_distance_m", "speed_m_s", "pace_s_per_km"]] = [
            0.0,
            0.0,
            math.nan,
        ]
        moving_mask = compute_moving_mask(df)

        prepared = prepare_pace_hr_samples(
            df, moving_mask=moving_mask, config=self._config()
        )

        self.assertFalse(bool(prepared.loc[8:14, "valid"].any()))
        self.assertTrue(math.isnan(float(prepared.loc[16, "pace_smoothed_s_per_km"])))
        self.assertTrue(bool(prepared.loc[18:, "valid"].any()))

    def test_rejects_long_time_gap_and_does_not_smooth_across_it(self) -> None:
        from core.pace_hr import prepare_pace_hr_samples

        dt = [1.0] * 20
        dt[10] = 20.0
        df = _activity_frame([300.0] * 20, delta_times_s=dt)
        config = self._config(gap_floor_s=3.0, gap_multiplier=3.0, gap_ceiling_s=5.0)

        prepared = prepare_pace_hr_samples(
            df,
            moving_mask=pd.Series(True, index=df.index),
            config=config,
        )

        self.assertFalse(bool(prepared.loc[10, "time_interval_valid"]))
        self.assertFalse(bool(prepared.loc[10, "valid"]))
        self.assertTrue(math.isnan(float(prepared.loc[12, "pace_smoothed_s_per_km"])))
        self.assertTrue(
            math.isfinite(float(prepared.loc[13, "pace_smoothed_s_per_km"]))
        )

    def test_smooths_noisy_pace_using_time_over_distance(self) -> None:
        from core.pace_hr import prepare_pace_hr_samples

        df = _activity_frame([280.0, 320.0] * 20)
        prepared = prepare_pace_hr_samples(
            df,
            moving_mask=pd.Series(True, index=df.index),
            config=self._config(pace_window_s=6.0),
        )

        values = prepared["pace_smoothed_s_per_km"].dropna().to_numpy(dtype=float)
        self.assertGreater(values.size, 10)
        self.assertLess(float(np.nanstd(values)), 1.0)
        self.assertAlmostEqual(float(np.nanmedian(values)), 298.7, delta=1.0)

    def test_hampel_filter_rejects_isolated_hr_spike(self) -> None:
        from core.pace_hr import prepare_pace_hr_samples

        heart_rates = [140.0] * 30
        heart_rates[15] = 220.0
        df = _activity_frame([300.0] * 30, heart_rates=heart_rates)
        prepared = prepare_pace_hr_samples(
            df,
            moving_mask=pd.Series(True, index=df.index),
            config=self._config(hr_max_slew_bpm_per_s=5.0),
        )

        self.assertAlmostEqual(float(prepared.loc[14, "heart_rate_clean_bpm"]), 140.0)
        self.assertTrue(math.isnan(float(prepared.loc[15, "heart_rate_clean_bpm"])))
        self.assertFalse(bool(prepared.loc[15, "valid"]))

    def test_excludes_first_ten_seconds_of_moving_time_when_configured(self) -> None:
        from core.pace_hr import prepare_pace_hr_samples

        df = _activity_frame([300.0] * 25)
        prepared = prepare_pace_hr_samples(
            df,
            moving_mask=pd.Series(True, index=df.index),
            config=self._config(warmup_moving_time_s=10.0),
        )

        self.assertFalse(bool(prepared.loc[:9, "after_warmup"].any()))
        self.assertTrue(bool(prepared.loc[10, "after_warmup"]))
        self.assertFalse(bool(prepared.loc[:9, "valid"].any()))
        self.assertTrue(bool(prepared.loc[10:, "valid"].any()))

    def test_excludes_seconds_following_significant_pace_change(self) -> None:
        from core.pace_hr import prepare_pace_hr_samples

        df = _activity_frame(([300.0] * 40) + ([240.0] * 40))
        config = self._config(
            transition_lookback_s=5.0,
            transition_min_change_s_per_km=30.0,
            transition_min_change_ratio=0.08,
            transition_exclusion_s=10.0,
        )
        prepared = prepare_pace_hr_samples(
            df,
            moving_mask=pd.Series(True, index=df.index),
            config=config,
        )

        unstable = np.flatnonzero(~prepared["transition_stable"].to_numpy(dtype=bool))
        unstable_after_change = unstable[unstable >= 40]
        self.assertGreaterEqual(unstable_after_change.size, 10)
        self.assertEqual(int(unstable_after_change[0]), 40)
        self.assertFalse(bool(prepared.loc[40, "valid"]))
        self.assertFalse(bool(prepared.loc[unstable_after_change[0], "valid"]))

    def test_bin_builder_uses_cleaned_samples(self) -> None:
        from progress.indexer import _build_pace_hr_bins

        heart_rates = [140.0] * 720
        heart_rates[650] = 220.0
        df = _activity_frame([300.0] * 720, heart_rates=heart_rates)
        bins = _build_pace_hr_bins(
            df=df,
            moving_mask=pd.Series(True, index=df.index),
            activity_id="activity",
            activity_type="real",
            start_ts_utc="2026-07-15T08:00:00Z",
        )

        self.assertEqual(len(bins), 1)
        self.assertEqual(bins[0].pace_bin_s_per_km, 300.0)
        self.assertEqual(bins[0].hr_q50_w_bpm, 140.0)
        self.assertGreaterEqual(bins[0].time_s_bin, 60.0)
        self.assertLess(bins[0].time_s_bin, 120.0)


if __name__ == "__main__":
    unittest.main()
