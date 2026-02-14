from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .models import ProgressActivityIndex, ProgressBestEffortPoint


@dataclass(frozen=True)
class ProgressSeriesRow:
    start_ts_utc: str
    value: float | None


class ProgressRepository:
    def get_activity_index(self, session: Session, activity_id: str) -> ProgressActivityIndex | None:
        return session.get(ProgressActivityIndex, activity_id)

    def upsert_activity_index(self, session: Session, row: ProgressActivityIndex) -> None:
        existing = session.get(ProgressActivityIndex, row.activity_id)
        if existing is None:
            session.add(row)
            return

        # Fast path: avoid rewriting rows that are up-to-date.
        if existing.fingerprint == row.fingerprint and existing.metrics_version == row.metrics_version:
            return

        for key, value in row.__dict__.items():
            if key.startswith("_"):
                continue
            setattr(existing, key, value)

    def replace_best_efforts(
        self,
        session: Session,
        *,
        activity_id: str,
        effort_kind: str,
        points: Iterable[ProgressBestEffortPoint],
    ) -> None:
        session.execute(
            delete(ProgressBestEffortPoint)
            .where(ProgressBestEffortPoint.activity_id == activity_id)
            .where(ProgressBestEffortPoint.effort_kind == effort_kind)
        )
        for p in points:
            session.add(p)

    def list_activity_rows(
        self,
        session: Session,
        *,
        from_ts_utc: str | None,
        to_ts_utc: str | None,
        activity_type: str | None,
        limit: int | None,
    ) -> list[ProgressActivityIndex]:
        stmt = select(ProgressActivityIndex)
        if from_ts_utc is not None:
            stmt = stmt.where(ProgressActivityIndex.start_ts_utc >= from_ts_utc)
        if to_ts_utc is not None:
            stmt = stmt.where(ProgressActivityIndex.start_ts_utc <= to_ts_utc)
        if activity_type is not None:
            stmt = stmt.where(ProgressActivityIndex.activity_type == activity_type)
        stmt = stmt.order_by(ProgressActivityIndex.start_ts_utc.asc())
        if limit is not None and int(limit) > 0:
            stmt = stmt.limit(int(limit))
        return list(session.execute(stmt).scalars().all())

    def list_series_rows(
        self,
        session: Session,
        *,
        metric: str,
        from_ts_utc: str | None,
        to_ts_utc: str | None,
        activity_type: str | None,
    ) -> list[ProgressSeriesRow]:
        col = getattr(ProgressActivityIndex, metric)
        stmt = select(ProgressActivityIndex.start_ts_utc, col)
        if from_ts_utc is not None:
            stmt = stmt.where(ProgressActivityIndex.start_ts_utc >= from_ts_utc)
        if to_ts_utc is not None:
            stmt = stmt.where(ProgressActivityIndex.start_ts_utc <= to_ts_utc)
        if activity_type is not None:
            stmt = stmt.where(ProgressActivityIndex.activity_type == activity_type)
        stmt = stmt.order_by(ProgressActivityIndex.start_ts_utc.asc())
        rows = session.execute(stmt).all()
        out: list[ProgressSeriesRow] = []
        for start_ts_utc, value in rows:
            out.append(ProgressSeriesRow(start_ts_utc=str(start_ts_utc), value=value))
        return out

    def list_best_effort_points(
        self,
        session: Session,
        *,
        effort_kind: str,
        duration_s: int,
        from_ts_utc: str | None,
        to_ts_utc: str | None,
    ) -> list[ProgressBestEffortPoint]:
        stmt = (
            select(ProgressBestEffortPoint)
            .where(ProgressBestEffortPoint.effort_kind == effort_kind)
            .where(ProgressBestEffortPoint.duration_s == int(duration_s))
        )
        if from_ts_utc is not None:
            stmt = stmt.where(ProgressBestEffortPoint.start_ts_utc >= from_ts_utc)
        if to_ts_utc is not None:
            stmt = stmt.where(ProgressBestEffortPoint.start_ts_utc <= to_ts_utc)
        stmt = stmt.order_by(ProgressBestEffortPoint.start_ts_utc.asc())
        return list(session.execute(stmt).scalars().all())
