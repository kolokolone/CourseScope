from __future__ import annotations

import io
import os
import zipfile
from datetime import date
from pathlib import Path

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
def _isolated_env(tmp_path: Path):
    data_dir = tmp_path / "data"
    db_path = tmp_path / "coursescope.sqlite"

    os.environ["COURSESCOPE_DATA_DIR"] = str(data_dir)
    os.environ["COURSESCOPE_DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    # Keep initial sync bounded to a single window.
    os.environ["COURSESCOPE_GARMIN_BACKFILL_START_DATE"] = date.today().isoformat()
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

    with TestClient(app) as client:
        r1 = client.post("/integrations/garmin/sync")
        assert r1.status_code == 200
        p1 = r1.json()
        assert p1["status"] == "ok"
        assert p1["imported_count"] == 1

        r2 = client.post("/integrations/garmin/sync")
        assert r2.status_code == 200
        p2 = r2.json()
        assert p2["status"] == "ok"
        assert p2["imported_count"] == 0
        assert p2["skipped_count"] >= 1


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
            data={"name": "Manual Upload", "persist_to_disk": "true"},
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
