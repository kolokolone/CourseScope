from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


def _make_df(n: int) -> pd.DataFrame:
    # Minimal canonical-like DF used by compute_derived_series / compute_basic_stats.
    dt = [0.0] + [1.0] * (n - 1)
    dd = [0.0] + [2.0] * (n - 1)
    dist = []
    elapsed = []
    cur_d = 0.0
    cur_t = 0.0
    for i in range(n):
        cur_d += float(dd[i])
        cur_t += float(dt[i])
        dist.append(cur_d)
        elapsed.append(cur_t)
    speed = [0.0 if dt_i == 0 else dd_i / dt_i for dd_i, dt_i in zip(dd, dt)]
    pace = [300.0 if s <= 0 else 1000.0 / s for s in speed]

    return pd.DataFrame(
        {
            "time": pd.date_range("2026-02-03T10:00:00Z", periods=n, freq="s"),
            "elapsed_time_s": elapsed,
            "delta_time_s": dt,
            "distance_m": dist,
            "delta_distance_m": dd,
            "lat": [48.0] * n,
            "lon": [2.0] * n,
            "elevation": [10.0] * n,
            "speed_m_s": speed,
            "pace_s_per_km": pace,
        }
    )


def test_verify_progress_index_creates_rollup_and_traces_activity(tmp_path, monkeypatch):
    monkeypatch.setenv("COURSESCOPE_DATA_DIR", str(tmp_path))

    from backend.config import get_activities_dir
    from backend.db.session import init_db, make_engine, make_session_factory
    from backend.db.models import Activity, ProgressActivityIndex
    from backend.progress.verify_index import verify_progress_index

    engine = make_engine()
    init_db(engine)
    factory = make_session_factory(engine)

    activities_dir = get_activities_dir().resolve()
    activity_id = "00000000-0000-0000-0000-000000000001"
    activity_dir = activities_dir / activity_id
    activity_dir.mkdir(parents=True, exist_ok=True)

    df = _make_df(120)
    parquet_path = activity_dir / "df.parquet"
    df.to_parquet(parquet_path, engine="pyarrow")

    meta = {
        "id": activity_id,
        "filename": "original.gpx",
        "name": "Verify Test",
        "activity_type": "real",
        "created_at": "2026-02-03T10:00:00Z",
        "started_at": "2026-02-03T10:00:00Z",
        "stats_sidebar": {"distance_km": 0.2},
        "file_hash": "deadbeef" * 8,
    }
    (activity_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=True, indent=2), encoding="utf-8")
    (activity_dir / "original.gpx").write_text("x", encoding="utf-8")

    session = factory()
    try:
        res = verify_progress_index(session, activities_dir=activities_dir, commit_every=1)
    finally:
        session.close()

    assert res.scanned == 1
    assert res.indexed == 1
    assert res.errors == 0

    session = factory()
    try:
        row = session.get(ProgressActivityIndex, activity_id)
        assert row is not None
        act = session.get(Activity, activity_id)
        assert act is not None
        assert act.progress_rollup_path is not None
        assert Path(act.progress_rollup_path).exists()
        assert act.progress_indexed_at_utc is not None
    finally:
        session.close()


def test_verify_progress_index_backfills_vo2max_from_fit_when_row_is_current(tmp_path, monkeypatch):
    monkeypatch.setenv("COURSESCOPE_DATA_DIR", str(tmp_path))

    from backend.config import get_activities_dir
    from backend.db.models import ProgressActivityIndex
    from backend.db.session import init_db, make_engine, make_session_factory
    from backend.progress.verify_index import METRICS_VERSION, build_fingerprint, verify_progress_index
    import backend.progress.verify_index as verify_mod

    engine = make_engine()
    init_db(engine)
    factory = make_session_factory(engine)

    activities_dir = get_activities_dir().resolve()
    activity_id = "00000000-0000-0000-0000-0000000000aa"
    activity_dir = activities_dir / activity_id
    activity_dir.mkdir(parents=True, exist_ok=True)

    df = _make_df(20)
    parquet_path = activity_dir / "df.parquet"
    df.to_parquet(parquet_path, engine="pyarrow")

    meta = {
        "id": activity_id,
        "filename": "original.fit",
        "name": "Verify VO2 Backfill",
        "activity_type": "real",
        "created_at": "2026-02-03T10:00:00Z",
        "started_at": "2026-02-03T10:00:00Z",
        "file_hash": "beadfeed" * 8,
    }
    (activity_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=True, indent=2), encoding="utf-8")
    (activity_dir / "original.fit").write_bytes(b"fit")

    session = factory()
    try:
        session.add(ProgressActivityIndex(
            activity_id=activity_id, activity_type="real", start_ts_utc="2026-02-03T10:00:00Z", local_date="2026-02-03",
            tz=None, fingerprint=build_fingerprint(meta, parquet_path), metrics_version=int(METRICS_VERSION), indexed_at_ts="2026-02-03T10:00:00Z",
            distance_m=5000.0, moving_time_s=1500.0, elapsed_time_s=1600.0, elevation_gain_m=50.0, avg_pace_s_per_km=300.0,
            best_pace_s_per_km=250.0, pace_threshold_s_per_km=310.0, avg_hr_bpm=140.0, max_hr_bpm=175.0, trimp=40.0,
            training_load_method="edwards", decoupling_pct=4.0, cardiac_drift_pct=4.0, stability_cv=0.08, stability_iqr_ratio=0.12,
            aerobic_efficiency_m_s_per_bpm=0.09, vo2max=None, has_hr=1, has_power=0, has_cadence=0, data_points=1234
        ))
        session.commit()
    finally:
        session.close()

    monkeypatch.setattr(verify_mod, "load_fit", lambda _fh: object())
    monkeypatch.setattr(verify_mod, "fit_to_dataframe", lambda _fit: _make_df(20).assign(vo2max=54.2))

    session = factory()
    try:
        res = verify_progress_index(session, activities_dir=activities_dir, commit_every=1)
    finally:
        session.close()

    assert res.indexed == 1

    session = factory()
    try:
        row = session.get(ProgressActivityIndex, activity_id)
        assert row is not None
        assert float(row.vo2max) == 54.2
    finally:
        session.close()
