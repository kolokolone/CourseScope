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
        }
        defaults.update(overrides)
        return replace(DEFAULT_PACE_HR_PREPROCESSING_CONFIG, **defaults)

    def test_keeps_a_continuous_pace_window_across_zero_distance_points(self) -> None:
        from core.pace_hr import prepare_pace_hr_samples

        df = _activity_frame([300.0] * 25)
        df.loc[8:9, ["delta_distance_m", "speed_m_s", "pace_s_per_km"]] = [
            0.0,
            0.0,
            math.nan,
        ]

        prepared = prepare_pace_hr_samples(df, config=self._config())

        self.assertTrue(math.isfinite(float(prepared.loc[10, "pace_smoothed_s_per_km"])))
        self.assertTrue(bool(prepared.loc[10, "valid"]))

    def test_keeps_long_recording_intervals_in_the_rolling_pace(self) -> None:
        from core.pace_hr import prepare_pace_hr_samples

        dt = [1.0] * 20
        dt[10] = 20.0
        df = _activity_frame([300.0] * 20, delta_times_s=dt)

        prepared = prepare_pace_hr_samples(df, config=self._config())

        self.assertEqual(float(prepared.loc[10, "delta_time_s"]), 20.0)
        self.assertAlmostEqual(float(prepared.loc[10, "pace_smoothed_s_per_km"]), 300.0)

    def test_smooths_noisy_pace_using_time_over_distance(self) -> None:
        from core.pace_hr import prepare_pace_hr_samples

        df = _activity_frame([280.0, 320.0] * 20)
        prepared = prepare_pace_hr_samples(
            df,
            config=self._config(pace_window_s=6.0),
        )

        values = prepared["pace_smoothed_s_per_km"].dropna().to_numpy(dtype=float)
        self.assertGreater(values.size, 10)
        self.assertLess(float(np.nanstd(values)), 1.0)
        self.assertAlmostEqual(float(np.nanmedian(values)), 298.7, delta=1.0)

    def test_hampel_filter_rejects_only_the_isolated_hr_spike(self) -> None:
        from core.pace_hr import prepare_pace_hr_samples

        heart_rates = [140.0] * 30
        heart_rates[15] = 220.0
        df = _activity_frame([300.0] * 30, heart_rates=heart_rates)
        prepared = prepare_pace_hr_samples(df, config=self._config())

        self.assertAlmostEqual(float(prepared.loc[14, "heart_rate_clean_bpm"]), 140.0)
        self.assertTrue(math.isnan(float(prepared.loc[15, "heart_rate_clean_bpm"])))
        self.assertAlmostEqual(float(prepared.loc[16, "heart_rate_clean_bpm"]), 140.0)
        self.assertFalse(bool(prepared.loc[15, "valid"]))
        self.assertTrue(bool(prepared.loc[16, "valid"]))

    def test_rejects_heart_rate_outside_physiological_bounds(self) -> None:
        from core.pace_hr import prepare_pace_hr_samples

        heart_rates = [140.0] * 30
        heart_rates[12] = 40.0
        heart_rates[18] = 240.0
        prepared = prepare_pace_hr_samples(
            _activity_frame([300.0] * 30, heart_rates=heart_rates),
            config=self._config(),
        )

        self.assertTrue(math.isnan(float(prepared.loc[12, "heart_rate_clean_bpm"])))
        self.assertTrue(math.isnan(float(prepared.loc[18, "heart_rate_clean_bpm"])))

    def test_excludes_first_ten_seconds_of_positive_distance_time(self) -> None:
        from core.pace_hr import prepare_pace_hr_samples

        df = _activity_frame([300.0] * 25)
        df.loc[5:7, "delta_distance_m"] = 0.0
        prepared = prepare_pace_hr_samples(
            df,
            config=self._config(warmup_moving_time_s=10.0),
        )

        self.assertFalse(bool(prepared.loc[:12, "after_warmup"].any()))
        self.assertTrue(bool(prepared.loc[13, "after_warmup"]))

    def test_does_not_exclude_samples_after_a_pace_transition(self) -> None:
        from core.pace_hr import prepare_pace_hr_samples

        df = _activity_frame(([300.0] * 40) + ([240.0] * 40))
        prepared = prepare_pace_hr_samples(df, config=self._config())

        self.assertTrue(bool(prepared.loc[40, "valid"]))
        self.assertTrue(bool(prepared.loc[41:50, "valid"].all()))

    def test_bin_builder_computes_each_native_resolution_from_samples(self) -> None:
        from core.pace_hr import PACE_HR_BIN_STEPS_S_PER_KM
        from progress.indexer import _build_pace_hr_bins

        heart_rates = [140.0] * 720
        heart_rates[650] = 220.0
        df = _activity_frame([300.0] * 720, heart_rates=heart_rates)
        bins = _build_pace_hr_bins(
            df=df,
            activity_id="activity",
            activity_type="real",
            start_ts_utc="2026-07-15T08:00:00Z",
        )

        self.assertEqual(len(bins), len(PACE_HR_BIN_STEPS_S_PER_KM))
        self.assertEqual(
            {row.bin_step_s_per_km for row in bins},
            set(PACE_HR_BIN_STEPS_S_PER_KM),
        )
        for row in bins:
            self.assertEqual(row.pace_bin_s_per_km, 300.0)
            self.assertEqual(row.hr_q50_w_bpm, 140.0)
            self.assertGreaterEqual(row.time_s_bin, 60.0)
            self.assertLess(row.time_s_bin, 120.0)

    def test_wider_resolution_recomputes_the_weighted_median_from_samples(self) -> None:
        from progress.indexer import _build_pace_hr_bins

        paces = ([310.0] * 660) + ([320.0] * 120)
        heart_rates = ([140.0] * 600) + ([100.0] * 60) + ([200.0] * 120)
        bins = _build_pace_hr_bins(
            df=_activity_frame(paces, heart_rates=heart_rates),
            activity_id="activity",
            activity_type="real",
            start_ts_utc="2026-07-15T08:00:00Z",
            pace_bin_steps_s_per_km=(10, 20),
        )

        ten_second_bins = [row for row in bins if row.bin_step_s_per_km == 10]
        twenty_second_bins = [row for row in bins if row.bin_step_s_per_km == 20]
        self.assertEqual(len(ten_second_bins), 2)
        self.assertEqual(len(twenty_second_bins), 1)

        wider = twenty_second_bins[0]
        mean_of_ten_second_medians = sum(
            float(row.hr_q50_w_bpm) * row.time_s_bin for row in ten_second_bins
        ) / sum(row.time_s_bin for row in ten_second_bins)
        self.assertEqual(wider.hr_q50_w_bpm, 200.0)
        self.assertNotAlmostEqual(wider.hr_q50_w_bpm, mean_of_ten_second_medians)


if __name__ == "__main__":
    unittest.main()
