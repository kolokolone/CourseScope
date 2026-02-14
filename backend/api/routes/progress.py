from __future__ import annotations

import math
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Query, Request

from db.progress_repository import ProgressRepository
from progress.verify_runner import get_verify_state, start_verify_in_background


router = APIRouter()


@router.post("/progress/verify")
async def verify_progress_index_endpoint(request: Request):
    db_session_factory = getattr(request.app.state, "db_session_factory", None)
    if db_session_factory is None:
        raise HTTPException(status_code=500, detail="DB not initialized")

    state = start_verify_in_background(db_session_factory=db_session_factory)
    return {
        "running": bool(state.running),
        "last_started_at_utc": state.last_started_at_utc,
        "last_finished_at_utc": state.last_finished_at_utc,
        "last_error": state.last_error,
        "last_result": state.last_result.__dict__ if state.last_result is not None else None,
    }


@router.get("/progress/verify-status")
async def verify_progress_status_endpoint(request: Request):
    db_session_factory = getattr(request.app.state, "db_session_factory", None)
    if db_session_factory is None:
        raise HTTPException(status_code=500, detail="DB not initialized")

    state = get_verify_state()
    return {
        "running": bool(state.running),
        "last_started_at_utc": state.last_started_at_utc,
        "last_finished_at_utc": state.last_finished_at_utc,
        "last_error": state.last_error,
        "last_result": state.last_result.__dict__ if state.last_result is not None else None,
    }


def _parse_ts_utc(value: str | None, *, is_end: bool) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if raw == "":
        return None

    # Accept YYYY-MM-DD and interpret as UTC day bounds.
    if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
        if is_end:
            raw = f"{raw}T23:59:59Z"
        else:
            raw = f"{raw}T00:00:00Z"

    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid datetime: {value}")

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc).replace(microsecond=0)
    return dt.isoformat().replace("+00:00", "Z")


def _bucket_start(dt: datetime, group_by: str) -> datetime:
    d = dt.astimezone(timezone.utc)
    if group_by == "day":
        return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    if group_by == "month":
        return datetime(d.year, d.month, 1, tzinfo=timezone.utc)

    # group_by == 'week' => ISO week starting Monday.
    base = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    weekday = base.weekday()  # Monday=0
    return base.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=weekday)


@router.get("/progress/activities")
async def list_progress_activities(
    request: Request,
    from_ts: str | None = Query(None, alias="from"),
    to_ts: str | None = Query(None, alias="to"),
    activity_type: str | None = Query(None, alias="type"),
    limit: int | None = Query(None),
):
    db_session_factory = getattr(request.app.state, "db_session_factory", None)
    if db_session_factory is None:
        raise HTTPException(status_code=500, detail="DB not initialized")

    repo = ProgressRepository()
    session = db_session_factory()
    try:
        from_ts_utc = _parse_ts_utc(from_ts, is_end=False)
        to_ts_utc = _parse_ts_utc(to_ts, is_end=True)
        if activity_type is not None and activity_type not in {"real", "theoretical"}:
            raise HTTPException(status_code=400, detail="Invalid type")

        rows = repo.list_activity_rows(
            session,
            from_ts_utc=from_ts_utc,
            to_ts_utc=to_ts_utc,
            activity_type=activity_type,
            limit=limit,
        )
        payload = []
        for r in rows:
            payload.append(
                {
                    "activity_id": r.activity_id,
                    "activity_type": r.activity_type,
                    "start_ts_utc": r.start_ts_utc,
                    "distance_m": r.distance_m,
                    "moving_time_s": r.moving_time_s,
                    "elapsed_time_s": r.elapsed_time_s,
                    "elevation_gain_m": r.elevation_gain_m,
                    "avg_pace_s_per_km": r.avg_pace_s_per_km,
                    "best_pace_s_per_km": r.best_pace_s_per_km,
                    "pace_threshold_s_per_km": r.pace_threshold_s_per_km,
                    "avg_hr_bpm": r.avg_hr_bpm,
                    "max_hr_bpm": r.max_hr_bpm,
                    "trimp": r.trimp,
                    "training_load_method": r.training_load_method,
                    "aerobic_efficiency_m_s_per_bpm": r.aerobic_efficiency_m_s_per_bpm,
                    "decoupling_pct": r.decoupling_pct,
                    "stability_cv": r.stability_cv,
                    "stability_iqr_ratio": r.stability_iqr_ratio,
                    "has_hr": bool(r.has_hr),
                    "has_power": bool(r.has_power),
                    "has_cadence": bool(r.has_cadence),
                    "data_points": r.data_points,
                }
            )

        return {"activities": payload}
    finally:
        session.close()


@router.get("/progress/series")
async def get_progress_series(
    request: Request,
    metric: str = Query(...),
    group_by: str = Query("week"),
    agg: str = Query("sum"),
    from_ts: str | None = Query(None, alias="from"),
    to_ts: str | None = Query(None, alias="to"),
    activity_type: str | None = Query(None, alias="type"),
):
    db_session_factory = getattr(request.app.state, "db_session_factory", None)
    if db_session_factory is None:
        raise HTTPException(status_code=500, detail="DB not initialized")

    allowed_metrics = {
        "distance_m",
        "moving_time_s",
        "elapsed_time_s",
        "elevation_gain_m",
        "trimp",
        "aerobic_efficiency_m_s_per_bpm",
        "decoupling_pct",
    }
    if metric not in allowed_metrics:
        raise HTTPException(status_code=400, detail=f"Unsupported metric: {metric}")
    if activity_type is not None and activity_type not in {"real", "theoretical"}:
        raise HTTPException(status_code=400, detail="Invalid type")

    if group_by not in {"day", "week", "month"}:
        raise HTTPException(status_code=400, detail="Invalid group_by")
    if agg not in {"sum", "avg"}:
        raise HTTPException(status_code=400, detail="Invalid agg")

    from_ts_utc = _parse_ts_utc(from_ts, is_end=False)
    to_ts_utc = _parse_ts_utc(to_ts, is_end=True)

    repo = ProgressRepository()
    session = db_session_factory()
    try:
        rows = repo.list_series_rows(
            session,
            metric=metric,
            from_ts_utc=from_ts_utc,
            to_ts_utc=to_ts_utc,
            activity_type=activity_type,
        )
    finally:
        session.close()

    buckets: dict[str, list[float]] = {}
    for r in rows:
        if r.value is None:
            continue
        if not isinstance(r.value, (int, float)):
            continue
        v = float(r.value)
        if not math.isfinite(v):
            continue

        try:
            dt = datetime.fromisoformat(str(r.start_ts_utc).replace("Z", "+00:00"))
        except Exception:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        b = _bucket_start(dt, group_by)
        key = b.date().isoformat()
        buckets.setdefault(key, []).append(v)

    out = []
    for key in sorted(buckets.keys()):
        values = buckets[key]
        if not values:
            continue
        if agg == "avg":
            value = float(sum(values) / len(values))
        else:
            value = float(sum(values))
        out.append({"bucket_start": key, "value": value})

    return out


@router.get("/progress/best-efforts")
async def get_progress_best_efforts(
    request: Request,
    kind: str = Query(...),
    duration_s: int = Query(..., ge=1),
    from_ts: str | None = Query(None, alias="from"),
    to_ts: str | None = Query(None, alias="to"),
):
    db_session_factory = getattr(request.app.state, "db_session_factory", None)
    if db_session_factory is None:
        raise HTTPException(status_code=500, detail="DB not initialized")

    if kind != "pace_s_per_km":
        raise HTTPException(status_code=400, detail="Unsupported kind")

    from_ts_utc = _parse_ts_utc(from_ts, is_end=False)
    to_ts_utc = _parse_ts_utc(to_ts, is_end=True)

    repo = ProgressRepository()
    session = db_session_factory()
    try:
        points = repo.list_best_effort_points(
            session,
            effort_kind=kind,
            duration_s=int(duration_s),
            from_ts_utc=from_ts_utc,
            to_ts_utc=to_ts_utc,
        )
    finally:
        session.close()

    best = math.inf
    out = []
    for p in points:
        v = float(p.value)
        is_pr = False
        if math.isfinite(v) and v < best:
            best = v
            is_pr = True
        out.append(
            {
                "activity_id": p.activity_id,
                "start_ts_utc": p.start_ts_utc,
                "value": v,
                "is_pr": is_pr,
            }
        )

    return {"points": out}
