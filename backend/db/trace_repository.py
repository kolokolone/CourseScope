from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Trace


@dataclass(frozen=True)
class TraceCreatePayload:
    trace_id: str
    name: str | None
    created_at_utc: str
    file_hash_sha256: str
    route_fingerprint: str | None
    distance_km: float
    elevation_gain_m: float
    elevation_loss_m: float | None
    elevation_min_m: float | None
    elevation_max_m: float | None
    original_filename: str | None
    original_path: str
    parquet_path: str | None = None
    parquet_source_hash_sha256: str | None = None
    dataframe_schema_version: str | None = None
    parquet_generated_at_utc: str | None = None


class TraceRepository:
    def get_by_id(self, session: Session, trace_id: str) -> Trace | None:
        return session.get(Trace, trace_id)

    def get_by_file_hash(self, session: Session, file_hash_sha256: str) -> Trace | None:
        stmt = select(Trace).where(Trace.file_hash_sha256 == file_hash_sha256)
        return session.execute(stmt).scalars().first()

    def get_by_route_fingerprint(self, session: Session, route_fingerprint: str) -> Trace | None:
        stmt = select(Trace).where(Trace.route_fingerprint == route_fingerprint)
        return session.execute(stmt).scalars().first()

    def list_traces(self, session: Session) -> list[Trace]:
        stmt = select(Trace).order_by(Trace.created_at_utc.desc())
        return list(session.execute(stmt).scalars().all())

    def create_trace(self, session: Session, payload: TraceCreatePayload) -> Trace:
        row = Trace(
            id=payload.trace_id,
            name=payload.name,
            created_at_utc=payload.created_at_utc,
            file_hash_sha256=payload.file_hash_sha256,
            route_fingerprint=payload.route_fingerprint,
            distance_km=float(payload.distance_km),
            elevation_gain_m=float(payload.elevation_gain_m),
            elevation_loss_m=payload.elevation_loss_m,
            elevation_min_m=payload.elevation_min_m,
            elevation_max_m=payload.elevation_max_m,
            original_filename=payload.original_filename,
            original_path=payload.original_path,
            parquet_path=payload.parquet_path,
            parquet_source_hash_sha256=payload.parquet_source_hash_sha256,
            dataframe_schema_version=payload.dataframe_schema_version,
            parquet_generated_at_utc=payload.parquet_generated_at_utc,
        )
        session.add(row)
        return row

    def rename_trace(self, session: Session, trace_id: str, name: str | None) -> bool:
        row = session.get(Trace, trace_id)
        if row is None:
            return False
        row.name = name
        return True

    def delete_trace(self, session: Session, trace_id: str) -> bool:
        row = session.get(Trace, trace_id)
        if row is None:
            return False
        session.delete(row)
        return True

    def update_parquet_metadata(
        self,
        session: Session,
        trace_id: str,
        *,
        parquet_path: str,
        source_hash_sha256: str,
        dataframe_schema_version: str,
        generated_at_utc: str,
    ) -> None:
        row = session.get(Trace, trace_id)
        if row is None:
            return
        row.parquet_path = parquet_path
        row.parquet_source_hash_sha256 = source_hash_sha256
        row.dataframe_schema_version = dataframe_schema_version
        row.parquet_generated_at_utc = generated_at_utc
