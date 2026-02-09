from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
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
