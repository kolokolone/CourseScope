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
            "location_city": "Bedoin",
            "location_country": "France",
            "location_country_code": "FR",
            "location_lat": 44.125,
            "location_lon": 5.183,
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
        assert goal_a["location_city"] == "Bedoin"
        assert goal_a["location_country"] == "France"
        assert goal_a["location_country_code"] == "FR"

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

        cleanup_resp = client.delete("/goals")
        assert cleanup_resp.status_code == 200
        assert cleanup_resp.json()["deleted"] >= 1

        listed_final = client.get("/goals")
        assert listed_final.status_code == 200
        assert listed_final.json()["goals"] == []


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
        assert isinstance(real_resp.json().get("started_at_utc"), str)

        bins_resp = client.get(f"/activity/{activity_id}/real-bins")
        assert bins_resp.status_code == 200
        bins = bins_resp.json()
        assert isinstance(bins.get("pace_elevation_series"), list)
        assert isinstance(bins.get("pace_time_bins"), list)
        assert isinstance(bins.get("grade_time_bins"), list)


def test_theoretical_activity_endpoint_is_deprecated_and_trace_preview_is_used(tmp_path, monkeypatch):
    monkeypatch.setenv("COURSESCOPE_DATA_DIR", str(tmp_path))

    with TestClient(app) as client:
        data, filename = _load_fixture_bytes()
        load_resp = client.post(
            "/traces/upload",
            files={"file": (filename, data, "application/gpx+xml")},
            data={"name": "Pace parse"},
        )
        assert load_resp.status_code == 200
        trace_id = load_resp.json()["trace"]["id"]
        assert "activity_id" not in load_resp.json()

        deprecated = client.get(f"/activity/{trace_id}/theoretical")
        assert deprecated.status_code == 410
        detail = client.get(f"/traces/{trace_id}").json()
        plan = detail["active_plan"]
        scenario_id = plan["active_scenario_id"]
        resp = client.post(f"/traces/{trace_id}/plan-preview", json={"plan_id": plan["id"], "scenario_id": scenario_id})
        assert resp.status_code == 200
        body = resp.json()
        assert body["units"]["distance"] == "km"
        assert body["units"]["pace"] == "s/km"


def test_geo_cities_short_query_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("COURSESCOPE_DATA_DIR", str(tmp_path))

    with TestClient(app) as client:
        resp = client.get("/geo/cities", params={"query": "a"})
        assert resp.status_code == 422
