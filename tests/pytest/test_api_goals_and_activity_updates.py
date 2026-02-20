from pathlib import Path

from fastapi.testclient import TestClient

from backend.api.main import app


def _load_fixture_bytes() -> tuple[bytes, str]:
    root = Path(__file__).resolve().parents[2]
    fixture = root / "tests" / "course.gpx"
    return fixture.read_bytes(), fixture.name


def test_goals_create_list_delete(tmp_path, monkeypatch):
    monkeypatch.setenv("COURSESCOPE_DATA_DIR", str(tmp_path))

    with TestClient(app) as client:
        empty = client.get("/goals")
        assert empty.status_code == 200
        assert empty.json()["goals"] == []

        payload_a = {
            "name": "Trail du Ventoux",
            "event_date": "2026-06-15",
            "distance_km": 46.2,
            "location": "Bedoin",
            "target_time_s": 18240,
            "race_type": "trail",
        }
        payload_b = {
            "name": "Semi de Paris",
            "event_date": "2026-05-10",
            "distance_km": 21.1,
            "target_pace_s_per_km": 285,
            "race_type": "road",
        }

        created_a = client.post("/goals", json=payload_a)
        assert created_a.status_code == 200
        goal_a = created_a.json()
        assert goal_a["name"] == payload_a["name"]

        created_b = client.post("/goals", json=payload_b)
        assert created_b.status_code == 200
        goal_b = created_b.json()
        assert goal_b["name"] == payload_b["name"]

        listed = client.get("/goals")
        assert listed.status_code == 200
        goals = listed.json()["goals"]
        assert [g["name"] for g in goals] == [payload_b["name"], payload_a["name"]]

        update_resp = client.patch(
            f"/goals/{goal_b['id']}",
            json={
                "name": "Semi de Paris - objectif chrono",
                "event_date": "2026-05-12",
                "distance_km": 21.1,
                "location": "Paris",
                "target_time_s": 5400,
                "target_pace_s_per_km": None,
                "race_type": "road",
                "notes": "Depart prudent puis acceleration",
            },
        )
        assert update_resp.status_code == 200
        updated_goal = update_resp.json()
        assert updated_goal["name"] == "Semi de Paris - objectif chrono"
        assert updated_goal["event_date"] == "2026-05-12"
        assert int(round(float(updated_goal["target_time_s"]))) == 5400
        assert updated_goal["target_pace_s_per_km"] is None
        assert updated_goal["location"] == "Paris"

        delete_resp = client.delete(f"/goals/{goal_a['id']}")
        assert delete_resp.status_code == 200
        assert delete_resp.json()["deleted"] is True

        listed_after = client.get("/goals")
        assert listed_after.status_code == 200
        assert [g["id"] for g in listed_after.json()["goals"]] == [goal_b["id"]]


def test_activity_rename_and_real_endpoint_title(tmp_path, monkeypatch):
    monkeypatch.setenv("COURSESCOPE_DATA_DIR", str(tmp_path))

    with TestClient(app) as client:
        data, filename = _load_fixture_bytes()
        load_resp = client.post(
            "/activity/load",
            files={"file": (filename, data, "application/gpx+xml")},
            data={"name": "Nom initial"},
        )
        assert load_resp.status_code == 200
        activity_id = load_resp.json()["id"]

        rename_resp = client.patch(f"/activities/{activity_id}", json={"name": "Sortie tempo du mardi"})
        assert rename_resp.status_code == 200
        assert rename_resp.json()["name"] == "Sortie tempo du mardi"

        listed = client.get("/activities")
        assert listed.status_code == 200
        one = next((row for row in listed.json()["activities"] if row["id"] == activity_id), None)
        assert one is not None
        assert one["name"] == "Sortie tempo du mardi"

        real_resp = client.get(f"/activity/{activity_id}/real")
        assert real_resp.status_code == 200
        assert real_resp.json()["activity_name"] == "Sortie tempo du mardi"


def test_theoretical_target_pace_single_integer_is_accepted(tmp_path, monkeypatch):
    monkeypatch.setenv("COURSESCOPE_DATA_DIR", str(tmp_path))

    with TestClient(app) as client:
        data, filename = _load_fixture_bytes()
        load_resp = client.post(
            "/activity/load",
            files={"file": (filename, data, "application/gpx+xml")},
            data={"name": "Pace parse"},
        )
        assert load_resp.status_code == 200
        activity_id = load_resp.json()["id"]

        resp = client.get(
            f"/activity/{activity_id}/theoretical",
            params={"target_mode": "pace", "target_pace": "6", "grade_model": "pro_ref"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert int(round(float(body["target_pace_s_per_km"]))) == 360
