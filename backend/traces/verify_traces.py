from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import get_traces_dir
from db.models import Trace
from db.trace_repository import TraceCreatePayload, TraceRepository
from services import activity_service
from storage.trace_store import compute_route_fingerprint, compute_trace_metrics


@dataclass(frozen=True)
class VerifyTracesResult:
    scanned: int
    indexed: int
    up_to_date: int
    deleted: int
    errors: int


def _find_original_file(trace_dir: Path) -> Path | None:
    for p in trace_dir.iterdir():
        if p.is_file() and p.name.startswith("original"):
            return p
    return None


def _load_df_from_dir(trace_dir: Path) -> pd.DataFrame:
    parquet_path = trace_dir / "df.parquet"
    if parquet_path.exists():
        return pd.read_parquet(parquet_path)

    original = _find_original_file(trace_dir)
    if original is None:
        raise FileNotFoundError(f"Missing original file for {trace_dir.name}")
    loaded = activity_service.load_activity_from_bytes(data=original.read_bytes(), name=original.name)
    if loaded.df is None:
        raise RuntimeError(f"No dataframe for trace {trace_dir.name}")
    loaded.df.to_parquet(parquet_path, engine="pyarrow")
    return loaded.df


def _dir_created_at_utc(trace_dir: Path) -> str:
    ts = trace_dir.stat().st_mtime
    return datetime.fromtimestamp(ts, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def verify_traces(session: Session, *, traces_dir: Path | None = None) -> VerifyTracesResult:
    base_dir = (traces_dir or get_traces_dir()).resolve()
    if not base_dir.exists():
        return VerifyTracesResult(scanned=0, indexed=0, up_to_date=0, deleted=0, errors=0)

    repo = TraceRepository()
    scanned = 0
    indexed = 0
    up_to_date = 0
    errors = 0
    seen_ids: set[str] = set()

    for trace_dir in base_dir.iterdir():
        if not trace_dir.is_dir():
            continue

        trace_id = trace_dir.name
        scanned += 1
        seen_ids.add(trace_id)

        try:
            original = _find_original_file(trace_dir)
            if original is None:
                raise FileNotFoundError(f"Missing original file for trace {trace_id}")
            meta_path = trace_dir / "meta.json"
            try:
                metadata = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
            except (OSError, json.JSONDecodeError):
                metadata = {}
            stored_hash = metadata.get("source_sha256") if isinstance(metadata, dict) else None
            file_hash = str(stored_hash) if stored_hash else hashlib.sha256(original.read_bytes()).hexdigest()
            df = _load_df_from_dir(trace_dir)
            metrics = compute_trace_metrics(df)
            route_fingerprint = compute_route_fingerprint(df)

            row = repo.get_by_id(session, trace_id)
            if row is None:
                repo.create_trace(
                    session,
                    TraceCreatePayload(
                        trace_id=trace_id,
                        name=None,
                        created_at_utc=_dir_created_at_utc(trace_dir),
                        file_hash_sha256=file_hash,
                        route_fingerprint=route_fingerprint,
                        distance_km=float(metrics["distance_km"] or 0.0),
                        elevation_gain_m=float(metrics["elevation_gain_m"] or 0.0),
                        elevation_loss_m=metrics["elevation_loss_m"],
                        elevation_min_m=metrics["elevation_min_m"],
                        elevation_max_m=metrics["elevation_max_m"],
                        original_filename=original.name,
                        original_path=str(original.resolve()),
                        parquet_path=str((trace_dir / "df.parquet").resolve()),
                        parquet_source_hash_sha256=file_hash,
                        dataframe_schema_version=metadata.get("dataframe_schema_version"),
                        parquet_generated_at_utc=metadata.get("generated_at_utc"),
                    ),
                )
                indexed += 1
            else:
                row.file_hash_sha256 = file_hash
                row.route_fingerprint = route_fingerprint
                row.distance_km = float(metrics["distance_km"] or 0.0)
                row.elevation_gain_m = float(metrics["elevation_gain_m"] or 0.0)
                row.elevation_loss_m = metrics["elevation_loss_m"]
                row.elevation_min_m = metrics["elevation_min_m"]
                row.elevation_max_m = metrics["elevation_max_m"]
                row.original_filename = original.name
                row.original_path = str(original.resolve())
                row.parquet_path = str((trace_dir / "df.parquet").resolve())
                row.parquet_source_hash_sha256 = file_hash
                row.dataframe_schema_version = metadata.get("dataframe_schema_version")
                row.parquet_generated_at_utc = metadata.get("generated_at_utc")
                up_to_date += 1
            session.commit()
        except Exception:
            errors += 1
            session.rollback()

    deleted = 0
    rows = list(session.execute(select(Trace)).scalars().all())
    for row in rows:
        if row.id in seen_ids:
            continue
        session.delete(row)
        deleted += 1

    session.commit()
    return VerifyTracesResult(scanned=scanned, indexed=indexed, up_to_date=up_to_date, deleted=deleted, errors=errors)
