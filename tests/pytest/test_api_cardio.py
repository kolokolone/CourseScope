from pathlib import Path

from fastapi.testclient import TestClient

from backend.api.main import app


def _load_fit_fixture_bytes() -> tuple[bytes, str]:
    root = Path(__file__).resolve().parents[2]
    fixture = root / "tests" / "course.fit"
    return fixture.read_bytes(), fixture.name


def test_real_activity_includes_cardio_summary_from_fit():
    with TestClient(app) as client:
        data, filename = _load_fit_fixture_bytes()
        response = client.post(
            "/activity/load",
            files={"file": (filename, data, "application/octet-stream")},
            data={"name": "Cardio Test"},
        )
        assert response.status_code == 200
        activity_id = response.json()["id"]

        real_resp = client.get(f"/activity/{activity_id}/real")
        assert real_resp.status_code == 200
        payload = real_resp.json()

        summary = payload["summary"]
        assert "cardio" in summary
        cardio = summary["cardio"]

        assert "hr_avg_bpm" in cardio
        assert "hr_max_bpm" in cardio
        assert "hr_min_bpm" in cardio

        assert isinstance(cardio["hr_avg_bpm"], (int, float))
        assert isinstance(cardio["hr_max_bpm"], (int, float))
        assert isinstance(cardio["hr_min_bpm"], (int, float))
        assert cardio["hr_min_bpm"] <= cardio["hr_avg_bpm"] <= cardio["hr_max_bpm"]
