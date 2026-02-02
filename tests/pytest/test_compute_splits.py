from __future__ import annotations

import math
import numpy as np
import pandas as pd

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


def test_compute_splits_basic() -> None:
    """Test compute_splits function with basic data."""
    from core.real_run_analysis import compute_splits

    # Basic, realistic test data (includes boundaries).
    df = pd.DataFrame(
        {
            "distance_m": [0, 1000, 2000, 3000],
            "elapsed_time_s": [0, 300, 600, 900],
            "elevation": [100, 105, 103, 110],
        }
    )

    # Test with 1km splits
    splits = compute_splits(df, split_distance_km=1.0)
    
    expected_columns = ["split_index", "distance_km", "time_s", "pace_s_per_km", "elevation_gain_m", "avg_hr_bpm", "elev_delta_m"]
    assert list(splits.columns) == expected_columns
    
    # Should have 3 splits (0-1km, 1-2km, 2-3km)
    assert len(splits) == 3
    
    # Verify basic split data
    assert all(splits["split_index"] == [1, 2, 3])

    # No NaN pace in this basic case.
    assert all(np.isfinite(splits["pace_s_per_km"]))
    assert all(abs(splits["pace_s_per_km"] - 300.0) < 1e-6)
    
    # Verify avg_hr_bpm is None when no heart_rate data
    assert all(splits["avg_hr_bpm"].isna())


def test_compute_splits_with_heart_rate() -> None:
    """Test compute_splits function with heart rate data."""
    from core.real_run_analysis import compute_splits

    # Create test data with heart rate - ensure proper boundaries for each split
    df = pd.DataFrame({
        "distance_m": [0, 500, 1000, 1500, 2000],
        "elapsed_time_s": [0, 300, 600, 900, 1200],
        "elevation": [100, 105, 110, 108, 112],
        "heart_rate": [140, 145, 150, 148, 152],
    })

    splits = compute_splits(df, split_distance_km=1.0)
    
    # Verify heart rate calculation
    # Split 1 (0-999m): HR [140, 145, 150] -> avg = 145
    # Split 2 (1000-1999m): HR [150, 148, 152] -> avg = 150
    expected_hr = [145.0, 150.0]
    hr_diff = abs(splits["avg_hr_bpm"] - expected_hr)
    assert all(hr_diff < 1.0)


def test_compute_splits_with_negative_elevation() -> None:
    """Test compute_splits with negative elevation changes."""
    from core.real_run_analysis import compute_splits

    df = pd.DataFrame({
        "distance_m": [0, 500, 1000, 1500, 2000, 2500, 3000],
        "elapsed_time_s": [0, 300, 600, 900, 1200, 1500, 1800],
        "elevation": [120, 110, 105, 108, 100, 95, 98],  # Mixed descent/ascent
    })

    splits = compute_splits(df, split_distance_km=1.0)
    
    # Split 1 (0-1km): [120,110,105] -> gain 0
    # Split 2 (1-2km): [105,108,100] -> gain 3
    # Split 3 (2-3km): [100,95,98] -> gain 3
    expected_elevation_gain = [0.0, 3.0, 3.0]
    assert all(abs(splits["elevation_gain_m"] - expected_elevation_gain) < 0.5)
    
    # Verify elevation delta (total change, can be negative)
    # Split 1: 120->105 = -15
    # Split 2: 105->100 = -5
    # Split 3: 100->98 = -2
    expected_elev_delta = [-15.0, -5.0, -2.0]
    assert all(abs(splits["elev_delta_m"] - expected_elev_delta) < 0.5)
    
    # Verify avg_hr_bpm is None (no heart rate data)
    assert all(splits["avg_hr_bpm"].isna())


def test_compute_splits_empty_dataframe() -> None:
    """Test compute_splits with empty dataframe."""
    from core.real_run_analysis import compute_splits

    df = pd.DataFrame()
    splits = compute_splits(df, split_distance_km=1.0)
    
    expected_columns = ["split_index", "distance_km", "time_s", "pace_s_per_km", "elevation_gain_m", "avg_hr_bpm", "elev_delta_m"]
    assert list(splits.columns) == expected_columns
    assert len(splits) == 0


def test_compute_splits_partial_heart_rate() -> None:
    """Test compute_splits with partial heart rate data (some NaN)."""
    from core.real_run_analysis import compute_splits

    df = pd.DataFrame({
        "distance_m": [0, 500, 1000, 1500, 2000],
        "elapsed_time_s": [0, 300, 600, 900, 1200],
        "elevation": [100, 105, 110, 108, 112],
        "heart_rate": [140, np.nan, 150, 148, np.nan],  # Missing values
    })

    splits = compute_splits(df, split_distance_km=1.0)
    
    # Based on actual split distribution:
    # Split 1: HR [140, np.nan, 150] -> avg of non-NaN = 145
    # Split 2: HR [150, 148, np.nan] -> avg of non-NaN = 149, but last point has no data
    expected_hr = [145.0, 149.0]  # Avg of available samples per split
    hr_diff = abs(splits["avg_hr_bpm"] - expected_hr)
    assert all(hr_diff < 1.0)


def test_compute_splits_missing_elevation() -> None:
    """Test compute_splits when elevation data is missing."""
    from core.real_run_analysis import compute_splits

    df = pd.DataFrame({
        "distance_m": [500, 1500],
        "elapsed_time_s": [300, 600],
        # No elevation column
    })

    splits = compute_splits(df, split_distance_km=1.0)
    
    # Should handle missing elevation gracefully
    assert all(splits["elevation_gain_m"] == 0.0)
    assert all(splits["elev_delta_m"] == 0.0)


def test_compute_splits_excludes_pauses_from_time() -> None:
    """Split time/pace should exclude stopped time (no distance progress)."""
    from core.real_run_analysis import compute_splits

    # Pause between 500m and 500m (time passes, distance does not).
    df = pd.DataFrame(
        {
            "distance_m": [0, 500, 500, 1000],
            "elapsed_time_s": [0, 150, 250, 350],
            "elevation": [100, 100, 100, 100],
        }
    )

    splits = compute_splits(df, split_distance_km=1.0)
    assert len(splits) == 1

    # Moving time is 150s (0->500) + 100s (500->1000) = 250s.
    assert abs(float(splits.iloc[0]["time_s"]) - 250.0) < 1e-6
    assert abs(float(splits.iloc[0]["pace_s_per_km"]) - 250.0) < 1e-6
