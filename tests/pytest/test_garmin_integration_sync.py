from __future__ import annotations

import io
import os
import zipfile
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app


def _zip_fit_bytes(fit_bytes: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("activity.fit", fit_bytes)
    return buf.getvalue()


def _load_fit_fixture_bytes() -> tuple[bytes, str]:
    root = Path(__file__).resolve().parents[2]
    fixture = root / "tests" / "course.fit"
    return fixture.read_bytes(), fixture.name


class _FakeGarmin:
    class ActivityDownloadFormat:
        ORIGINAL = object()

    def __init__(self, *, activities: list[dict], original_zip_bytes: bytes):
        self._activities = activities
        self._zip = original_zip_bytes

    def get_activities_by_date(self, _start: str, _end: str):
        return list(self._activities)

    def download_activity(self, _activity_id: str, *, dl_fmt):
        assert dl_fmt is self.ActivityDownloadFormat.ORIGINAL
        return self._zip


@pytest.fixture()
def _isolated_env(tmp_path: Path, monkeypatch):
    data_dir = tmp_path / "data"
    db_path = tmp_path / "coursescope.sqlite"

    monkeypatch.setenv("COURSESCOPE_DATA_DIR", str(data_dir))
    monkeypatch.setenv("COURSESCOPE_DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    # Keep initial sync bounded to a single window.
    monkeypatch.setenv("COURSESCOPE_GARMIN_BACKFILL_START_DATE", date.today().isoformat())
    yield


def test_garmin_sync_idempotent(_isolated_env, monkeypatch):
    fit_bytes, filename = _load_fit_fixture_bytes()
    zip_bytes = _zip_fit_bytes(fit_bytes)
    fake = _FakeGarmin(
        activities=[{"activityId": 123, "activityName": "Run 123", "activityType": {"typeKey": "running"}}],
        original_zip_bytes=zip_bytes,
    )

    from api.routes import garmin_integration as garmin_routes

    monkeypatch.setattr(garmin_routes, "connect_with_tokens", lambda: fake)
    trigger_calls = {"n": 0, "reasons": []}

    class _State:
        running = False

    def _fake_trigger(*, db_session_factory, reason):
        _ = db_session_factory
        trigger_calls["n"] += 1
        trigger_calls["reasons"].append(reason)
        return _State()

    monkeypatch.setattr(garmin_routes, "start_fast_indexation_in_background", _fake_trigger)

    with TestClient(app) as client:
        r1 = client.post("/integrations/garmin/sync")
        assert r1.status_code == 200
        p1 = r1.json()
        assert p1["status"] == "ok"
        assert p1["imported_count"] == 1

        status = client.get("/integrations/garmin/status")
        assert status.status_code == 200
        s = status.json()
        assert isinstance(s.get("tokens_present"), bool)
        assert isinstance(s.get("tokens_dir"), str)
        assert isinstance(s.get("cursor_time_utc"), str)
        assert isinstance(s.get("cursor_updated_at_utc"), str)
        assert isinstance(s.get("last_run"), dict)
        last = s["last_run"]
        assert last["status"] in {"ok", "error", "running"}
        assert last["processed_count"] == int(last["imported_count"]) + int(last["skipped_count"])
        assert isinstance(last.get("duration_s"), (int, type(None)))

        r2 = client.post("/integrations/garmin/sync")
        assert r2.status_code == 200
        p2 = r2.json()
        assert p2["status"] == "ok"
        assert p2["imported_count"] == 0
        assert p2["skipped_count"] >= 1
        assert trigger_calls["n"] == 2
        assert trigger_calls["reasons"] == ["garmin_sync", "garmin_sync"]


def test_garmin_sync_renews_invalid_tokens_from_saved_credentials(_isolated_env, monkeypatch):
    fit_bytes, _ = _load_fit_fixture_bytes()
    fake = _FakeGarmin(activities=[], original_zip_bytes=_zip_fit_bytes(fit_bytes))
    from api.routes import garmin_integration as garmin_routes
    from integrations.garmin.client import GarminAuthError

    calls = {"connect": 0, "login": 0}

    def connect():
        calls["connect"] += 1
        if calls["connect"] == 1:
            raise GarminAuthError("expired token")
        return fake

    def login(*, email: str, password: str):
        assert email == "runner@example.test"
        assert password == "saved-secret"
        calls["login"] += 1
        return None

    monkeypatch.setattr(garmin_routes, "connect_with_tokens", connect)
    monkeypatch.setattr(garmin_routes, "load_credentials", lambda: SimpleNamespace(email="runner@example.test", password="saved-secret"))
    monkeypatch.setattr(garmin_routes, "start_login", login)
    monkeypatch.setattr(garmin_routes, "start_fast_indexation_in_background", lambda **_: None)

    with TestClient(app) as client:
        response = client.post("/integrations/garmin/sync")

    assert response.status_code == 200
    assert calls == {"connect": 2, "login": 1}


def test_garmin_sync_returns_401_for_incompatible_garth_installation(_isolated_env, monkeypatch):
    from api.routes import garmin_integration as garmin_routes
    from integrations.garmin.client import GarminAuthError

    def incompatible_tokens():
        raise GarminAuthError("Incompatible garth installation (missing garth.resume)")

    def incompatible_login(*, email: str, password: str):
        _ = email, password
        raise GarminAuthError("Incompatible garth installation (missing garth.http.Client)")

    monkeypatch.setattr(garmin_routes, "connect_with_tokens", incompatible_tokens)
    monkeypatch.setattr(
        garmin_routes,
        "load_credentials",
        lambda: SimpleNamespace(email="runner@example.test", password="saved-secret"),
    )
    monkeypatch.setattr(garmin_routes, "start_login", incompatible_login)

    with TestClient(app) as client:
        response = client.post("/integrations/garmin/sync")

    assert response.status_code == 401
    assert response.json()["detail"].startswith("reauth_required:")
    assert "garth.http.Client" in response.json()["detail"]


def test_garmin_sync_skips_when_manual_upload_matches_file_hash(_isolated_env, monkeypatch):
    fit_bytes, filename = _load_fit_fixture_bytes()
    zip_bytes = _zip_fit_bytes(fit_bytes)
    fake = _FakeGarmin(
        activities=[{"activityId": 999, "activityName": "Run 999", "activityType": {"typeKey": "running"}}],
        original_zip_bytes=zip_bytes,
    )

    from api.routes import garmin_integration as garmin_routes

    monkeypatch.setattr(garmin_routes, "connect_with_tokens", lambda: fake)

    with TestClient(app) as client:
        manual = client.post(
            "/activity/load",
            files={"file": (filename, fit_bytes, "application/octet-stream")},
    data={"name": "Manual Upload"},
        )
        assert manual.status_code == 200
        manual_id = manual.json()["id"]

        sync = client.post("/integrations/garmin/sync")
        assert sync.status_code == 200
        payload = sync.json()
        assert payload["status"] == "ok"
        assert payload["imported_count"] == 0
        assert payload["skipped_count"] >= 1

        # Still only one activity directory exists (the manual upload).
        activities_dir = Path(os.environ["COURSESCOPE_DATA_DIR"]) / "activities"
        dirs = [p for p in activities_dir.iterdir() if p.is_dir()]
        assert len(dirs) == 1
        assert dirs[0].name == manual_id
