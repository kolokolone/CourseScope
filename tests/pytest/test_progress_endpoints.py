from fastapi.testclient import TestClient

from backend.api.main import app


def _insert_rows(client: TestClient, rows, best_efforts):
    factory = getattr(client.app.state, "db_session_factory", None)
    assert factory is not None
    session = factory()
    try:
        for r in rows:
            session.add(r)
        for p in best_efforts:
            session.add(p)
        session.commit()
    finally:
        session.close()


def test_progress_series_and_best_efforts(tmp_path, monkeypatch):
    monkeypatch.setenv("COURSESCOPE_DATA_DIR", str(tmp_path))

    from backend.db.models import ProgressActivityIndex, ProgressBestEffortPoint

    with TestClient(app) as client:
        rows = [
            ProgressActivityIndex(
                activity_id="a1",
                activity_type="real",
                start_ts_utc="2026-02-03T10:00:00Z",
                local_date="2026-02-03",
                tz=None,
                fingerprint="fp1",
                metrics_version=1,
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
                has_hr=1,
                has_power=0,
                has_cadence=0,
                data_points=1234,
            ),
            ProgressActivityIndex(
                activity_id="a2",
                activity_type="real",
                start_ts_utc="2026-02-04T10:00:00Z",
                local_date="2026-02-04",
                tz=None,
                fingerprint="fp2",
                metrics_version=1,
                indexed_at_ts="2026-02-04T10:00:00Z",
                distance_m=7000.0,
                moving_time_s=2000.0,
                elapsed_time_s=2100.0,
                elevation_gain_m=60.0,
                avg_pace_s_per_km=285.0,
                best_pace_s_per_km=240.0,
                pace_threshold_s_per_km=300.0,
                avg_hr_bpm=145.0,
                max_hr_bpm=178.0,
                trimp=50.0,
                training_load_method="edwards",
                decoupling_pct=5.0,
                cardiac_drift_pct=5.0,
                stability_cv=0.09,
                stability_iqr_ratio=0.13,
                aerobic_efficiency_m_s_per_bpm=0.10,
                has_hr=1,
                has_power=0,
                has_cadence=0,
                data_points=2345,
            ),
            ProgressActivityIndex(
                activity_id="a3",
                activity_type="real",
                start_ts_utc="2026-02-10T10:00:00Z",
                local_date="2026-02-10",
                tz=None,
                fingerprint="fp3",
                metrics_version=1,
                indexed_at_ts="2026-02-10T10:00:00Z",
                distance_m=3000.0,
                moving_time_s=1000.0,
                elapsed_time_s=1100.0,
                elevation_gain_m=30.0,
                avg_pace_s_per_km=333.0,
                best_pace_s_per_km=260.0,
                pace_threshold_s_per_km=340.0,
                avg_hr_bpm=135.0,
                max_hr_bpm=168.0,
                trimp=20.0,
                training_load_method="edwards",
                decoupling_pct=3.0,
                cardiac_drift_pct=3.0,
                stability_cv=0.10,
                stability_iqr_ratio=0.14,
                aerobic_efficiency_m_s_per_bpm=0.07,
                has_hr=1,
                has_power=0,
                has_cadence=0,
                data_points=3456,
            ),
        ]

        points = [
            ProgressBestEffortPoint(
                activity_id="a1",
                start_ts_utc="2026-02-03T10:00:00Z",
                effort_kind="pace_s_per_km",
                duration_s=1200,
                value=300.0,
            ),
            ProgressBestEffortPoint(
                activity_id="a2",
                start_ts_utc="2026-02-04T10:00:00Z",
                effort_kind="pace_s_per_km",
                duration_s=1200,
                value=290.0,
            ),
            ProgressBestEffortPoint(
                activity_id="a3",
                start_ts_utc="2026-02-10T10:00:00Z",
                effort_kind="pace_s_per_km",
                duration_s=1200,
                value=295.0,
            ),
        ]

        _insert_rows(client, rows, points)

        series = client.get(
            "/progress/series",
            params={
                "metric": "distance_m",
                "group_by": "week",
                "agg": "sum",
                "from": "2026-02-01",
                "to": "2026-02-28",
            },
        )
        assert series.status_code == 200
        payload = series.json()
        assert payload == [
            {"bucket_start": "2026-02-02", "value": 12000.0},
            {"bucket_start": "2026-02-09", "value": 3000.0},
        ]

        best = client.get(
            "/progress/best-efforts",
            params={"kind": "pace_s_per_km", "duration_s": 1200, "from": "2026-02-01", "to": "2026-02-28"},
        )
        assert best.status_code == 200
        best_payload = best.json()
        pts = best_payload["points"]
        assert [p["is_pr"] for p in pts] == [True, True, False]

        acts = client.get("/progress/activities", params={"from": "2026-02-01", "to": "2026-02-28"})
        assert acts.status_code == 200
        acts_payload = acts.json()
        assert len(acts_payload["activities"]) == 3


def test_progress_verify_status_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("COURSESCOPE_DATA_DIR", str(tmp_path))

    with TestClient(app) as client:
        res = client.get("/progress/verify-status")
        assert res.status_code == 200
        body = res.json()
        assert isinstance(body["running"], bool)
        assert "last_started_at_utc" in body
        assert "last_finished_at_utc" in body
        assert "last_error" in body
        assert "last_result" in body
