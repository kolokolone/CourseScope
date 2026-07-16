from types import SimpleNamespace

import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


def test_hr_zone_boundaries_use_the_configured_hr_max() -> None:
    from core.metrics import compute_garmin_like_stats

    frame = pd.DataFrame(
        {
            "delta_time_s": [1.0] * 6,
            "delta_distance_m": [2.0] * 6,
            "distance_m": np.arange(6, dtype=float) * 2.0,
            "elapsed_time_s": np.arange(1, 7, dtype=float),
            "heart_rate": [99.0, 100.0, 120.0, 140.0, 160.0, 180.0],
        }
    )

    result = compute_garmin_like_stats(
        frame,
        moving_mask=pd.Series([True] * len(frame)),
        hr_max=200.0,
    )
    zones = result["heart_rate"]["zones"].set_index("zone")

    assert result["heart_rate"]["hr_max_used"] == 200.0
    assert zones["time_s"].to_dict() == {"Z1": 1.0, "Z2": 1.0, "Z3": 1.0, "Z4": 1.0, "Z5": 1.0}


def test_detected_hr_snapshot_is_global_for_the_run(tmp_path) -> None:
    from db.models import Base
    from progress.indexation_runner import _resolve_hr_zone_snapshot

    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    activities = []
    for activity_id, values in (("a1", [140.0, 170.0]), ("a2", [150.0, 192.0])):
        directory = tmp_path / activity_id
        directory.mkdir()
        parquet_path = directory / "df.parquet"
        pd.DataFrame({"heart_rate": values}).to_parquet(parquet_path, engine="pyarrow")
        activities.append(SimpleNamespace(id=activity_id, parquet_path=str(parquet_path)))

    with Session(engine) as session:
        value, source = _resolve_hr_zone_snapshot(session, activities, activities_dir=tmp_path)

    assert value == 192.0
    assert source == "detected"
