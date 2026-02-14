from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .models import ProgressActivityIndex, ProgressActivityTag, ProgressBestEffortPoint, ProgressPaceHrBin


@dataclass(frozen=True)
class ProgressSeriesRow:
    start_ts_utc: str
    value: float | None


@dataclass(frozen=True)
class ProgressPaceHrRow:
    activity_id: str
    start_ts_utc: str
    pace_bin_s_per_km: float
    time_s_bin: float
    hr_mean_w_bpm: float | None
    hr_q50_w_bpm: float | None


@dataclass(frozen=True)
class ProgressActivityTagRow:
    activity_id: str
    session_tag: str | None
    terrain_tag: str | None
    race_marker: bool
    source: str
    updated_at_ts: str


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

    def replace_pace_hr_bins(
        self,
        session: Session,
        *,
        activity_id: str,
        bins: Iterable[ProgressPaceHrBin],
    ) -> None:
        session.execute(
            delete(ProgressPaceHrBin)
            .where(ProgressPaceHrBin.activity_id == activity_id)
        )
        for row in bins:
            session.add(row)

    def upsert_activity_tag(
        self,
        session: Session,
        *,
        row: ProgressActivityTag,
        preserve_manual: bool,
    ) -> None:
        existing = session.get(ProgressActivityTag, row.activity_id)
        if existing is None:
            session.add(row)
            return

        if preserve_manual and existing.source == "manual":
            return

        existing.session_tag = row.session_tag
        existing.terrain_tag = row.terrain_tag
        existing.race_marker = row.race_marker
        existing.source = row.source
        existing.updated_at_ts = row.updated_at_ts

    def get_activity_tags_map(
        self,
        session: Session,
        *,
        activity_ids: list[str],
    ) -> dict[str, ProgressActivityTagRow]:
        if not activity_ids:
            return {}
        stmt = select(ProgressActivityTag).where(ProgressActivityTag.activity_id.in_(activity_ids))
        rows = list(session.execute(stmt).scalars().all())
        out: dict[str, ProgressActivityTagRow] = {}
        for r in rows:
            out[str(r.activity_id)] = ProgressActivityTagRow(
                activity_id=str(r.activity_id),
                session_tag=(str(r.session_tag) if r.session_tag else None),
                terrain_tag=(str(r.terrain_tag) if r.terrain_tag else None),
                race_marker=bool(r.race_marker),
                source=str(r.source),
                updated_at_ts=str(r.updated_at_ts),
            )
        return out

    def list_activity_tag_rows(
        self,
        session: Session,
        *,
        from_ts_utc: str | None,
        to_ts_utc: str | None,
        activity_type: str | None,
    ) -> list[ProgressActivityTagRow]:
        stmt = (
            select(
                ProgressActivityTag.activity_id,
                ProgressActivityTag.session_tag,
                ProgressActivityTag.terrain_tag,
                ProgressActivityTag.race_marker,
                ProgressActivityTag.source,
                ProgressActivityTag.updated_at_ts,
            )
            .select_from(ProgressActivityTag)
            .join(ProgressActivityIndex, ProgressActivityIndex.activity_id == ProgressActivityTag.activity_id)
        )
        if from_ts_utc is not None:
            stmt = stmt.where(ProgressActivityIndex.start_ts_utc >= from_ts_utc)
        if to_ts_utc is not None:
            stmt = stmt.where(ProgressActivityIndex.start_ts_utc <= to_ts_utc)
        if activity_type is not None:
            stmt = stmt.where(ProgressActivityIndex.activity_type == activity_type)
        stmt = stmt.order_by(ProgressActivityIndex.start_ts_utc.asc())
        rows = session.execute(stmt).all()
        out: list[ProgressActivityTagRow] = []
        for activity_id, session_tag, terrain_tag, race_marker, source, updated_at_ts in rows:
            out.append(
                ProgressActivityTagRow(
                    activity_id=str(activity_id),
                    session_tag=(str(session_tag) if session_tag else None),
                    terrain_tag=(str(terrain_tag) if terrain_tag else None),
                    race_marker=bool(race_marker),
                    source=str(source),
                    updated_at_ts=str(updated_at_ts),
                )
            )
        return out

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

    def list_pace_hr_rows(
        self,
        session: Session,
        *,
        from_ts_utc: str | None,
        to_ts_utc: str | None,
        activity_type: str | None,
        session_tag: str | None = None,
        terrain_tag: str | None = None,
        endurance_only: bool = False,
    ) -> list[ProgressPaceHrRow]:
        stmt = select(
            ProgressPaceHrBin.activity_id,
            ProgressPaceHrBin.start_ts_utc,
            ProgressPaceHrBin.pace_bin_s_per_km,
            ProgressPaceHrBin.time_s_bin,
            ProgressPaceHrBin.hr_mean_w_bpm,
            ProgressPaceHrBin.hr_q50_w_bpm,
        ).select_from(ProgressPaceHrBin)

        if session_tag is not None or terrain_tag is not None or endurance_only:
            stmt = stmt.join(ProgressActivityTag, ProgressActivityTag.activity_id == ProgressPaceHrBin.activity_id)
            if session_tag is not None:
                stmt = stmt.where(ProgressActivityTag.session_tag == session_tag)
            if terrain_tag is not None:
                stmt = stmt.where(ProgressActivityTag.terrain_tag == terrain_tag)
            if endurance_only:
                stmt = stmt.where(ProgressActivityTag.session_tag.in_(["easy", "long_run"]))

        if from_ts_utc is not None:
            stmt = stmt.where(ProgressPaceHrBin.start_ts_utc >= from_ts_utc)
        if to_ts_utc is not None:
            stmt = stmt.where(ProgressPaceHrBin.start_ts_utc <= to_ts_utc)
        if activity_type is not None:
            stmt = stmt.where(ProgressPaceHrBin.activity_type == activity_type)
        stmt = stmt.order_by(
            ProgressPaceHrBin.start_ts_utc.asc(),
            ProgressPaceHrBin.pace_bin_s_per_km.asc(),
        )
        rows = session.execute(stmt).all()
        out: list[ProgressPaceHrRow] = []
        for activity_id, start_ts_utc, pace_bin_s_per_km, time_s_bin, hr_mean_w_bpm, hr_q50_w_bpm in rows:
            out.append(
                ProgressPaceHrRow(
                    activity_id=str(activity_id),
                    start_ts_utc=str(start_ts_utc),
                    pace_bin_s_per_km=float(pace_bin_s_per_km),
                    time_s_bin=float(time_s_bin),
                    hr_mean_w_bpm=(float(hr_mean_w_bpm) if hr_mean_w_bpm is not None else None),
                    hr_q50_w_bpm=(float(hr_q50_w_bpm) if hr_q50_w_bpm is not None else None),
                )
            )
        return out
