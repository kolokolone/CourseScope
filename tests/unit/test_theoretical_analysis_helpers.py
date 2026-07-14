from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


def synthetic_course(step_m: float = 10.0, noise_m: float = 0.0) -> pd.DataFrame:
    distance = np.arange(100.0, 10_100.0 + step_m, step_m)
    elevation = 120.0 + 35.0 * np.sin((distance - 100.0) / 850.0)
    if noise_m:
        elevation = elevation + np.random.default_rng(42).normal(0.0, noise_m, len(distance))
    return pd.DataFrame({"distance_m": distance, "elevation": elevation, "lat": np.nan, "lon": np.nan})


class TestRacePlanningPipeline(unittest.TestCase):
    def test_profile_normalizes_distance_and_is_sampling_density_resistant(self) -> None:
        from core.course_profile import prepare_course_profile

        dense = prepare_course_profile(synthetic_course(5.0)).dataframe
        sparse = prepare_course_profile(synthetic_course(10.0)).dataframe
        self.assertEqual(float(dense["distance_m"].iloc[0]), 0.0)
        self.assertEqual(float(sparse["distance_m"].iloc[0]), 0.0)
        self.assertAlmostEqual(float(dense["distance_km"].iloc[-1]), 10.0, places=6)
        self.assertAlmostEqual(float(np.quantile(dense["grade_robust_pct"], 0.95)), float(np.quantile(sparse["grade_robust_pct"], 0.95)), delta=0.15)

    def test_missing_elevation_and_controlled_noise_are_robust(self) -> None:
        from core.course_profile import prepare_course_profile

        clean = synthetic_course()
        noisy = synthetic_course(noise_m=1.0)
        noisy.loc[100:130, "elevation"] = np.nan
        clean_profile = prepare_course_profile(clean)
        noisy_profile = prepare_course_profile(noisy)
        self.assertFalse(noisy_profile.dataframe["elevation_m"].isna().any())
        self.assertGreater(noisy_profile.quality["interpolated_elevation_ratio"], 0.0)
        clean_grade = float(np.quantile(np.abs(clean_profile.dataframe["grade_robust_pct"]), 0.9))
        noisy_grade = float(np.quantile(np.abs(noisy_profile.dataframe["grade_robust_pct"]), 0.9))
        self.assertAlmostEqual(noisy_grade, clean_grade, delta=1.2)

    def test_minetti_and_exact_time_target(self) -> None:
        from services.race_planning_service import calculate_race_plan_preview, minetti_cost_ratio

        ratios = minetti_cost_ratio(np.array([-8.0, 0.0, 8.0]))
        self.assertLess(float(ratios[0]), float(ratios[1]))
        self.assertAlmostEqual(float(ratios[1]), 1.0, places=6)
        self.assertGreater(float(ratios[2]), float(ratios[1]))
        extended_ratios = minetti_cost_ratio(np.array([-15.0, -10.0, -5.0, 15.0, 20.0, 25.0]))
        self.assertEqual(len(set(np.round(extended_ratios[:3], 6))), 3)
        self.assertEqual(len(set(np.round(extended_ratios[3:], 6))), 3)
        preview = calculate_race_plan_preview(synthetic_course(), scenario={"name": "chrono", "objective_type": "time", "target_value": 3600.0, "slope_model": "minetti"})
        self.assertAlmostEqual(float(preview["totals"]["running_time_s"]), 3600.0, delta=1.0)

    def test_stops_shift_all_following_passages_exactly(self) -> None:
        from services.race_planning_service import calculate_race_plan_preview

        base = calculate_race_plan_preview(synthetic_course(), scenario={"name": "base", "objective_type": "pace", "target_value": 360.0, "slope_model": "minetti"})
        stopped = calculate_race_plan_preview(synthetic_course(), scenario={"name": "stop", "objective_type": "pace", "target_value": 360.0, "slope_model": "minetti"}, stops=[{"distance_km": 5.0, "stop_type": "water", "duration_s": 120.0}])
        for before, after in zip(base["passages"], stopped["passages"]):
            expected = 120.0 if float(after["distance_km"]) >= 5.0 else 0.0
            self.assertAlmostEqual(float(after["elapsed_time_s"]) - float(before["elapsed_time_s"]), expected, places=6)
        times = [float(item["elapsed_time_s"]) for item in stopped["passages"]]
        self.assertTrue(all(b >= a for a, b in zip(times, times[1:])))

    def test_histograms_conserve_time_and_apply_display_rules(self) -> None:
        from services.race_planning_service import calculate_race_plan_preview

        preview = calculate_race_plan_preview(synthetic_course(), scenario={"name": "bins", "objective_type": "pace", "target_value": 330.0, "slope_model": "minetti"})
        total = float(preview["totals"]["running_time_s"])
        for name in ("pace", "grade"):
            histogram = preview["histograms"][name]
            self.assertAlmostEqual(sum(float(row["time_s"]) for row in histogram["complete_classes"]), total, places=6)
            self.assertTrue(all(float(row["time_s"]) >= 90.0 for row in histogram["display_classes"]))
        max_pace = float(preview["totals"]["base_pace_s_per_km"]) * 1.75
        self.assertTrue(all(float(row["pace_bin_floor_s_per_km"]) <= max_pace for row in preview["histograms"]["pace"]["display_classes"]))
        grade_rows = preview["histograms"]["grade"]["complete_classes"]
        self.assertTrue(all(-20.0 <= float(row["grade_bin_center_pct"]) <= 20.0 for row in grade_rows))


if __name__ == "__main__":
    unittest.main()
