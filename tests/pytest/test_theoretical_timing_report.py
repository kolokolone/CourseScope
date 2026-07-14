from __future__ import annotations

import numpy as np
import pandas as pd

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


def test_course_profile_deduplicates_distances_and_exposes_explicit_units() -> None:
    from core.course_profile import prepare_course_profile

    df = pd.DataFrame({"distance_m": [50.0, 60.0, 60.0, 75.0], "elevation": [0.0, 1.0, 1.0, 2.0], "lat": np.nan, "lon": np.nan})
    profile = prepare_course_profile(df)
    assert profile.dataframe["distance_m"].iloc[0] == 0.0
    assert profile.dataframe["distance_m"].is_monotonic_increasing
    assert profile.quality["distance_unit"] == "km"
    assert profile.quality["internal_distance_unit"] == "m"
