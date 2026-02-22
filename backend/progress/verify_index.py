from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from config import get_activities_dir
from core.fit_loader import fit_to_dataframe, load_fit
from db.models import (
    Activity,
    ActivitySource,
    ProgressActivityIndex,
    ProgressActivityTag,
    ProgressBestEffortPoint,
    ProgressPaceHrBin,
    UserSettings,
    utc_now_iso,
)
from progress.indexer import METRICS_VERSION, build_fingerprint, index_activity


logger = logging.getLogger("coursescope")


@dataclass(frozen=True)
class VerifyProgressResult:
    scanned: int
    indexed: int
    up_to_date: int
    errors: int


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_iso(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc).replace(microsecond=0)
    return dt.isoformat().replace("+00:00", "Z")


def _find_original_path(activity_dir: Path) -> str | None:
    try:
        for p in activity_dir.iterdir():
            if p.is_file() and p.name.startswith("original."):
                return str(p.resolve())
    except Exception:
        return None
    return None


def _find_original_fit_path(activity_dir: Path) -> Path | None:
    try:
        for p in activity_dir.iterdir():
            if not p.is_file():
                continue
            name = p.name.lower()
            if name.startswith("original.") and name.endswith(".fit"):
                return p
    except Exception:
        return None
    return None


def _extract_vo2max_from_df(df: pd.DataFrame) -> float | None:
    if "vo2max" not in df.columns:
        return None
    values = pd.to_numeric(df["vo2max"], errors="coerce").dropna()
    if values.empty:
        return None
    value = float(values.iloc[-1])
    if not math.isfinite(value):
        return None
    if value < 10.0 or value > 95.0:
        return None
    return value


def _write_rollup(activity_dir: Path, payload: dict) -> str:
    rollup_path = activity_dir / "progress_rollup.json"
    rollup_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return str(rollup_path.resolve())


def _maybe_backfill_vo2max_from_fit(activity_dir: Path, parquet_path: Path, df: pd.DataFrame) -> pd.DataFrame:
    fit_path = _find_original_fit_path(activity_dir)
    if fit_path is None or not fit_path.exists():
        return df

    try:
        with fit_path.open("rb") as fh:
            fit_df = fit_to_dataframe(load_fit(fh))
        fit_vo2 = _extract_vo2max_from_df(fit_df)
        if fit_vo2 is None:
            return df
        try:
            fit_df.to_parquet(parquet_path, engine="pyarrow")
        except Exception:
            pass
        return fit_df
    except Exception:
        return df


def _sync_vo2max_latest_from_index(session: Session) -> None:
    latest_stmt = (
        select(ProgressActivityIndex.vo2max)
        .where(ProgressActivityIndex.vo2max.is_not(None))
        .order_by(ProgressActivityIndex.start_ts_utc.desc())
        .limit(1)
    )
    latest_vo2 = session.execute(latest_stmt).scalar_one_or_none()
    latest_value = float(latest_vo2) if latest_vo2 is not None else None

    settings = session.get(UserSettings, 1)
    if settings is None:
        settings = UserSettings(
            id=1,
            vma_kmh=None,
            vo2max_lastest=latest_value,
            hr_max_manual_bpm=None,
            hr_max_source="detected",
            updated_at_utc=utc_now_iso(),
        )
        session.add(settings)
        return

    if settings.vo2max_lastest != latest_value:
        settings.vo2max_lastest = latest_value
        settings.updated_at_utc = utc_now_iso()


def _purge_missing_activities(session: Session, *, keep_activity_ids: set[str]) -> int:
    candidates: set[str] = set()

    id_queries = (
        select(Activity.id),
        select(ActivitySource.activity_id),
        select(ProgressActivityIndex.activity_id),
        select(ProgressActivityTag.activity_id),
        select(ProgressBestEffortPoint.activity_id),
        select(ProgressPaceHrBin.activity_id),
    )
    for stmt in id_queries:
        for value in session.execute(stmt).scalars().all():
            if value is None:
                continue
            candidates.add(str(value))

    stale_ids = sorted(candidates - keep_activity_ids)
    if not stale_ids:
        return 0

    deleted = 0
    delete_statements = (
        delete(ProgressBestEffortPoint).where(ProgressBestEffortPoint.activity_id.in_(stale_ids)),
        delete(ProgressPaceHrBin).where(ProgressPaceHrBin.activity_id.in_(stale_ids)),
        delete(ProgressActivityTag).where(ProgressActivityTag.activity_id.in_(stale_ids)),
        delete(ProgressActivityIndex).where(ProgressActivityIndex.activity_id.in_(stale_ids)),
        delete(ActivitySource).where(ActivitySource.activity_id.in_(stale_ids)),
        delete(Activity).where(Activity.id.in_(stale_ids)),
    )
    for stmt in delete_statements:
        res = session.execute(stmt)
        deleted += int(getattr(res, "rowcount", 0) or 0)

    return deleted


def verify_progress_index(
    session: Session,
    *,
    activities_dir: Path | None = None,
    commit_every: int = 25,
) -> VerifyProgressResult:
    base_dir = (activities_dir or get_activities_dir()).resolve()
    if not base_dir.exists():
        return VerifyProgressResult(scanned=0, indexed=0, up_to_date=0, errors=0)

    scanned = 0
    indexed = 0
    up_to_date = 0
    errors = 0
    existing_activity_ids: set[str] = set()

    for activity_dir in base_dir.iterdir():
        if not activity_dir.is_dir():
            continue

        activity_id = activity_dir.name
        meta_path = activity_dir / "meta.json"
        parquet_path = activity_dir / "df.parquet"
        if not meta_path.exists() or not parquet_path.exists():
            continue

        existing_activity_ids.add(activity_id)

        scanned += 1
        try:
            meta = _read_json(meta_path)
            fingerprint = build_fingerprint(meta, parquet_path)

            row = session.get(ProgressActivityIndex, activity_id)
            is_current = (
                row is not None
                and row.fingerprint == fingerprint
                and int(row.metrics_version) == int(METRICS_VERSION)
            )

            needs_reindex = bool(not is_current or (row is not None and row.vo2max is None))

            if needs_reindex:
                df = pd.read_parquet(parquet_path)
                df = _maybe_backfill_vo2max_from_fit(activity_dir, parquet_path, df)

                index_activity(
                    session,
                    activity_id=activity_id,
                    df=df,
                    meta=meta,
                    parquet_path=parquet_path,
                )
                indexed += 1
                row = session.get(ProgressActivityIndex, activity_id)
            else:
                up_to_date += 1

            # Ensure an Activity row exists so we can trace the computed file path.
            act = session.get(Activity, activity_id)
            if act is None:
                original_path = _find_original_path(activity_dir) or str((activity_dir / "original.unknown").resolve())
                started = _parse_iso(meta.get("started_at"))
                created = _parse_iso(meta.get("created_at")) or utc_now_iso()
                act = Activity(
                    id=activity_id,
                    name=meta.get("name"),
                    activity_type=str(meta.get("activity_type") or "real"),
                    started_at_utc=started,
                    created_at_utc=created,
                    file_hash_sha256=str(meta.get("file_hash") or f"missing:{activity_id}"),
                    original_path=str(original_path),
                    parquet_path=str(parquet_path.resolve()),
                )
                session.add(act)

            # Write a rollup file (computed artifact) and store its path in activities.
            if row is not None:
                payload = {
                    "activity_id": activity_id,
                    "fingerprint": row.fingerprint,
                    "metrics_version": int(row.metrics_version),
                    "indexed_at_ts": row.indexed_at_ts,
                    "start_ts_utc": row.start_ts_utc,
                    "activity_type": row.activity_type,
                    "distance_m": row.distance_m,
                    "moving_time_s": row.moving_time_s,
                    "elevation_gain_m": row.elevation_gain_m,
                    "trimp": row.trimp,
                    "aerobic_efficiency_m_s_per_bpm": row.aerobic_efficiency_m_s_per_bpm,
                    "decoupling_pct": row.decoupling_pct,
                }
            else:
                payload = {
                    "activity_id": activity_id,
                    "fingerprint": fingerprint,
                    "metrics_version": int(METRICS_VERSION),
                    "indexed_at_ts": utc_now_iso(),
                }

            rollup_path = _write_rollup(activity_dir, payload)
            act.progress_rollup_path = rollup_path
            act.progress_indexed_at_utc = utc_now_iso()

            if commit_every and scanned % int(commit_every) == 0:
                session.commit()
        except Exception as exc:
            errors += 1
            logger.warning(
                "progress_verify_failed",
                extra={"request_id": "-", "activity_id": activity_id, "error": str(exc)},
            )
            try:
                session.rollback()
            except Exception:
                pass

    deleted = _purge_missing_activities(session, keep_activity_ids=existing_activity_ids)
    if deleted > 0:
        logger.info(
            "progress_verify_deleted_orphans",
            extra={"request_id": "-", "deleted_rows": int(deleted)},
        )

    _sync_vo2max_latest_from_index(session)
    session.commit()
    return VerifyProgressResult(scanned=scanned, indexed=indexed, up_to_date=up_to_date, errors=errors)
