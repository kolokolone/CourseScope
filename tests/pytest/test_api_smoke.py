from pathlib import Path

from fastapi.testclient import TestClient

from api.main import app


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

        series_resp = client.get(f"/activity/{activity_id}/series/speed")
        assert series_resp.status_code == 200
        series_payload = series_resp.json()
        assert series_payload["name"] == "speed"

        map_resp = client.get(f"/activity/{activity_id}/map")
        assert map_resp.status_code == 200
        map_payload = map_resp.json()
        assert "polyline" in map_payload
