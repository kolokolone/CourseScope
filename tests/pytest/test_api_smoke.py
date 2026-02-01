from pathlib import Path

from fastapi.testclient import TestClient

from backend.api.main import app


def _load_fixture_bytes() -> tuple[bytes, str]:
    root = Path(__file__).resolve().parents[2]
    fixture = root / "tests" / "course.gpx"
    return fixture.read_bytes(), fixture.name


def test_health_check():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "healthy"


def test_load_activity_and_fetch_endpoints():
    with TestClient(app) as client:
        data, filename = _load_fixture_bytes()
        response = client.post(
            "/activity/load",
            files={"file": (filename, data, "application/gpx+xml")},
            data={"name": "Smoke Test"},
        )
        assert response.status_code == 200
        payload = response.json()
        activity_id = payload["id"]

        real_resp = client.get(f"/activity/{activity_id}/real")
        assert real_resp.status_code == 200
        real_payload = real_resp.json()
        assert "series_index" in real_payload
        assert "training_load" in real_payload
        assert "segment_analysis" in real_payload
        assert "performance_predictions" in real_payload
        assert "personal_records" in real_payload

        training_load = real_payload.get("training_load")
        if training_load is not None:
            assert "trimp" in training_load
            assert "method" in training_load

        segment_analysis = real_payload.get("segment_analysis")
        if segment_analysis is not None:
            assert "rows" in segment_analysis

        performance_predictions = real_payload.get("performance_predictions")
        if performance_predictions is not None:
            assert "items" in performance_predictions

        personal_records = real_payload.get("personal_records")
        if personal_records is not None:
            assert "rows" in personal_records

        series_resp = client.get(f"/activity/{activity_id}/series/speed")
        assert series_resp.status_code == 200
        series_payload = series_resp.json()
        assert series_payload["name"] == "speed"

        map_resp = client.get(f"/activity/{activity_id}/map")
        assert map_resp.status_code == 200
        map_payload = map_resp.json()
        assert "polyline" in map_payload
