from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import select
from sqlalchemy import delete
from sqlalchemy.orm import Session

from .models import Activity, ActivitySource, SyncRun, SyncState, utc_now_iso


@dataclass(frozen=True)
class SyncRunCounts:
    imported: int
    skipped: int


class ActivityIndexRepository:
    def get_activity_id_by_hash(self, session: Session, file_hash_sha256: str) -> str | None:
        stmt = select(Activity.id).where(Activity.file_hash_sha256 == file_hash_sha256)
        return session.execute(stmt).scalar_one_or_none()

    def get_activity_id_by_source(self, session: Session, source: str, source_activity_id: str) -> str | None:
        stmt = (
            select(ActivitySource.activity_id)
            .where(ActivitySource.source == source)
            .where(ActivitySource.source_activity_id == source_activity_id)
        )
        return session.execute(stmt).scalar_one_or_none()

    def link_source(self, session: Session, *, activity_id: str, source: str, source_activity_id: str) -> bool:
        existing = self.get_activity_id_by_source(session, source, source_activity_id)
        if existing is not None:
            return False
        session.add(ActivitySource(activity_id=activity_id, source=source, source_activity_id=source_activity_id))
        return True

    def create_activity(
        self,
        session: Session,
        *,
        activity_id: str,
        name: str | None,
        activity_type: str,
        started_at_utc: str | None,
        created_at_utc: str,
        file_hash_sha256: str,
        original_path: str,
        parquet_path: str,
    ) -> None:
        session.add(
            Activity(
                id=activity_id,
                name=name,
                activity_type=activity_type,
                started_at_utc=started_at_utc,
                created_at_utc=created_at_utc,
                file_hash_sha256=file_hash_sha256,
                original_path=original_path,
                parquet_path=parquet_path,
            )
        )

    def get_cursor(self, session: Session, source: str) -> str | None:
        stmt = select(SyncState.cursor_time_utc).where(SyncState.source == source)
        return session.execute(stmt).scalar_one_or_none()

    def set_cursor(self, session: Session, source: str, cursor_time_utc: str | None) -> None:
        row = session.get(SyncState, source)
        now = utc_now_iso()
        if row is None:
            session.add(SyncState(source=source, cursor_time_utc=cursor_time_utc, updated_at_utc=now))
        else:
            row.cursor_time_utc = cursor_time_utc
            row.updated_at_utc = now

    def start_sync_run(self, session: Session, *, run_id: str, source: str) -> None:
        session.add(
            SyncRun(
                id=run_id,
                source=source,
                started_at_utc=utc_now_iso(),
                finished_at_utc=None,
                status="running",
                imported_count=0,
                skipped_count=0,
                error=None,
            )
        )

    def finish_sync_run(
        self,
        session: Session,
        *,
        run_id: str,
        status: str,
        imported_count: int,
        skipped_count: int,
        error: str | None,
    ) -> None:
        row = session.get(SyncRun, run_id)
        if row is None:
            return
        row.finished_at_utc = utc_now_iso()
        row.status = status
        row.imported_count = int(imported_count)
        row.skipped_count = int(skipped_count)
        row.error = error

    def get_last_sync_run(self, session: Session, source: str) -> SyncRun | None:
        stmt = select(SyncRun).where(SyncRun.source == source).order_by(SyncRun.started_at_utc.desc()).limit(1)
        return session.execute(stmt).scalars().first()

    def delete_sync_state(self, session: Session, source: str) -> int:
        res = session.execute(delete(SyncState).where(SyncState.source == source))
        return int(res.rowcount or 0)

    def delete_activity_sources_by_source(self, session: Session, source: str) -> int:
        res = session.execute(delete(ActivitySource).where(ActivitySource.source == source))
        return int(res.rowcount or 0)

    def delete_all_activities(self, session: Session) -> int:
        # Delete sources first to avoid FK issues.
        session.execute(delete(ActivitySource))
        res = session.execute(delete(Activity))
        return int(res.rowcount or 0)
