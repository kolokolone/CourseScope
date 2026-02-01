from __future__ import annotations

import math
import numpy as np
import pandas as pd

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


def test_compute_splits_basic() -> None:
    """Test compute_splits function with basic data."""
    from core.real_run_analysis import compute_splits

    # Create basic test data - ensure exactly 3km distance
    df = pd.DataFrame({
        "distance_m": [0, 333, 667, 1000, 1333, 1667, 2000, 2333, 2667, 3000],
        "elapsed_time_s": [0, 60, 120, 180, 240, 300, 360, 420, 480, 540],
        "elevation": [100, 103, 106, 110, 108, 112, 115, 117, 119, 118],
    })

    # Test with 1km splits
    splits = compute_splits(df, split_distance_km=1.0)
    
    expected_columns = ["split_index", "distance_index", "distance_km", "time_s", "pace_s_per_km", "elevation_gain_m", "avg_hr_bpm", "elev_delta_m"]
    assert list(splits.columns) == expected_columns
    
    # Should have 3 splits (0-1km, 1-2km, 2-3km)
    assert len(splits) == 3
    
    # Verify basic split data
    assert all(splits["split_index"] == [1, 2, 3])
    assert all(abs(splits["distance_km"] - 1.0) < 0.01)  # Each split ~1km
    assert all(abs(splits["time_s"] - 180.0) < 1.0)  # Each split ~3 minutes
    assert all(abs(splits["pace_s_per_km"] - 180.0) < 1.0)  # ~3 min/km pace
    
    # Verify avg_hr_bpm is None when no heart_rate data
    assert all(splits["avg_hr_bpm"].isna())


def test_compute_splits_with_heart_rate() -> None:
    """Test compute_splits function with heart rate data."""
    from core.real_run_analysis import compute_splits

    # Create test data with heart rate
    df = pd.DataFrame({
        "distance_m": [0, 500, 1000, 1500],
        "elapsed_time_s": [0, 300, 600, 900],
        "elevation": [100, 105, 110, 108],
        "heart_rate": [140, 145, 150, 148],
    })

    splits = compute_splits(df, split_distance_km=1.0)
    
    # Verify heart rate calculation
    # Split 1: HR [140, 145, 150] -> avg = 145
    # Split 2: HR [150, 148] -> avg = 149
    expected_hr = [145.0, 149.0]
    assert all(abs(splits["avg_hr_bpm"] - expected_hr) < 1.0)


def test_compute_splits_with_negative_elevation() -> None:
    """Test compute_splits with negative elevation changes."""
    from core.real_run_analysis import compute_splits

    df = pd.DataFrame({
        "distance_m": [0, 500, 1000, 1500, 2000],
        "elapsed_time_s": [0, 300, 600, 900, 1200],
        "elevation": [120, 110, 105, 108, 100],  # Net descent
    })

    splits = compute_splits(df, split_distance_km=1.0)
    
    # Verify elevation gain (only positive changes)
    # Split 1: 120->105 (no gain) = 0
    # Split 2: 105->108 (gain 3) = 3
    expected_elevation_gain = [0.0, 3.0, 0.0]
    assert all(abs(splits["elevation_gain_m"] - expected_elevation_gain) < 0.5)
    
    # Verify elevation delta (total change, can be negative)
    # Split 1: 120->105 = -15
    # Split 2: 105->108 = +3
    # Split 3: 108->100 = -8
    expected_elev_delta = [-15.0, 3.0, -8.0]
    assert all(abs(splits["elev_delta_m"] - expected_elev_delta) < 0.5)


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
        "distance_m": [0, 500, 1000, 1500],
        "elapsed_time_s": [0, 300, 600, 900],
        "elevation": [100, 105, 110, 108],
        "heart_rate": [140, np.nan, 150, 148],  # One missing value
    })

    splits = compute_splits(df, split_distance_km=1.0)
    
    # Should handle missing heart rate data properly
    assert splits["avg_hr_bpm"].notna().all()  # Should still compute avg from available data
    expected_hr = [145.0, 149.0]  # Same as before, ignoring NaN
    assert all(abs(splits["avg_hr_bpm"] - expected_hr) < 1.0)


def test_compute_splits_missing_elevation() -> None:
    """Test compute_splits when elevation data is missing."""
    from core.real_run_analysis import compute_splits

    df = pd.DataFrame({
        "distance_m": [0, 500, 1000, 1500],
        "elapsed_time_s": [0, 300, 600, 900],
        # No elevation column
    })

    splits = compute_splits(df, split_distance_km=1.0)
    
    # Should handle missing elevation gracefully
    assert all(splits["elevation_gain_m"] == 0.0)
    assert all(splits["elev_delta_m"] == 0.0)