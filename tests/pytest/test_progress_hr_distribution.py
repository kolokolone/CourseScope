from typing import Any, cast

from fastapi.testclient import TestClient

from backend.api.main import app


def _insert_manual_zone_row(client: TestClient, *, used_hr_max: float) -> None:
    from backend.db.models import ProgressActivityIndex, UserSettings

    factory = cast(Any, client.app).state.db_session_factory
    session = factory()
    try:
        session.add(UserSettings(
            id=1,
            vma_kmh=None,
            vo2max_lastest=None,
            hr_max_manual_bpm=200,
            hr_max_source="manual",
            updated_at_utc="2026-07-01T00:00:00Z",
        ))
        session.add(ProgressActivityIndex(
            activity_id="zones-a1",
            activity_type="real",
            start_ts_utc="2026-07-01T10:00:00Z",
            local_date="2026-07-01",
            tz="Europe/Paris",
            fingerprint="zones-fp",
            metrics_version=10,
            indexed_at_ts="2026-07-01T10:00:00Z",
            max_hr_bpm=190.0,
            has_hr=1,
            has_power=0,
            has_cadence=0,
            z1_time_s=60.0,
            z2_time_s=120.0,
            z3_time_s=180.0,
            z4_time_s=240.0,
            z5_time_s=300.0,
            hr_max_used_bpm=used_hr_max,
            hr_max_source="manual",
        ))
        session.commit()
    finally:
        session.close()


def test_intensity_distribution_exposes_exact_ranges_and_provenance(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("COURSESCOPE_DATA_DIR", str(tmp_path))
    with TestClient(app) as client:
        _insert_manual_zone_row(client, used_hr_max=200.0)
        response = client.get(
            "/progress/intensity-distribution",
            params={"from": "2026-07-01", "to": "2026-07-31", "type": "real"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["zones_stale"] is False
        assert body["hr_max_used_bpm"] == 200.0
        assert body["hr_max_source"] == "manual"
        assert [(item["min_percent"], item["max_percent"]) for item in body["zone_ranges_bpm"]] == [
            (50, 60), (60, 70), (70, 80), (80, 90), (90, None)
        ]
        assert len(body["points"]) == 1


def test_intensity_distribution_hides_stale_zone_bins(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("COURSESCOPE_DATA_DIR", str(tmp_path))
    with TestClient(app) as client:
        _insert_manual_zone_row(client, used_hr_max=190.0)
        response = client.get(
            "/progress/intensity-distribution",
            params={"from": "2026-07-01", "to": "2026-07-31", "type": "real"},
        )

        assert response.status_code == 200
        assert response.json()["zones_stale"] is True
        assert response.json()["points"] == []


def test_hr_setting_change_requests_forced_reindexation(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("COURSESCOPE_DATA_DIR", str(tmp_path))
    import api.routes.settings as settings_routes

    calls: list[dict[str, object]] = []

    def fake_start(factory, reason: str, strategy: str, force: bool):
        calls.append({"factory": factory, "reason": reason, "strategy": strategy, "force": force})
        return None

    monkeypatch.setattr(settings_routes, "start_slow_indexation_in_background", fake_start)
    with TestClient(app) as client:
        response = client.patch(
            "/settings/personal",
            json={"hr_max_manual_bpm": 195, "hr_max_source": "manual"},
        )

        assert response.status_code == 200
        assert calls[0]["reason"] == "hr_max_settings_changed"
        assert calls[0]["strategy"] == "backfill_full"
        assert calls[0]["force"] is True
