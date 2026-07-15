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


def test_slow_full_keeps_enriched_parquet_unchanged(tmp_path, monkeypatch):
    monkeypatch.setenv("COURSESCOPE_DATA_DIR", str(tmp_path))

    from backend.config import get_activities_dir
    from backend.db.models import Activity, UserSettings
    from backend.db.session import init_db, make_engine, make_session_factory
    from backend.progress.indexation_runner import start_slow_indexation_in_background

    _wait_runner_done()
    engine = make_engine()
    init_db(engine)
    factory = make_session_factory(engine)

    activities_dir = get_activities_dir().resolve()
    activity_id = "00000000-0000-0000-0000-0000000001f8"
    activity_dir, parquet_path, _ = _write_activity_fs(
        activities_dir, activity_id, file_hash="h" * 64, with_fit=True
    )
    enriched = pd.read_parquet(parquet_path)
    enriched["vo2max"] = 52.4
    enriched.to_parquet(parquet_path, engine="pyarrow")
    parquet_before = parquet_path.read_bytes()
    fit_load_calls = 0

    def _unexpected_fit_load(_stream):
        nonlocal fit_load_calls
        fit_load_calls += 1
        return object()

    monkeypatch.setattr("progress._utils.load_fit", _unexpected_fit_load)
    monkeypatch.setattr("progress._utils._extract_fit_vo2max", lambda _fit: 54.8)

    session = factory()
    try:
        session.add(
            UserSettings(
                id=1,
                vma_kmh=None,
                vo2max_lastest=None,
                hr_max_manual_bpm=None,
                hr_max_source="detected",
                updated_at_utc="2026-02-03T10:00:00Z",
            )
        )
        session.add(
            Activity(
                id=activity_id,
                name="VO2max cached",
                activity_type="real",
                started_at_utc="2026-02-03T10:00:00Z",
                created_at_utc="2026-02-03T10:00:00Z",
                file_hash_sha256="h" * 64,
                original_path=str((activity_dir / "original.fit").resolve()),
                parquet_path=str(parquet_path.resolve()),
            )
        )
        session.commit()
    finally:
        session.close()

    start_slow_indexation_in_background(
        factory,
        reason="test_vo2max_cache",
        strategy="backfill_full",
        force=True,
    )
    state = _wait_runner_done()

    assert state.last_result is not None
    assert state.last_result.indexed == 1
    assert fit_load_calls == 0
    assert parquet_path.read_bytes() == parquet_before


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


def test_fast_persists_completed_run_record(tmp_path, monkeypatch):
    monkeypatch.setenv("COURSESCOPE_DATA_DIR", str(tmp_path))

    from backend.config import get_activities_dir
    from backend.db.models import ProgressIndexationRun
    from backend.db.session import init_db, make_engine, make_session_factory
    from backend.progress.indexation_runner import start_fast_indexation_in_background

    _wait_runner_done()
    engine = make_engine()
    init_db(engine)
    factory = make_session_factory(engine)

    activities_dir = get_activities_dir().resolve()
    _write_activity_fs(activities_dir, "00000000-0000-0000-0000-0000000001f6", file_hash="f" * 64)

    start_fast_indexation_in_background(factory, reason="test_fast_run_persistence")
    _wait_runner_done()

    session = factory()
    try:
        rows = session.query(ProgressIndexationRun).order_by(ProgressIndexationRun.started_at_utc.asc()).all()
        assert len(rows) >= 1
        candidates = [r for r in rows if r.mode == "fast" and r.reason == "test_fast_run_persistence"]
        assert len(candidates) == 1
        row = candidates[0]
        assert row.mode == "fast"
        assert row.reason == "test_fast_run_persistence"
        assert row.status == "completed"
        assert row.finished_at_utc is not None
        assert int(row.duration_ms) >= 0
        assert row.result_json is not None
        payload = json.loads(str(row.result_json))
        assert "scanned" in payload
    finally:
        session.close()


def test_slow_persists_failed_run_record_on_timeout(tmp_path, monkeypatch):
    monkeypatch.setenv("COURSESCOPE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("COURSESCOPE_INDEXATION_TIMEOUT_S", "0.0001")

    from backend.config import get_activities_dir
    from backend.db.models import Activity, ProgressIndexationRun
    from backend.db.session import init_db, make_engine, make_session_factory
    from backend.progress.indexation_runner import start_slow_indexation_in_background

    _wait_runner_done()
    engine = make_engine()
    init_db(engine)
    factory = make_session_factory(engine)

    activities_dir = get_activities_dir().resolve()
    activity_id = "00000000-0000-0000-0000-0000000001f7"
    _, parquet_path, _ = _write_activity_fs(activities_dir, activity_id, file_hash="g" * 64)

    session = factory()
    try:
        session.add(
            Activity(
                id=activity_id,
                name="Timeout",
                activity_type="real",
                started_at_utc="2026-02-03T10:00:00Z",
                created_at_utc="2026-02-03T10:00:00Z",
                file_hash_sha256="g" * 64,
                original_path=str((activities_dir / activity_id / "original.gpx").resolve()),
                parquet_path=str(parquet_path.resolve()),
            )
        )
        session.commit()
    finally:
        session.close()

    start_slow_indexation_in_background(factory, reason="test_timeout", strategy="backfill_full", force=True)
    state = _wait_runner_done()

    assert state.last_error is not None
    assert "timeout" in state.last_error.lower()

    session = factory()
    try:
        rows = session.query(ProgressIndexationRun).order_by(ProgressIndexationRun.started_at_utc.asc()).all()
        assert len(rows) >= 1
        row = rows[-1]
        assert row.mode == "slow"
        assert row.status == "failed"
        assert row.error is not None
        assert "timeout" in str(row.error).lower()
        assert row.finished_at_utc is not None
    finally:
        session.close()


def test_fast_trigger_is_idempotent_while_running(tmp_path, monkeypatch):
    monkeypatch.setenv("COURSESCOPE_DATA_DIR", str(tmp_path))

    from backend.db.session import init_db, make_engine, make_session_factory
    from backend.progress.indexation_runner import IndexationResult, start_fast_indexation_in_background

    _wait_runner_done()
    engine = make_engine()
    init_db(engine)
    factory = make_session_factory(engine)

    call_count = {"n": 0}

    def _fake_fast_once(session, *, activities_dir, deadline_ts, commit_every=50):
        _ = session
        _ = activities_dir
        _ = deadline_ts
        _ = commit_every
        call_count["n"] += 1
        time.sleep(0.25)
        return IndexationResult(scanned=0, added=0, deleted=0, indexed=0, up_to_date=0, errors=0, skipped=0), False

    monkeypatch.setattr("backend.progress.indexation_runner._run_fast_indexation_once", _fake_fast_once, raising=True)

    state1 = start_fast_indexation_in_background(factory, reason="idempotence_test")
    state2 = start_fast_indexation_in_background(factory, reason="idempotence_test")

    assert state1.running is True
    assert state2.running is True

    _wait_runner_done()
    assert call_count["n"] == 1
