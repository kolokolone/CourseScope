from __future__ import annotations

import hashlib
import os
import uuid
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from io import BytesIO
from typing import Any, Iterable

from db.repository import ActivityIndexRepository
from services.analysis_service import load_activity


GARMIN_SOURCE = "garmin"


@dataclass(frozen=True)
class GarminSyncResult:
    run_id: str
    status: str
    imported_count: int
    skipped_count: int
    cursor_time_utc: str | None
    error: str | None = None


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _min_backfill_date() -> date:
    raw = os.getenv("COURSESCOPE_GARMIN_BACKFILL_START_DATE", "2000-01-01")
    try:
        return _parse_date(raw)
    except Exception:
        return date(2000, 1, 1)


def _chunk_ranges(start: date, end: date, chunk_days: int) -> Iterable[tuple[date, date]]:
    cur = start
    while cur <= end:
        chunk_end = min(end, cur + timedelta(days=chunk_days - 1))
        yield cur, chunk_end
        cur = chunk_end + timedelta(days=1)


def _extract_fit_bytes(original_bytes: bytes) -> bytes:
    # Garmin "ORIGINAL" is typically a ZIP containing .fit.
    if len(original_bytes) >= 4 and original_bytes[0:2] == b"PK":
        with zipfile.ZipFile(BytesIO(original_bytes)) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith(".fit")]
            if not names:
                raise ValueError("Garmin ORIGINAL payload zip has no .fit file")
            # Prefer the first .fit.
            return zf.read(names[0])
    # Fallback: already a FIT.
    return original_bytes


class GarminSyncService:
    def __init__(
        self,
        *,
        garmin_client: Any,
        storage: Any,
        db_session_factory: Any,
        repo: ActivityIndexRepository | None = None,
    ):
        self._garmin = garmin_client
        self._storage = storage
        self._db_session_factory = db_session_factory
        self._repo = repo or ActivityIndexRepository()

    def _now_cursor_iso(self) -> str:
        return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    def _get_cursor(self) -> str | None:
        session = self._db_session_factory()
        try:
            return self._repo.get_cursor(session, GARMIN_SOURCE)  # type: ignore[arg-type]
        finally:
            session.close()  # type: ignore[attr-defined]

    def _set_cursor(self, cursor_time_utc: str | None) -> None:
        session = self._db_session_factory()
        try:
            self._repo.set_cursor(session, GARMIN_SOURCE, cursor_time_utc)  # type: ignore[arg-type]
            session.commit()  # type: ignore[attr-defined]
        finally:
            session.close()  # type: ignore[attr-defined]

    def _start_run(self, run_id: str) -> None:
        session = self._db_session_factory()
        try:
            self._repo.start_sync_run(session, run_id=run_id, source=GARMIN_SOURCE)  # type: ignore[arg-type]
            session.commit()  # type: ignore[attr-defined]
        finally:
            session.close()  # type: ignore[attr-defined]

    def _finish_run(self, run_id: str, *, status: str, imported: int, skipped: int, error: str | None) -> None:
        session = self._db_session_factory()
        try:
            self._repo.finish_sync_run(
                session,  # type: ignore[arg-type]
                run_id=run_id,
                status=status,
                imported_count=imported,
                skipped_count=skipped,
                error=error,
            )
            session.commit()  # type: ignore[attr-defined]
        finally:
            session.close()  # type: ignore[attr-defined]

    def _has_source_mapping(self, source_activity_id: str) -> str | None:
        session = self._db_session_factory()
        try:
            return self._repo.get_activity_id_by_source(session, GARMIN_SOURCE, source_activity_id)  # type: ignore[arg-type]
        finally:
            session.close()  # type: ignore[attr-defined]

    def _get_activity_id_by_hash(self, file_hash: str) -> str | None:
        session = self._db_session_factory()
        try:
            return self._repo.get_activity_id_by_hash(session, file_hash)  # type: ignore[arg-type]
        finally:
            session.close()  # type: ignore[attr-defined]

    def _link_source(self, *, activity_id: str, source_activity_id: str) -> None:
        session = self._db_session_factory()
        try:
            self._repo.link_source(
                session,  # type: ignore[arg-type]
                activity_id=activity_id,
                source=GARMIN_SOURCE,
                source_activity_id=source_activity_id,
            )
            session.commit()  # type: ignore[attr-defined]
        finally:
            session.close()  # type: ignore[attr-defined]

    def _list_activities(self, start: date, end: date) -> list[dict[str, Any]]:
        items = self._garmin.get_activities_by_date(start.isoformat(), end.isoformat())
        if not isinstance(items, list):
            return []
        out: list[dict[str, Any]] = []
        for it in items:
            if isinstance(it, dict):
                out.append(it)
        return out

    def _download_original(self, activity_id: str) -> bytes:
        fmt = getattr(self._garmin, "ActivityDownloadFormat", None)
        original = getattr(fmt, "ORIGINAL", None)
        if original is None:
            raise RuntimeError("Garmin client missing ActivityDownloadFormat.ORIGINAL")
        return self._garmin.download_activity(activity_id, dl_fmt=original)

    def sync(self) -> GarminSyncResult:
        """Single entry point.

        - First run: backfill from today down to COURSESCOPE_GARMIN_BACKFILL_START_DATE.
        - Subsequent runs: incremental from cursor with a buffer.
        """

        run_id = str(uuid.uuid4())
        self._start_run(run_id)

        imported = 0
        skipped = 0

        try:
            cursor = self._get_cursor()
            if cursor is None:
                imported, skipped = self._sync_full_backfill()
            else:
                imported, skipped = self._sync_incremental(cursor)

            cursor_out = self._now_cursor_iso()
            self._set_cursor(cursor_out)
            self._finish_run(run_id, status="ok", imported=imported, skipped=skipped, error=None)
            return GarminSyncResult(
                run_id=run_id,
                status="ok",
                imported_count=imported,
                skipped_count=skipped,
                cursor_time_utc=cursor_out,
            )
        except Exception as exc:
            error = str(exc)
            self._finish_run(run_id, status="error", imported=imported, skipped=skipped, error=error)
            return GarminSyncResult(
                run_id=run_id,
                status="error",
                imported_count=imported,
                skipped_count=skipped,
                cursor_time_utc=None,
                error=error,
            )

    def _sync_incremental(self, cursor_time_utc: str) -> tuple[int, int]:
        # Buffer to tolerate clock drift / edited activities.
        buffer_days = int(os.getenv("COURSESCOPE_GARMIN_SYNC_BUFFER_DAYS", "2") or "2")
        try:
            cursor_dt = datetime.fromisoformat(cursor_time_utc.replace("Z", "+00:00"))
            cursor_date = cursor_dt.date()
        except Exception:
            cursor_date = date.today()

        start = max(_min_backfill_date(), cursor_date - timedelta(days=buffer_days))
        end = date.today()

        imported = 0
        skipped = 0
        for a, b in _chunk_ranges(start, end, chunk_days=28):
            items = self._list_activities(a, b)
            imp, sk = self._process_activity_list(items)
            imported += imp
            skipped += sk
        return imported, skipped

    def _sync_full_backfill(self) -> tuple[int, int]:
        min_date = _min_backfill_date()
        end = date.today()
        window_days = int(os.getenv("COURSESCOPE_GARMIN_BACKFILL_WINDOW_DAYS", "28") or "28")

        imported = 0
        skipped = 0

        while end >= min_date:
            start = max(min_date, end - timedelta(days=window_days - 1))
            items = self._list_activities(start, end)
            imp, sk = self._process_activity_list(items)
            imported += imp
            skipped += sk
            end = start - timedelta(days=1)

        return imported, skipped

    def _process_activity_list(self, activities: list[dict[str, Any]]) -> tuple[int, int]:
        imported = 0
        skipped = 0

        for activity in activities:
            raw_id = activity.get("activityId") or activity.get("activityUUID")
            if raw_id is None:
                continue
            activity_id = str(raw_id)

            if self._has_source_mapping(activity_id) is not None:
                skipped += 1
                continue

            original_bytes = self._download_original(activity_id)
            fit_bytes = _extract_fit_bytes(original_bytes)
            file_hash = _sha256_bytes(fit_bytes)

            existing_by_hash = self._get_activity_id_by_hash(file_hash)
            if existing_by_hash is not None:
                self._link_source(activity_id=existing_by_hash, source_activity_id=activity_id)
                skipped += 1
                continue

            display_name = activity.get("activityName") or f"Garmin Activity {activity_id}"
            filename = f"garmin_{activity_id}.fit"
            loaded = load_activity(data=fit_bytes, name=filename)
            stored_id = self._storage.store(loaded, filename, fit_bytes, name=display_name)
            self._link_source(activity_id=stored_id, source_activity_id=activity_id)
            imported += 1

        return imported, skipped
