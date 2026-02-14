from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Float, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    activity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at_utc: Mapped[str] = mapped_column(Text, nullable=False)
    file_hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    original_path: Mapped[str] = mapped_column(Text, nullable=False)
    parquet_path: Mapped[str] = mapped_column(Text, nullable=False)

    # Progression index trace (computed artifacts).
    progress_indexed_at_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    progress_rollup_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    sources: Mapped[list["ActivitySource"]] = relationship(
        back_populates="activity",
        cascade="all, delete-orphan",
    )


class ActivitySource(Base):
    __tablename__ = "activity_sources"
    __table_args__ = (
        UniqueConstraint("source", "source_activity_id", name="uq_activity_source_external"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    activity_id: Mapped[str] = mapped_column(String(36), ForeignKey("activities.id"), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    source_activity_id: Mapped[str] = mapped_column(Text, nullable=False)

    activity: Mapped[Activity] = relationship(back_populates="sources")


class SyncState(Base):
    __tablename__ = "sync_state"

    source: Mapped[str] = mapped_column(String(32), primary_key=True)
    cursor_time_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at_utc: Mapped[str] = mapped_column(Text, nullable=False)


class SyncRun(Base):
    __tablename__ = "sync_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at_utc: Mapped[str] = mapped_column(Text, nullable=False)
    finished_at_utc: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    imported_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


class ProgressActivityIndex(Base):
    __tablename__ = "progress_activity_index"

    activity_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    activity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    start_ts_utc: Mapped[str] = mapped_column(Text, nullable=False)
    local_date: Mapped[str | None] = mapped_column(Text, nullable=True)
    tz: Mapped[str | None] = mapped_column(Text, nullable=True)

    fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    metrics_version: Mapped[int] = mapped_column(Integer, nullable=False)
    indexed_at_ts: Mapped[str] = mapped_column(Text, nullable=False)

    distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    moving_time_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    elapsed_time_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    elevation_gain_m: Mapped[float | None] = mapped_column(Float, nullable=True)

    avg_pace_s_per_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    best_pace_s_per_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    pace_threshold_s_per_km: Mapped[float | None] = mapped_column(Float, nullable=True)

    avg_hr_bpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_hr_bpm: Mapped[float | None] = mapped_column(Float, nullable=True)

    trimp: Mapped[float | None] = mapped_column(Float, nullable=True)
    training_load_method: Mapped[str | None] = mapped_column(Text, nullable=True)

    decoupling_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    cardiac_drift_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    stability_cv: Mapped[float | None] = mapped_column(Float, nullable=True)
    stability_iqr_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)

    aerobic_efficiency_m_s_per_bpm: Mapped[float | None] = mapped_column(Float, nullable=True)

    has_hr: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    has_power: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    has_cadence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    data_points: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_progress_activity_start_ts", "start_ts_utc"),
        Index("ix_progress_activity_type_start_ts", "activity_type", "start_ts_utc"),
    )


class ProgressBestEffortPoint(Base):
    __tablename__ = "progress_best_effort_points"
    __table_args__ = (
        UniqueConstraint("activity_id", "effort_kind", "duration_s", name="uq_progress_best_effort"),
        Index("ix_progress_best_effort_kind_duration", "effort_kind", "duration_s"),
        Index("ix_progress_best_effort_kind_duration_start", "effort_kind", "duration_s", "start_ts_utc"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    activity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    start_ts_utc: Mapped[str] = mapped_column(Text, nullable=False)
    effort_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    duration_s: Mapped[int] = mapped_column(Integer, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
