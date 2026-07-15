from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.api.main import app


def _fixture() -> tuple[str, bytes]:
    path = Path(__file__).resolve().parents[1] / 'course.gpx'
    return path.name, path.read_bytes()


def _upload(client: TestClient) -> dict:
    filename, data = _fixture()
    response = client.post('/traces/upload', files={'file': (filename, data, 'application/gpx+xml')}, data={'name': 'Trace API'})
    assert response.status_code == 200, response.text
    assert 'activity_id' not in response.json()
    return response.json()['trace']


def test_trace_plan_save_reload_stops_and_comparison(tmp_path, monkeypatch):
    monkeypatch.setenv('COURSESCOPE_DATA_DIR', str(tmp_path))
    monkeypatch.delenv('COURSESCOPE_DATABASE_URL', raising=False)
    with TestClient(app) as client:
        trace = _upload(client)
        trace_id = trace['id']
        detail = client.get(f'/traces/{trace_id}')
        assert detail.status_code == 200
        detail_data = detail.json()
        assert detail_data['file']['parquet_source'] == 'parquet'
        plan_id = detail_data['active_plan']['id']
        plan = client.get(f'/traces/{trace_id}/plans/{plan_id}').json()
        scenario_id = plan['active_scenario_id']

        plan_patch = client.patch(f'/traces/{trace_id}/plans/{plan_id}', json={'race_date': '2026-07-20', 'start_time': '08:00', 'timezone': 'Europe/Paris'})
        assert plan_patch.status_code == 200
        stop = client.post(f'/traces/{trace_id}/plans/{plan_id}/scenarios/{scenario_id}/stops', json={'distance_km': 1.0, 'stop_type': 'water_nutrition', 'duration_s': 90})
        assert stop.status_code == 201

        preview = client.post(f'/traces/{trace_id}/plan-preview', json={'plan_id': plan_id, 'scenario_id': scenario_id})
        assert preview.status_code == 200, preview.text
        body = preview.json()
        assert body['totals']['stop_time_s'] == 90
        assert body['totals']['arrival_time_iso'] is not None
        preview_stop = body['stops'][0]
        assert preview_stop['stop_type'] == 'water_nutrition'
        assert preview_stop['departure_elapsed_time_s'] - preview_stop['arrival_elapsed_time_s'] == 90
        assert preview_stop['arrival_time_iso'] is not None
        assert preview_stop['departure_time_iso'] is not None
        passage_times = [row['elapsed_time_s'] for row in body['passages']]
        assert passage_times == sorted(passage_times)
        assert abs(sum(row['time_s'] for row in body['histograms']['pace']['complete_classes']) - body['totals']['running_time_s']) < 1e-6
        assert abs(sum(row['time_s'] for row in body['histograms']['grade']['complete_classes']) - body['totals']['running_time_s']) < 1e-6

        scenario_two = client.post(f'/traces/{trace_id}/plans/{plan_id}/scenarios', json={'name': 'Rapide', 'objective_type': 'time', 'target_value': body['totals']['running_time_s'] * 0.95, 'slope_model': 'minetti'})
        assert scenario_two.status_code == 201
        scenario_two_id = scenario_two.json()['scenario']['id']
        comparison = client.post(f'/traces/{trace_id}/plans/{plan_id}/compare', json={'scenario_ids': [scenario_id, scenario_two_id]})
        assert comparison.status_code == 200, comparison.text
        assert len(comparison.json()['scenarios']) == 2

        reloaded = client.get(f'/traces/{trace_id}/plans/{plan_id}')
        assert reloaded.status_code == 200
        active = next(item for item in reloaded.json()['scenarios'] if item['id'] == scenario_id)
        assert active['stops'][0]['duration_s'] == 90


def test_trace_id_and_activity_id_are_not_resolved_interchangeably(tmp_path, monkeypatch):
    monkeypatch.setenv('COURSESCOPE_DATA_DIR', str(tmp_path))
    monkeypatch.delenv('COURSESCOPE_DATABASE_URL', raising=False)
    with TestClient(app) as client:
        trace_id = _upload(client)['id']
        assert client.get(f'/activity/{trace_id}/real').status_code == 404
        assert client.post(f'/traces/{trace_id}/open').status_code == 410
        filename, data = _fixture()
        activity = client.post('/activity/load', files={'file': (filename, data, 'application/gpx+xml')}, data={'name': 'Reelle'}).json()
        assert activity['type'] == 'real'
        assert client.get(f'/traces/{activity["id"]}').status_code == 404


def test_opening_legacy_trace_creates_default_plan_automatically_once(tmp_path, monkeypatch):
    monkeypatch.setenv('COURSESCOPE_DATA_DIR', str(tmp_path))
    monkeypatch.delenv('COURSESCOPE_DATABASE_URL', raising=False)
    with TestClient(app) as client:
        trace_id = _upload(client)['id']
        initial = client.get(f'/traces/{trace_id}').json()
        initial_plan_id = initial['active_plan']['id']
        deleted = client.delete(f'/traces/{trace_id}/plans/{initial_plan_id}')
        assert deleted.status_code == 200

        reopened = client.get(f'/traces/{trace_id}')
        assert reopened.status_code == 200
        reopened_body = reopened.json()
        assert reopened_body['active_plan'] is not None
        assert reopened_body['active_plan']['name'] == 'Plan principal'
        assert reopened_body['active_plan']['id'] != initial_plan_id
        assert len(reopened_body['plans']) == 1

        opened_again = client.get(f'/traces/{trace_id}').json()
        assert opened_again['active_plan']['id'] == reopened_body['active_plan']['id']
        assert len(opened_again['plans']) == 1
