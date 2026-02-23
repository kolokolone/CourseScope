from __future__ import annotations

import json
import time

import pandas as pd

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


def _make_df(n: int) -> pd.DataFrame:
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


def _wait_runner_done(timeout_s: float = 10.0):
    from backend.progress.indexation_runner import get_indexation_state

    started = time.time()
    while True:
        state = get_indexation_state()
        if not state.running:
            return state
        if time.time() - started > timeout_s:
            raise AssertionError("indexation runner timeout")
        time.sleep(0.05)


def _write_activity_fs(activities_dir, activity_id: str, *, file_hash: str, with_fit: bool = False):
    activity_dir = activities_dir / activity_id
    activity_dir.mkdir(parents=True, exist_ok=True)
    df = _make_df(120)
    parquet_path = activity_dir / "df.parquet"
    df.to_parquet(parquet_path, engine="pyarrow")

    meta = {
        "id": activity_id,
        "filename": "original.fit" if with_fit else "original.gpx",
        "name": f"Activity {activity_id}",
        "activity_type": "real",
        "created_at": "2026-02-03T10:00:00Z",
        "started_at": "2026-02-03T10:00:00Z",
        "file_hash": file_hash,
    }
    (activity_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=True, indent=2), encoding="utf-8")
    if with_fit:
        (activity_dir / "original.fit").write_bytes(b"fit")
    else:
        (activity_dir / "original.gpx").write_text("x", encoding="utf-8")
    return activity_dir, parquet_path, meta


def _add_progress_row(session, *, activity_id: str, fingerprint: str, metrics_version: int, vo2max: float | None = 50.0):
    from backend.db.models import ProgressActivityIndex

    session.add(
        ProgressActivityIndex(
            activity_id=activity_id,
            activity_type="real",
            start_ts_utc="2026-02-03T10:00:00Z",
            local_date="2026-02-03",
            tz=None,
            fingerprint=fingerprint,
            metrics_version=int(metrics_version),
            indexed_at_ts="2026-02-03T10:00:00Z",
            distance_m=5000.0,
            moving_time_s=1500.0,
            elapsed_time_s=1600.0,
            elevation_gain_m=50.0,
            avg_pace_s_per_km=300.0,
            best_pace_s_per_km=250.0,
            pace_threshold_s_per_km=310.0,
            avg_hr_bpm=140.0,
            max_hr_bpm=175.0,
            trimp=40.0,
            training_load_method="edwards",
            decoupling_pct=4.0,
            cardiac_drift_pct=4.0,
            stability_cv=0.08,
            stability_iqr_ratio=0.12,
            aerobic_efficiency_m_s_per_bpm=0.09,
            vo2max=vo2max,
            has_hr=1,
            has_power=0,
            has_cadence=0,
            data_points=1234,
        )
    )


def test_fast_adds_missing_db_row_from_fs(tmp_path, monkeypatch):
    monkeypatch.setenv("COURSESCOPE_DATA_DIR", str(tmp_path))

    from backend.config import get_activities_dir
    from backend.db.models import Activity
    from backend.db.session import init_db, make_engine, make_session_factory
    from backend.progress.indexation_runner import start_fast_indexation_in_background

    _wait_runner_done()
    engine = make_engine()
    init_db(engine)
    factory = make_session_factory(engine)

    activities_dir = get_activities_dir().resolve()
    activity_id = "00000000-0000-0000-0000-0000000001f1"
    _write_activity_fs(activities_dir, activity_id, file_hash="a" * 64)

    start_fast_indexation_in_background(factory, reason="test")
    state = _wait_runner_done()

    assert state.last_result is not None
    assert state.last_result.added == 1

    session = factory()
    try:
        row = session.get(Activity, activity_id)
        assert row is not None
    finally:
        session.close()


def test_fast_deletes_stale_db_row_absent_on_disk(tmp_path, monkeypatch):
    monkeypatch.setenv("COURSESCOPE_DATA_DIR", str(tmp_path))

    from backend.db.models import Activity
    from backend.db.session import init_db, make_engine, make_session_factory
    from backend.progress.indexation_runner import start_fast_indexation_in_background

    _wait_runner_done()
    engine = make_engine()
    init_db(engine)
    factory = make_session_factory(engine)

    activity_id = "00000000-0000-0000-0000-0000000001f2"
    session = factory()
    try:
        session.add(
            Activity(
                id=activity_id,
                name="Stale",
                activity_type="real",
                started_at_utc="2026-02-03T10:00:00Z",
                created_at_utc="2026-02-03T10:00:00Z",
                file_hash_sha256="b" * 64,
                original_path=str(tmp_path / "missing.fit"),
                parquet_path=str(tmp_path / "missing.parquet"),
            )
        )
        session.commit()
    finally:
        session.close()

    start_fast_indexation_in_background(factory, reason="test")
    state = _wait_runner_done()

    assert state.last_result is not None
    assert state.last_result.deleted >= 1

    session = factory()
    try:
        assert session.get(Activity, activity_id) is None
    finally:
        session.close()


def test_slow_reindexes_when_fingerprint_changes(tmp_path, monkeypatch):
    monkeypatch.setenv("COURSESCOPE_DATA_DIR", str(tmp_path))

    from backend.config import get_activities_dir
    from backend.db.models import Activity, ProgressActivityIndex
    from backend.db.session import init_db, make_engine, make_session_factory
    from backend.progress.indexation_runner import start_slow_indexation_in_background
    from backend.progress.indexer import METRICS_VERSION, build_fingerprint

    _wait_runner_done()
    engine = make_engine()
    init_db(engine)
    factory = make_session_factory(engine)

    activities_dir = get_activities_dir().resolve()
    activity_id = "00000000-0000-0000-0000-0000000001f3"
    _, parquet_path, meta = _write_activity_fs(activities_dir, activity_id, file_hash="c" * 64)
    current_fp = build_fingerprint(meta, parquet_path)

    session = factory()
    try:
        session.add(
            Activity(
                id=activity_id,
                name="Fingerprint",
                activity_type="real",
                started_at_utc="2026-02-03T10:00:00Z",
                created_at_utc="2026-02-03T10:00:00Z",
                file_hash_sha256="c" * 64,
                original_path=str((activities_dir / activity_id / "original.gpx").resolve()),
                parquet_path=str(parquet_path.resolve()),
            )
        )
        _add_progress_row(session, activity_id=activity_id, fingerprint="outdated", metrics_version=int(METRICS_VERSION), vo2max=52.0)
        session.commit()
    finally:
        session.close()

    start_slow_indexation_in_background(factory, reason="test", strategy="incremental")
    state = _wait_runner_done()

    assert state.last_result is not None
    assert state.last_result.indexed == 1

    session = factory()
    try:
        row = session.get(ProgressActivityIndex, activity_id)
        assert row is not None
        assert row.fingerprint == current_fp
        assert row.slow_indexation_date is not None
    finally:
        session.close()


def test_slow_reindexes_when_metrics_version_changes(tmp_path, monkeypatch):
    monkeypatch.setenv("COURSESCOPE_DATA_DIR", str(tmp_path))

    from backend.config import get_activities_dir
    from backend.db.models import Activity
    from backend.db.session import init_db, make_engine, make_session_factory
    from backend.progress.indexation_runner import start_slow_indexation_in_background
    from backend.progress.indexer import METRICS_VERSION, build_fingerprint

    _wait_runner_done()
    engine = make_engine()
    init_db(engine)
    factory = make_session_factory(engine)

    activities_dir = get_activities_dir().resolve()
    activity_id = "00000000-0000-0000-0000-0000000001f4"
    _, parquet_path, meta = _write_activity_fs(activities_dir, activity_id, file_hash="d" * 64)
    fp = build_fingerprint(meta, parquet_path)

    session = factory()
    try:
        session.add(
            Activity(
                id=activity_id,
                name="Metrics",
                activity_type="real",
                started_at_utc="2026-02-03T10:00:00Z",
                created_at_utc="2026-02-03T10:00:00Z",
                file_hash_sha256="d" * 64,
                original_path=str((activities_dir / activity_id / "original.gpx").resolve()),
                parquet_path=str(parquet_path.resolve()),
            )
        )
        _add_progress_row(session, activity_id=activity_id, fingerprint=fp, metrics_version=int(METRICS_VERSION) - 1, vo2max=52.0)
        session.commit()
    finally:
        session.close()

    start_slow_indexation_in_background(factory, reason="test", strategy="incremental")
    state = _wait_runner_done()

    assert state.last_result is not None
    assert state.last_result.indexed == 1


def test_slow_ignores_activity_already_up_to_date(tmp_path, monkeypatch):
    monkeypatch.setenv("COURSESCOPE_DATA_DIR", str(tmp_path))

    from backend.config import get_activities_dir
    from backend.db.models import Activity
    from backend.db.session import init_db, make_engine, make_session_factory
    from backend.progress.indexation_runner import start_slow_indexation_in_background
    from backend.progress.indexer import METRICS_VERSION, build_fingerprint

    _wait_runner_done()
    engine = make_engine()
    init_db(engine)
    factory = make_session_factory(engine)

    activities_dir = get_activities_dir().resolve()
    activity_id = "00000000-0000-0000-0000-0000000001f5"
    _, parquet_path, meta = _write_activity_fs(activities_dir, activity_id, file_hash="e" * 64)
    fp = build_fingerprint(meta, parquet_path)

    session = factory()
    try:
        session.add(
            Activity(
                id=activity_id,
                name="UpToDate",
                activity_type="real",
                started_at_utc="2026-02-03T10:00:00Z",
                created_at_utc="2026-02-03T10:00:00Z",
                file_hash_sha256="e" * 64,
                original_path=str((activities_dir / activity_id / "original.gpx").resolve()),
                parquet_path=str(parquet_path.resolve()),
            )
        )
        _add_progress_row(session, activity_id=activity_id, fingerprint=fp, metrics_version=int(METRICS_VERSION), vo2max=52.0)
        session.commit()
    finally:
        session.close()

    start_slow_indexation_in_background(factory, reason="test", strategy="incremental")
    state = _wait_runner_done()

    assert state.last_result is not None
    assert state.last_result.indexed == 0
    assert state.last_result.up_to_date == 1
