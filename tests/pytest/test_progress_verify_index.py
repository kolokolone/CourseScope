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
    monkeypatch.setattr(verify_mod, "_extract_fit_vo2max", lambda _fit: 54.2)

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


def test_verify_progress_index_backfill_keeps_fit_stream_open(tmp_path, monkeypatch):
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
    activity_id = "00000000-0000-0000-0000-0000000000ac"
    activity_dir = activities_dir / activity_id
    activity_dir.mkdir(parents=True, exist_ok=True)

    df = _make_df(20)
    parquet_path = activity_dir / "df.parquet"
    df.to_parquet(parquet_path, engine="pyarrow")

    meta = {
        "id": activity_id,
        "filename": "original.fit",
        "name": "Verify VO2 Stream",
        "activity_type": "real",
        "created_at": "2026-02-03T10:00:00Z",
        "started_at": "2026-02-03T10:00:00Z",
        "file_hash": "cafefeed" * 8,
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

    def _fake_extract_fit_vo2max(fh):
        if getattr(fh, "closed", False):
            raise ValueError("fit stream is closed")
        _ = fh.read(1)
        return 51.1

    monkeypatch.setattr(verify_mod, "load_fit", lambda fh: fh)
    monkeypatch.setattr(verify_mod, "_extract_fit_vo2max", _fake_extract_fit_vo2max)
    monkeypatch.setattr("backend.progress.verify_index.load_fit", lambda fh: fh, raising=False)
    monkeypatch.setattr("backend.progress.verify_index._extract_fit_vo2max", _fake_extract_fit_vo2max, raising=False)
    monkeypatch.setattr("progress.verify_index.load_fit", lambda fh: fh, raising=False)
    monkeypatch.setattr("progress.verify_index._extract_fit_vo2max", _fake_extract_fit_vo2max, raising=False)

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
        assert float(row.vo2max) == 51.1
    finally:
        session.close()


def test_verify_progress_index_prefers_fit_vo2_over_existing_parquet_vo2_on_reindex(tmp_path, monkeypatch):
    monkeypatch.setenv("COURSESCOPE_DATA_DIR", str(tmp_path))

    from backend.config import get_activities_dir
    from backend.progress.verify_index import _extract_vo2max_from_df, _maybe_backfill_vo2max_from_fit
    import backend.progress.verify_index as verify_mod

    activities_dir = get_activities_dir().resolve()
    activity_id = "00000000-0000-0000-0000-0000000000ad"
    activity_dir = activities_dir / activity_id
    activity_dir.mkdir(parents=True, exist_ok=True)

    df = _make_df(20).assign(vo2max=60.0)
    parquet_path = activity_dir / "df.parquet"
    df.to_parquet(parquet_path, engine="pyarrow")

    meta = {
        "id": activity_id,
        "filename": "original.fit",
        "name": "Verify VO2 Source Priority",
        "activity_type": "real",
        "created_at": "2026-02-03T10:00:00Z",
        "started_at": "2026-02-03T10:00:00Z",
        "file_hash": "deadbeef" * 8,
    }
    (activity_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=True, indent=2), encoding="utf-8")
    (activity_dir / "original.fit").write_bytes(b"fit")

    def _fake_extract_fit_vo2max(fh):
        if getattr(fh, "closed", False):
            raise ValueError("fit stream is closed")
        _ = fh.read(1)
        return 52.6

    monkeypatch.setattr(verify_mod, "load_fit", lambda fh: fh)
    monkeypatch.setattr(verify_mod, "_extract_fit_vo2max", _fake_extract_fit_vo2max)

    current_df = pd.read_parquet(parquet_path)
    assert float(_extract_vo2max_from_df(current_df)) == 60.0

    updated_df = _maybe_backfill_vo2max_from_fit(activity_dir, parquet_path, current_df)
    assert float(_extract_vo2max_from_df(updated_df)) == 52.6


def test_verify_progress_index_syncs_settings_vo2max_latest_from_most_recent_activity(tmp_path, monkeypatch):
    monkeypatch.setenv("COURSESCOPE_DATA_DIR", str(tmp_path))

    from backend.config import get_activities_dir
    from backend.db.models import ProgressActivityIndex, UserSettings
    from backend.db.session import init_db, make_engine, make_session_factory
    from backend.progress.verify_index import METRICS_VERSION, build_fingerprint, verify_progress_index

    engine = make_engine()
    init_db(engine)
    factory = make_session_factory(engine)

    activities_dir = get_activities_dir().resolve()

    older_id = "00000000-0000-0000-0000-0000000000b1"
    older_dir = activities_dir / older_id
    older_dir.mkdir(parents=True, exist_ok=True)
    older_df = _make_df(20).assign(vo2max=48.0)
    older_parquet = older_dir / "df.parquet"
    older_df.to_parquet(older_parquet, engine="pyarrow")
    older_meta = {
        "id": older_id,
        "filename": "original.fit",
        "name": "Older",
        "activity_type": "real",
        "created_at": "2026-02-03T10:00:00Z",
        "started_at": "2026-02-03T10:00:00Z",
        "file_hash": "olderhash" * 8,
    }
    (older_dir / "meta.json").write_text(json.dumps(older_meta, ensure_ascii=True, indent=2), encoding="utf-8")
    (older_dir / "original.fit").write_bytes(b"fit")

    newer_id = "00000000-0000-0000-0000-0000000000b2"
    newer_dir = activities_dir / newer_id
    newer_dir.mkdir(parents=True, exist_ok=True)
    newer_df = _make_df(20).assign(vo2max=55.0)
    newer_parquet = newer_dir / "df.parquet"
    newer_df.to_parquet(newer_parquet, engine="pyarrow")
    newer_meta = {
        "id": newer_id,
        "filename": "original.fit",
        "name": "Newer",
        "activity_type": "real",
        "created_at": "2026-02-10T10:00:00Z",
        "started_at": "2026-02-10T10:00:00Z",
        "file_hash": "newerhash" * 8,
    }
    (newer_dir / "meta.json").write_text(json.dumps(newer_meta, ensure_ascii=True, indent=2), encoding="utf-8")
    (newer_dir / "original.fit").write_bytes(b"fit")

    session = factory()
    try:
        session.add(
            ProgressActivityIndex(
                activity_id=older_id,
                activity_type="real",
                start_ts_utc="2026-02-03T10:00:00Z",
                local_date="2026-02-03",
                tz=None,
                fingerprint=build_fingerprint(older_meta, older_parquet),
                metrics_version=int(METRICS_VERSION),
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
                vo2max=None,
                has_hr=1,
                has_power=0,
                has_cadence=0,
                data_points=1234,
            )
        )
        session.add(
            ProgressActivityIndex(
                activity_id=newer_id,
                activity_type="real",
                start_ts_utc="2026-02-10T10:00:00Z",
                local_date="2026-02-10",
                tz=None,
                fingerprint=build_fingerprint(newer_meta, newer_parquet),
                metrics_version=int(METRICS_VERSION),
                indexed_at_ts="2026-02-10T10:00:00Z",
                distance_m=8000.0,
                moving_time_s=2200.0,
                elapsed_time_s=2300.0,
                elevation_gain_m=80.0,
                avg_pace_s_per_km=290.0,
                best_pace_s_per_km=240.0,
                pace_threshold_s_per_km=300.0,
                avg_hr_bpm=145.0,
                max_hr_bpm=178.0,
                trimp=55.0,
                training_load_method="edwards",
                decoupling_pct=3.0,
                cardiac_drift_pct=3.0,
                stability_cv=0.07,
                stability_iqr_ratio=0.11,
                aerobic_efficiency_m_s_per_bpm=0.1,
                vo2max=55.0,
                has_hr=1,
                has_power=0,
                has_cadence=0,
                data_points=1400,
            )
        )
        settings = session.get(UserSettings, 1)
        if settings is None:
            session.add(
                UserSettings(
                    id=1,
                    vma_kmh=None,
                    vo2max_lastest=41.0,
                    hr_max_manual_bpm=None,
                    hr_max_source="detected",
                    updated_at_utc="2026-02-01T00:00:00Z",
                )
            )
        else:
            settings.vo2max_lastest = 41.0
            settings.updated_at_utc = "2026-02-01T00:00:00Z"
        session.commit()
    finally:
        session.close()

    session = factory()
    try:
        res = verify_progress_index(session, activities_dir=activities_dir, commit_every=1)
    finally:
        session.close()

    assert res.scanned == 2
    assert res.errors == 0

    session = factory()
    try:
        older_row = session.get(ProgressActivityIndex, older_id)
        assert older_row is not None
        assert float(older_row.vo2max) == 48.0
        settings = session.get(UserSettings, 1)
        assert settings is not None
        assert float(settings.vo2max_lastest) == 55.0
    finally:
        session.close()


def test_verify_progress_index_deletes_orphan_activity_rows_when_files_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("COURSESCOPE_DATA_DIR", str(tmp_path))

    from sqlalchemy import select

    from backend.config import get_activities_dir
    from backend.db.models import (
        Activity,
        ActivitySource,
        ProgressActivityIndex,
        ProgressActivityTag,
        ProgressBestEffortPoint,
        ProgressPaceHrBin,
    )
    from backend.db.session import init_db, make_engine, make_session_factory
    from backend.progress.verify_index import verify_progress_index

    engine = make_engine()
    init_db(engine)
    factory = make_session_factory(engine)

    activities_dir = get_activities_dir().resolve()

    valid_id = "00000000-0000-0000-0000-0000000000c1"
    valid_dir = activities_dir / valid_id
    valid_dir.mkdir(parents=True, exist_ok=True)
    valid_df = _make_df(20)
    valid_parquet = valid_dir / "df.parquet"
    valid_df.to_parquet(valid_parquet, engine="pyarrow")
    valid_meta = {
        "id": valid_id,
        "filename": "original.gpx",
        "name": "Valid Activity",
        "activity_type": "real",
        "created_at": "2026-02-03T10:00:00Z",
        "started_at": "2026-02-03T10:00:00Z",
        "file_hash": "validhash" * 8,
    }
    (valid_dir / "meta.json").write_text(json.dumps(valid_meta, ensure_ascii=True, indent=2), encoding="utf-8")
    (valid_dir / "original.gpx").write_text("x", encoding="utf-8")

    orphan_id = "00000000-0000-0000-0000-0000000000c2"

    session = factory()
    try:
        session.add(
            Activity(
                id=orphan_id,
                name="Orphan Activity",
                activity_type="real",
                started_at_utc="2026-02-04T10:00:00Z",
                created_at_utc="2026-02-04T10:00:00Z",
                file_hash_sha256="orphanhash" * 8,
                original_path=str((activities_dir / orphan_id / "original.fit").resolve()),
                parquet_path=str((activities_dir / orphan_id / "df.parquet").resolve()),
            )
        )
        session.add(ActivitySource(activity_id=orphan_id, source="garmin", source_activity_id="ext-orphan"))
        session.add(
            ProgressActivityIndex(
                activity_id=orphan_id,
                activity_type="real",
                start_ts_utc="2026-02-04T10:00:00Z",
                local_date="2026-02-04",
                tz=None,
                fingerprint="fp-orphan",
                metrics_version=1,
                indexed_at_ts="2026-02-04T10:00:00Z",
                distance_m=10000.0,
                moving_time_s=3600.0,
                elapsed_time_s=3700.0,
                elevation_gain_m=120.0,
                avg_pace_s_per_km=360.0,
                best_pace_s_per_km=300.0,
                pace_threshold_s_per_km=350.0,
                avg_hr_bpm=150.0,
                max_hr_bpm=180.0,
                trimp=70.0,
                training_load_method="edwards",
                decoupling_pct=4.0,
                cardiac_drift_pct=4.0,
                stability_cv=0.08,
                stability_iqr_ratio=0.12,
                aerobic_efficiency_m_s_per_bpm=0.08,
                vo2max=50.0,
                has_hr=1,
                has_power=0,
                has_cadence=0,
                data_points=2000,
            )
        )
        session.add(
            ProgressActivityTag(
                activity_id=orphan_id,
                session_tag="tempo",
                terrain_tag="flat",
                race_marker=0,
                source="auto",
                updated_at_ts="2026-02-04T10:00:00Z",
            )
        )
        session.add(
            ProgressBestEffortPoint(
                activity_id=orphan_id,
                start_ts_utc="2026-02-04T10:00:00Z",
                effort_kind="pace_s_per_km",
                duration_s=1200,
                value=300.0,
            )
        )
        session.add(
            ProgressPaceHrBin(
                activity_id=orphan_id,
                activity_type="real",
                start_ts_utc="2026-02-04T10:00:00Z",
                pace_bin_s_per_km=300.0,
                time_s_bin=120.0,
                hr_mean_w_bpm=150.0,
                hr_q50_w_bpm=150.0,
            )
        )
        session.commit()
    finally:
        session.close()

    session = factory()
    try:
        res = verify_progress_index(session, activities_dir=activities_dir, commit_every=1)
    finally:
        session.close()

    assert res.scanned == 1
    assert res.errors == 0

    session = factory()
    try:
        assert session.get(Activity, orphan_id) is None
        assert session.get(ProgressActivityIndex, orphan_id) is None
        assert session.get(ProgressActivityTag, orphan_id) is None
        assert session.execute(select(ActivitySource).where(ActivitySource.activity_id == orphan_id)).scalars().first() is None
        assert (
            session.execute(select(ProgressBestEffortPoint).where(ProgressBestEffortPoint.activity_id == orphan_id))
            .scalars()
            .first()
            is None
        )
        assert session.execute(select(ProgressPaceHrBin).where(ProgressPaceHrBin.activity_id == orphan_id)).scalars().first() is None
        assert session.get(Activity, valid_id) is not None
        assert session.get(ProgressActivityIndex, valid_id) is not None
    finally:
        session.close()
