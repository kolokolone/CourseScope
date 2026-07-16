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


def linear_course(grade_pct: float, step_m: float = 10.0, length_m: float = 2_000.0) -> pd.DataFrame:
    distance = np.arange(100.0, 100.0 + length_m + step_m, step_m)
    elevation = 300.0 + (distance - distance[0]) * grade_pct / 100.0
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

    def test_fixed_distance_grade_is_correct_and_stable_at_route_edges(self) -> None:
        from core.course_profile import prepare_course_profile

        for expected_grade in (-18.0, -7.5, 8.0):
            profile = prepare_course_profile(linear_course(expected_grade)).dataframe
            grade = profile["grade_robust_pct"].to_numpy(dtype=float)
            self.assertTrue(np.allclose(grade, expected_grade, atol=0.05))
            expected_elevation = 300.0 + profile["distance_m"].to_numpy(dtype=float) * expected_grade / 100.0
            self.assertTrue(np.allclose(profile["elevation_m"], expected_elevation, atol=0.05))

    def test_isolated_altitude_spike_does_not_create_extreme_robust_grades(self) -> None:
        from core.course_profile import prepare_course_profile

        course = linear_course(-6.0)
        course.loc[len(course) // 2, "elevation"] += 80.0
        prepared = prepare_course_profile(course)
        robust = prepared.dataframe["grade_robust_pct"].to_numpy(dtype=float)
        self.assertLess(float(np.max(np.abs(robust + 6.0))), 1.0)
        self.assertGreater(float(prepared.quality["corrected_elevation_ratio"]), 0.0)

    def test_minetti_and_exact_time_target(self) -> None:
        from services.race_planning_service import (
            calculate_race_plan_preview,
            minetti_cost_ratio,
            minetti_pace_ratio,
        )

        ratios = minetti_cost_ratio(np.array([-8.0, 0.0, 8.0]))
        self.assertLess(float(ratios[0]), float(ratios[1]))
        self.assertAlmostEqual(float(ratios[1]), 1.0, places=6)
        self.assertGreater(float(ratios[2]), float(ratios[1]))
        extended_ratios = minetti_cost_ratio(np.array([-15.0, -10.0, -5.0, 15.0, 20.0, 25.0]))
        self.assertEqual(len(set(np.round(extended_ratios[:3], 6))), 3)
        self.assertEqual(len(set(np.round(extended_ratios[3:], 6))), 3)
        expected_grades = np.array([0.0, -3.0, -5.0, -8.0, -10.0, -12.0, -15.0, -18.0, -25.0, -30.0])
        expected_ratios = np.array([1.00, 0.97, 0.94, 0.90, 0.88, 0.90, 0.95, 1.00, 1.10, 1.20])
        self.assertTrue(np.allclose(minetti_pace_ratio(expected_grades), expected_ratios, atol=1e-12))
        uphill = minetti_pace_ratio(np.array([5.0, 10.0, 20.0]))
        self.assertTrue(np.allclose(uphill, minetti_cost_ratio(np.array([5.0, 10.0, 20.0])) ** 0.80))
        preview = calculate_race_plan_preview(synthetic_course(), scenario={"name": "chrono", "objective_type": "time", "target_value": 3600.0, "slope_model": "minetti"})
        self.assertAlmostEqual(float(preview["totals"]["running_time_s"]), 3600.0, delta=1.0)

    def test_downhill_pace_is_progressive_and_metric_smoothing_preserves_time(self) -> None:
        from services.race_planning_service import (
            _display_indices,
            _smooth_pace_by_distance,
            calculate_race_plan_preview,
        )

        preview = calculate_race_plan_preview(
            linear_course(-18.0),
            scenario={"name": "descente", "objective_type": "pace", "target_value": 300.0, "slope_model": "minetti"},
        )
        paces = np.array([float(point["pace_s_per_km"]) for point in preview["profile"]])
        self.assertAlmostEqual(float(np.mean(paces)), 300.0, delta=0.5)

        raw = np.array([300.0, 300.0, 150.0, 300.0, 300.0])
        distances = np.full(len(raw), 0.01)
        smoothed = _smooth_pace_by_distance(raw, distances, window_m=40.0)
        self.assertLess(float(np.ptp(smoothed)), float(np.ptp(raw)))
        self.assertAlmostEqual(float(np.sum(smoothed * distances)), float(np.sum(raw * distances)), places=9)

        dense_distances = np.full(200, 0.005)
        sparse_distances = np.full(100, 0.01)
        dense_raw = np.where(np.arange(200) < 100, 240.0, 420.0)
        sparse_raw = np.where(np.arange(100) < 50, 240.0, 420.0)
        dense_smoothed = _smooth_pace_by_distance(dense_raw, dense_distances, window_m=100.0)
        sparse_smoothed = _smooth_pace_by_distance(sparse_raw, sparse_distances, window_m=100.0)
        dense_midpoints_m = np.cumsum(dense_distances * 1000.0) - dense_distances * 500.0
        sparse_midpoints_m = np.cumsum(sparse_distances * 1000.0) - sparse_distances * 500.0
        dense_at_sparse_center = np.interp(sparse_midpoints_m[50], dense_midpoints_m, dense_smoothed)
        self.assertAlmostEqual(float(dense_at_sparse_center), float(sparse_smoothed[50]), delta=0.1)
        self.assertAlmostEqual(float(np.sum(dense_smoothed * dense_distances)), float(np.sum(dense_raw * dense_distances)), places=9)
        self.assertAlmostEqual(float(np.sum(sparse_smoothed * sparse_distances)), float(np.sum(sparse_raw * sparse_distances)), places=9)

        size = 5_000
        profile = pd.DataFrame({
            "elevation_m": np.zeros(size),
            "grade_robust_pct": np.zeros(size),
        })
        display_pace = np.full(size, 300.0)
        display_pace[1_234] = 180.0
        display_pace[4_321] = 900.0
        selected = set(_display_indices(profile, display_pace, max_points=200).tolist())
        self.assertIn(1_234, selected)
        self.assertIn(4_321, selected)

    def test_stops_shift_all_following_passages_exactly(self) -> None:
        from services.race_planning_service import calculate_race_plan_preview

        base = calculate_race_plan_preview(synthetic_course(), scenario={"name": "base", "objective_type": "pace", "target_value": 360.0, "slope_model": "minetti"})
        stopped = calculate_race_plan_preview(synthetic_course(), scenario={"name": "stop", "objective_type": "pace", "target_value": 360.0, "slope_model": "minetti"}, stops=[{"distance_km": 5.0, "stop_type": "water", "duration_s": 120.0}])
        for before, after in zip(base["passages"], stopped["passages"]):
            expected = 120.0 if float(after["distance_km"]) >= 5.0 else 0.0
            self.assertAlmostEqual(float(after["elapsed_time_s"]) - float(before["elapsed_time_s"]), expected, places=6)
        times = [float(item["elapsed_time_s"]) for item in stopped["passages"]]
        self.assertTrue(all(b >= a for a, b in zip(times, times[1:])))

    def test_timeline_preserves_same_distance_stops_and_full_profile_elevation(self) -> None:
        from services.race_planning_service import calculate_race_plan_preview

        preview = calculate_race_plan_preview(
            linear_course(5.0),
            scenario={"name": "timeline", "objective_type": "pace", "target_value": 360.0, "slope_model": "minetti"},
            stops=[
                {"id": "water", "label": "  Source  ", "distance_km": 1.0, "stop_type": "water", "duration_s": 60.0, "sort_order": 0},
                {"id": "food", "label": None, "distance_km": 1.0, "stop_type": "nutrition", "duration_s": 90.0, "sort_order": 1},
            ],
        )

        timeline = preview["timeline_passages"]
        self.assertEqual([item["kind"] for item in timeline], ["start", "stop", "stop", "arrival"])
        self.assertEqual(timeline[1]["label"], "Source")
        self.assertEqual(timeline[2]["label"], "Alimentation")
        self.assertEqual(float(timeline[2]["distance_from_previous_km"]), 0.0)
        self.assertEqual(float(timeline[2]["elevation_gain_from_previous_m"]), 0.0)
        self.assertEqual(float(timeline[2]["elevation_loss_from_previous_m"]), 0.0)
        self.assertEqual(float(timeline[2]["arrival_elapsed_time_s"]), float(timeline[1]["departure_elapsed_time_s"]))
        self.assertAlmostEqual(float(timeline[-1]["cumulative_elevation_gain_m"]), float(preview["totals"]["elevation_gain_m"]), places=9)
        self.assertAlmostEqual(float(timeline[-1]["cumulative_elevation_loss_m"]), float(preview["totals"]["elevation_loss_m"]), places=9)
        self.assertIsNone(timeline[1]["lat"])
        self.assertIsNone(timeline[1]["lon"])

        renamed_hash = calculate_race_plan_preview(
            linear_course(5.0),
            scenario={"name": "timeline", "objective_type": "pace", "target_value": 360.0, "slope_model": "minetti"},
            stops=[{"id": "water", "label": "Autre nom", "distance_km": 1.0, "stop_type": "water", "duration_s": 60.0}],
        )["scenario_hash"]
        self.assertNotEqual(preview["scenario_hash"], renamed_hash)

    def test_histograms_conserve_time_and_apply_display_rules(self) -> None:
        from services.race_planning_service import calculate_race_plan_preview

        preview = calculate_race_plan_preview(synthetic_course(), scenario={"name": "bins", "objective_type": "pace", "target_value": 330.0, "slope_model": "minetti"})
        total = float(preview["totals"]["running_time_s"])
        for name in ("pace", "grade"):
            histogram = preview["histograms"][name]
            self.assertAlmostEqual(sum(float(row["time_s"]) for row in histogram["complete_classes"]), total, places=6)
        self.assertTrue(all(float(row["time_s"]) >= 90.0 for row in preview["histograms"]["pace"]["display_classes"]))
        self.assertEqual(preview["histograms"]["grade"]["display_classes"], preview["histograms"]["grade"]["complete_classes"])
        self.assertEqual(preview["histograms"]["grade"]["hidden_time_s"], 0.0)
        max_pace = float(preview["totals"]["base_pace_s_per_km"]) * 1.75
        self.assertTrue(all(float(row["pace_bin_floor_s_per_km"]) <= max_pace for row in preview["histograms"]["pace"]["display_classes"]))
        grade_rows = preview["histograms"]["grade"]["complete_classes"]
        self.assertTrue(all(-20.0 <= float(row["grade_bin_center_pct"]) <= 20.0 for row in grade_rows))


if __name__ == "__main__":
    unittest.main()
