from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from config import get_activities_dir
from db.models import (
    Activity,
    ActivitySource,
    ProgressActivityIndex,
    ProgressActivityTag,
    ProgressBestEffortPoint,
    ProgressIndexationRun,
    ProgressPaceHrBin,
    utc_now_iso,
)
from progress.indexer import METRICS_VERSION, build_fingerprint, index_activity
from progress.verify_index import _maybe_backfill_vo2max_from_fit, _sync_vo2max_latest_from_index
from sqlalchemy.exc import OperationalError


logger = logging.getLogger("coursescope")

PHASE_PREPARE = "prepare"
PHASE_SCAN_FS = "scan_fs"
PHASE_SYNC_DB = "sync_db"
PHASE_RECOMPUTE = "recompute"
PHASE_FINALIZE = "finalize"

MODE_FAST = "fast"
MODE_SLOW = "slow"

SLOW_STRATEGIES = {"incremental", "backfill_missing", "backfill_full"}

DEFAULT_INDEXATION_TIMEOUT_S = 30 * 60
DEFAULT_RETRY_ATTEMPTS = 5
DEFAULT_RETRY_BASE_DELAY_S = 0.05


@dataclass(frozen=True)
class IndexationResult:
    scanned: int = 0
    added: int = 0
    deleted: int = 0
    indexed: int = 0
    up_to_date: int = 0
    errors: int = 0
    skipped: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "scanned": int(self.scanned),
            "added": int(self.added),
            "deleted": int(self.deleted),
            "indexed": int(self.indexed),
            "up_to_date": int(self.up_to_date),
            "errors": int(self.errors),
            "skipped": int(self.skipped),
        }


@dataclass
class IndexationState:
    running: bool = False
    mode: str | None = None
    phase: str | None = None
    started_at_utc: str | None = None
    finished_at_utc: str | None = None
    progress_current: int = 0
    progress_total: int = 0
    last_error: str | None = None
    last_result: IndexationResult | None = None


_lock = threading.Lock()
_thread: threading.Thread | None = None
_state = IndexationState()


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _snapshot_state_unlocked() -> IndexationState:
    return IndexationState(
        running=bool(_state.running),
        mode=_state.mode,
        phase=_state.phase,
        started_at_utc=_state.started_at_utc,
        finished_at_utc=_state.finished_at_utc,
        progress_current=int(_state.progress_current),
        progress_total=int(_state.progress_total),
        last_error=_state.last_error,
        last_result=_state.last_result,
    )


def get_indexation_state() -> IndexationState:
    with _lock:
        return _snapshot_state_unlocked()


def _set_phase(mode: str, phase: str, *, progress_current: int, progress_total: int) -> None:
    with _lock:
        _state.mode = mode
        _state.phase = phase
        _state.progress_current = int(progress_current)
        _state.progress_total = int(progress_total)


def _set_progress(progress_current: int, progress_total: int) -> None:
    with _lock:
        _state.progress_current = int(progress_current)
        _state.progress_total = int(progress_total)


def _safe_int_env(name: str, default: int) -> int:
    try:
        raw = os.getenv(name)
        if raw is None:
            return int(default)
        value = int(str(raw).strip())
        return value if value > 0 else int(default)
    except Exception:
        return int(default)


def _safe_float_env(name: str, default: float) -> float:
    try:
        raw = os.getenv(name)
        if raw is None:
            return float(default)
        value = float(str(raw).strip())
        return value if value > 0 else float(default)
    except Exception:
        return float(default)


def _indexation_timeout_s() -> float:
    return _safe_float_env("COURSESCOPE_INDEXATION_TIMEOUT_S", float(DEFAULT_INDEXATION_TIMEOUT_S))


def _retry_attempts() -> int:
    return _safe_int_env("COURSESCOPE_DB_RETRY_ATTEMPTS", int(DEFAULT_RETRY_ATTEMPTS))


def _retry_base_delay_s() -> float:
    return _safe_float_env("COURSESCOPE_DB_RETRY_BASE_DELAY_S", float(DEFAULT_RETRY_BASE_DELAY_S))


def _is_sqlite_busy_error(exc: Exception) -> bool:
    raw = str(exc).lower()
    return "database is locked" in raw or "sqlite_busy" in raw or "database table is locked" in raw


def _rollback_quiet(session: Session) -> None:
    try:
        session.rollback()
    except Exception:
        pass


def _commit_with_retry(session: Session) -> None:
    attempts = max(1, int(_retry_attempts()))
    base_delay_s = max(0.001, float(_retry_base_delay_s()))
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            session.commit()
            return
        except OperationalError as exc:
            if not _is_sqlite_busy_error(exc):
                _rollback_quiet(session)
                raise
            _rollback_quiet(session)
            last_exc = exc
            if attempt >= attempts:
                break
            time.sleep(base_delay_s * float(2 ** (attempt - 1)))
        except Exception:
            _rollback_quiet(session)
            raise
    if last_exc is not None:
        raise last_exc


def _check_deadline(deadline_ts: float) -> None:
    if time.monotonic() > float(deadline_ts):
        raise TimeoutError("indexation timeout reached")


def _create_run_record(
    db_session_factory,
    *,
    mode: str,
    strategy: str | None,
    reason: str,
) -> str:
    run_id = str(uuid.uuid4())
    session = db_session_factory()
    try:
        session.add(
            ProgressIndexationRun(
                id=run_id,
                mode=mode,
                strategy=(str(strategy) if strategy is not None else None),
                reason=str(reason or "manual"),
                status="running",
                started_at_utc=utc_now_iso(),
                finished_at_utc=None,
                duration_ms=0,
                progress_total=0,
                progress_done=0,
                result_json=None,
                error=None,
            )
        )
        _commit_with_retry(session)
    finally:
        session.close()
    return run_id


def _finalize_run_record(
    db_session_factory,
    *,
    run_id: str | None,
    status: str,
    result: IndexationResult | None,
    error: str | None,
    progress_total: int,
    progress_done: int,
    started_monotonic: float,
) -> None:
    if not run_id:
        return

    session = db_session_factory()
    try:
        row = session.get(ProgressIndexationRun, run_id)
        if row is None:
            return
        duration_ms = max(0, int((time.monotonic() - float(started_monotonic)) * 1000.0))
        row.status = str(status)
        row.finished_at_utc = utc_now_iso()
        row.duration_ms = int(duration_ms)
        row.progress_total = int(max(0, progress_total))
        row.progress_done = int(max(0, progress_done))
        row.error = str(error) if error else None
        row.result_json = json.dumps(result.to_dict(), ensure_ascii=True) if result is not None else None
        _commit_with_retry(session)
    finally:
        session.close()


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


def _write_rollup(activity_dir: Path, payload: dict) -> str:
    rollup_path = activity_dir / "progress_rollup.json"
    rollup_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return str(rollup_path.resolve())


def _delete_related_rows_for_activity_ids(session: Session, activity_ids: list[str]) -> int:
    if not activity_ids:
        return 0
    deleted_rows = 0
    delete_statements = (
        delete(ProgressBestEffortPoint).where(ProgressBestEffortPoint.activity_id.in_(activity_ids)),
        delete(ProgressPaceHrBin).where(ProgressPaceHrBin.activity_id.in_(activity_ids)),
        delete(ProgressActivityTag).where(ProgressActivityTag.activity_id.in_(activity_ids)),
        delete(ProgressActivityIndex).where(ProgressActivityIndex.activity_id.in_(activity_ids)),
        delete(ActivitySource).where(ActivitySource.activity_id.in_(activity_ids)),
        delete(Activity).where(Activity.id.in_(activity_ids)),
    )
    for stmt in delete_statements:
        res = session.execute(stmt)
        deleted_rows += int(getattr(res, "rowcount", 0) or 0)
    return deleted_rows


def _combine_results(first: IndexationResult, second: IndexationResult) -> IndexationResult:
    return IndexationResult(
        scanned=int(first.scanned) + int(second.scanned),
        added=int(first.added) + int(second.added),
        deleted=int(first.deleted) + int(second.deleted),
        indexed=int(first.indexed) + int(second.indexed),
        up_to_date=int(first.up_to_date) + int(second.up_to_date),
        errors=int(first.errors) + int(second.errors),
        skipped=int(first.skipped) + int(second.skipped),
    )


def _run_fast_indexation_once(
    session: Session,
    *,
    activities_dir: Path,
    deadline_ts: float,
    commit_every: int = 50,
) -> tuple[IndexationResult, bool]:
    scanned = 0
    added = 0
    deleted = 0
    errors = 0

    _set_phase(MODE_FAST, PHASE_SCAN_FS, progress_current=0, progress_total=0)
    activities_dir.mkdir(parents=True, exist_ok=True)
    fs_ids: set[str] = set()
    activity_dirs: dict[str, Path] = {}
    for activity_dir in activities_dir.iterdir():
        _check_deadline(deadline_ts)
        if not activity_dir.is_dir():
            continue
        meta_path = activity_dir / "meta.json"
        parquet_path = activity_dir / "df.parquet"
        if not meta_path.exists() or not parquet_path.exists():
            continue
        scanned += 1
        activity_id = str(activity_dir.name)
        fs_ids.add(activity_id)
        activity_dirs[activity_id] = activity_dir

    _set_phase(MODE_FAST, PHASE_SYNC_DB, progress_current=0, progress_total=max(1, scanned))
    db_ids = {str(v) for v in session.execute(select(Activity.id)).scalars().all() if v is not None}
    missing_on_disk = sorted(db_ids - fs_ids)
    missing_in_db = sorted(fs_ids - db_ids)

    if missing_on_disk:
        _delete_related_rows_for_activity_ids(session, missing_on_disk)
        deleted = len(missing_on_disk)

    commit_mod = int(commit_every) if int(commit_every) > 0 else 0
    created_since_commit = 0
    for idx, activity_id in enumerate(missing_in_db, start=1):
        _check_deadline(deadline_ts)
        activity_dir = activity_dirs.get(activity_id)
        if activity_dir is None:
            errors += 1
            continue
        try:
            meta = _read_json(activity_dir / "meta.json")
            parquet_path = activity_dir / "df.parquet"
            original_path = _find_original_path(activity_dir) or str((activity_dir / "original.unknown").resolve())
            started = _parse_iso(meta.get("started_at"))
            created = _parse_iso(meta.get("created_at")) or utc_now_iso()
            file_hash = str(meta.get("file_hash") or f"missing:{activity_id}")

            session.add(
                Activity(
                    id=activity_id,
                    name=meta.get("name"),
                    activity_type=str(meta.get("activity_type") or "real"),
                    started_at_utc=started,
                    created_at_utc=created,
                    file_hash_sha256=file_hash,
                    original_path=str(original_path),
                    parquet_path=str(parquet_path.resolve()),
                )
            )
            added += 1
            created_since_commit += 1
            if commit_mod and created_since_commit % commit_mod == 0:
                _commit_with_retry(session)
        except Exception as exc:
            errors += 1
            _rollback_quiet(session)
            logger.warning(
                "fast_indexation_add_failed",
                extra={"request_id": "-", "activity_id": activity_id, "error": str(exc)},
            )
        _set_progress(progress_current=min(scanned, idx), progress_total=max(1, scanned))

    stamped_at = utc_now_iso()
    for row in session.execute(select(ProgressActivityIndex).where(ProgressActivityIndex.activity_id.in_(sorted(fs_ids)))).scalars().all():
        row.fast_indexation_date = stamped_at

    _commit_with_retry(session)
    result = IndexationResult(scanned=scanned, added=added, deleted=deleted, errors=errors)
    should_chain_slow = bool((added + deleted) > 0)
    return result, should_chain_slow


def _should_reindex_activity(
    *,
    strategy: str,
    force: bool,
    row: ProgressActivityIndex | None,
    fingerprint: str,
    has_fit_source: bool,
) -> bool:
    if force:
        return True
    if strategy == "backfill_full":
        return True

    metrics_stale = row is not None and int(row.metrics_version) < int(METRICS_VERSION)
    fingerprint_stale = row is not None and row.fingerprint != fingerprint
    missing_row = row is None
    critical_missing = row is not None and row.vo2max is None and has_fit_source

    if strategy == "backfill_missing":
        return bool(missing_row or critical_missing)

    return bool(missing_row or metrics_stale or fingerprint_stale or critical_missing)


def _run_slow_indexation_once(
    session: Session,
    *,
    activities_dir: Path,
    strategy: str,
    force: bool,
    deadline_ts: float,
    commit_every: int = 25,
) -> IndexationResult:
    scanned = 0
    indexed = 0
    up_to_date = 0
    errors = 0
    skipped = 0

    activities = list(session.execute(select(Activity).order_by(Activity.created_at_utc.asc())).scalars().all())
    total = len(activities)
    _set_phase(MODE_SLOW, PHASE_RECOMPUTE, progress_current=0, progress_total=max(1, total))

    commit_mod = int(commit_every) if int(commit_every) > 0 else 0
    done_since_commit = 0
    for idx, act in enumerate(activities, start=1):
        _check_deadline(deadline_ts)
        scanned += 1
        activity_id = str(act.id)
        activity_dir = activities_dir / activity_id
        parquet_path = Path(str(act.parquet_path)) if act.parquet_path else (activity_dir / "df.parquet")
        meta_path = activity_dir / "meta.json"
        if not meta_path.exists() or not parquet_path.exists():
            skipped += 1
            _set_progress(progress_current=idx, progress_total=max(1, total))
            continue

        try:
            meta = _read_json(meta_path)
            fingerprint = build_fingerprint(meta, parquet_path)
            row = session.get(ProgressActivityIndex, activity_id)
            has_fit_source = _find_original_fit_path(activity_dir) is not None
            needs_reindex = _should_reindex_activity(
                strategy=strategy,
                force=bool(force),
                row=row,
                fingerprint=fingerprint,
                has_fit_source=bool(has_fit_source),
            )

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
                row = session.get(ProgressActivityIndex, activity_id)
                if row is not None:
                    row.slow_indexation_date = utc_now_iso()
                indexed += 1
            else:
                up_to_date += 1
                if row is not None:
                    row.slow_indexation_date = utc_now_iso()

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
                rollup_path = _write_rollup(activity_dir, payload)
                act.progress_rollup_path = rollup_path
                act.progress_indexed_at_utc = utc_now_iso()

            done_since_commit += 1
            if commit_mod and done_since_commit % commit_mod == 0:
                _commit_with_retry(session)
        except Exception as exc:
            errors += 1
            logger.warning(
                "slow_indexation_failed",
                extra={"request_id": "-", "activity_id": activity_id, "error": str(exc)},
            )
            _rollback_quiet(session)

        _set_progress(progress_current=idx, progress_total=max(1, total))

    _sync_vo2max_latest_from_index(session)
    _commit_with_retry(session)
    return IndexationResult(
        scanned=scanned,
        indexed=indexed,
        up_to_date=up_to_date,
        errors=errors,
        skipped=skipped,
    )


def start_fast_indexation_in_background(db_session_factory, reason: str) -> IndexationState:
    global _thread
    activities_dir = get_activities_dir().resolve()
    run_reason = str(reason or "manual")

    with _lock:
        if _thread is not None and _thread.is_alive():
            return _snapshot_state_unlocked()

        _state.running = True
        _state.mode = MODE_FAST
        _state.phase = PHASE_PREPARE
        _state.started_at_utc = _now_utc_iso()
        _state.finished_at_utc = None
        _state.progress_current = 0
        _state.progress_total = 0
        _state.last_error = None
        _state.last_result = None

    def _run() -> None:
        global _thread
        final_result = IndexationResult()
        run_error: str | None = None
        run_start_mono = time.monotonic()
        run_deadline = run_start_mono + float(_indexation_timeout_s())
        fast_run_id: str | None = None
        slow_run_id: str | None = None
        fast_run_completed = False
        slow_run_start_mono = run_start_mono
        slow_run_completed = False
        try:
            fast_run_id = _create_run_record(
                db_session_factory,
                mode=MODE_FAST,
                strategy=None,
                reason=run_reason,
            )
            session = db_session_factory()
            try:
                fast_result, has_delta = _run_fast_indexation_once(
                    session,
                    activities_dir=activities_dir,
                    deadline_ts=run_deadline,
                )
            finally:
                session.close()
            final_result = fast_result
            _finalize_run_record(
                db_session_factory,
                run_id=fast_run_id,
                status="completed",
                result=fast_result,
                error=None,
                progress_total=int(fast_result.scanned),
                progress_done=int(fast_result.scanned),
                started_monotonic=run_start_mono,
            )
            fast_run_completed = True

            if has_delta:
                slow_run_start_mono = time.monotonic()
                slow_deadline = slow_run_start_mono + float(_indexation_timeout_s())
                _set_phase(MODE_SLOW, PHASE_PREPARE, progress_current=0, progress_total=0)
                slow_run_id = _create_run_record(
                    db_session_factory,
                    mode=MODE_SLOW,
                    strategy="incremental",
                    reason="delta_detected",
                )
                session = db_session_factory()
                try:
                    slow_result = _run_slow_indexation_once(
                        session,
                        activities_dir=activities_dir,
                        strategy="incremental",
                        force=False,
                        deadline_ts=slow_deadline,
                    )
                finally:
                    session.close()
                final_result = _combine_results(fast_result, slow_result)
                _finalize_run_record(
                    db_session_factory,
                    run_id=slow_run_id,
                    status="completed",
                    result=slow_result,
                    error=None,
                    progress_total=int(slow_result.scanned),
                    progress_done=int(slow_result.scanned),
                    started_monotonic=slow_run_start_mono,
                )
                slow_run_completed = True

            with _lock:
                _state.last_result = final_result
        except Exception as exc:
            run_error = str(exc)
            with _lock:
                _state.last_error = run_error
            if fast_run_id is not None and not fast_run_completed:
                _finalize_run_record(
                    db_session_factory,
                    run_id=fast_run_id,
                    status="failed",
                    result=None,
                    error=run_error,
                    progress_total=int(_state.progress_total),
                    progress_done=int(_state.progress_current),
                    started_monotonic=run_start_mono,
                )
            if slow_run_id is not None and not slow_run_completed:
                _finalize_run_record(
                    db_session_factory,
                    run_id=slow_run_id,
                    status="failed",
                    result=None,
                    error=run_error,
                    progress_total=int(_state.progress_total),
                    progress_done=int(_state.progress_current),
                    started_monotonic=slow_run_start_mono,
                )
        finally:
            with _lock:
                _state.running = False
                _state.mode = None
                _state.phase = None
                _state.progress_current = int(max(_state.progress_current, _state.progress_total))
                _state.finished_at_utc = _now_utc_iso()

    _thread = threading.Thread(target=_run, name="progress-index-fast", daemon=True)
    _thread.start()
    with _lock:
        return _snapshot_state_unlocked()


def start_slow_indexation_in_background(
    db_session_factory,
    reason: str,
    strategy: str = "incremental",
    force: bool = False,
) -> IndexationState:
    global _thread
    selected_strategy = str(strategy or "incremental").strip().lower()
    if selected_strategy not in SLOW_STRATEGIES:
        selected_strategy = "incremental"

    activities_dir = get_activities_dir().resolve()
    run_reason = str(reason or "manual")

    with _lock:
        if _thread is not None and _thread.is_alive():
            return _snapshot_state_unlocked()

        _state.running = True
        _state.mode = MODE_SLOW
        _state.phase = PHASE_PREPARE
        _state.started_at_utc = _now_utc_iso()
        _state.finished_at_utc = None
        _state.progress_current = 0
        _state.progress_total = 0
        _state.last_error = None
        _state.last_result = None

    def _run() -> None:
        global _thread
        run_start_mono = time.monotonic()
        run_deadline = run_start_mono + float(_indexation_timeout_s())
        run_id: str | None = None
        run_error: str | None = None
        try:
            run_id = _create_run_record(
                db_session_factory,
                mode=MODE_SLOW,
                strategy=selected_strategy,
                reason=run_reason,
            )
            session = db_session_factory()
            try:
                result = _run_slow_indexation_once(
                    session,
                    activities_dir=activities_dir,
                    strategy=selected_strategy,
                    force=bool(force),
                    deadline_ts=run_deadline,
                )
            finally:
                session.close()
            with _lock:
                _state.last_result = result
            _finalize_run_record(
                db_session_factory,
                run_id=run_id,
                status="completed",
                result=result,
                error=None,
                progress_total=int(result.scanned),
                progress_done=int(result.scanned),
                started_monotonic=run_start_mono,
            )
        except Exception as exc:
            run_error = str(exc)
            with _lock:
                _state.last_error = run_error
            _finalize_run_record(
                db_session_factory,
                run_id=run_id,
                status="failed",
                result=None,
                error=run_error,
                progress_total=int(_state.progress_total),
                progress_done=int(_state.progress_current),
                started_monotonic=run_start_mono,
            )
        finally:
            with _lock:
                _state.running = False
                _state.mode = None
                _state.phase = None
                _state.progress_current = int(max(_state.progress_current, _state.progress_total))
                _state.finished_at_utc = _now_utc_iso()

    _thread = threading.Thread(target=_run, name="progress-index-slow", daemon=True)
    _thread.start()
    with _lock:
        return _snapshot_state_unlocked()
