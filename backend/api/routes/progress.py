from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Request
from starlette.responses import JSONResponse

from db.models import ProgressActivityTag, utc_now_iso
from db.progress_repository import ProgressRepository
from progress.indexation_runner import (
    get_indexation_state,
    start_fast_indexation_in_background,
    start_slow_indexation_in_background,
)
from services.progress_service import ProgressService

from core.utils import (
    parse_ts_utc as _parse_ts_utc_core,
    parse_csv_floats as _parse_csv_floats,
    parse_optional_bool as _parse_optional_bool,
)



def _parse_ts_utc(value: str | None, *, is_end: bool) -> str | None:
    """Wrapper qui convertit ValueError en HTTPException 400."""
    try:
        return _parse_ts_utc_core(value, is_end=is_end)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


router = APIRouter()

SESSION_TAGS = {"easy", "tempo", "interval", "long_run", "unknown"}
TERRAIN_TAGS = {"flat", "rolling", "hilly", "unknown"}


def _to_indexation_status_payload(state) -> dict:
    now = datetime.now(timezone.utc)

    def _parse_iso(raw: str | None) -> datetime | None:
        if raw is None:
            return None
        try:
            dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except Exception:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    started = _parse_iso(state.started_at_utc)
    finished = _parse_iso(state.finished_at_utc)

    current_run_duration_ms = None
    if bool(state.running) and started is not None:
        current_run_duration_ms = max(0, int((now - started).total_seconds() * 1000.0))

    last_duration_ms = None
    if started is not None and finished is not None:
        last_duration_ms = max(0, int((finished - started).total_seconds() * 1000.0))

    total = int(state.progress_total or 0)
    current = int(state.progress_current or 0)
    percent = 0.0
    if total > 0:
        percent = max(0.0, min(100.0, (float(current) / float(total)) * 100.0))

    last_result = state.last_result.to_dict() if state.last_result is not None else None

    return {
        "running": bool(state.running),
        "mode": state.mode,
        "phase": state.phase,
        "current_run_duration_ms": current_run_duration_ms,
        "progress_current": current,
        "progress_total": total,
        "percent": round(percent, 2),
        "last_result": last_result,
        "last_error": state.last_error,
        "last_started_at_utc": state.started_at_utc,
        "last_finished_at_utc": state.finished_at_utc,
        "last_duration_ms": last_duration_ms,
    }


@router.post("/progress/index/fast")
async def trigger_fast_indexation(request: Request, payload: dict | None = None):
    db_session_factory = getattr(request.app.state, "db_session_factory", None)
    if db_session_factory is None:
        raise HTTPException(status_code=500, detail="DB not initialized")

    body = payload or {}
    reason = str(body.get("reason") or "api_fast").strip() or "api_fast"

    before = get_indexation_state()
    state = start_fast_indexation_in_background(db_session_factory=db_session_factory, reason=reason)
    payload = _to_indexation_status_payload(state)
    if before.running:
        return JSONResponse(status_code=202, content=payload)
    return payload


@router.post("/progress/index/slow")
async def trigger_slow_indexation(request: Request, payload: dict | None = None):
    db_session_factory = getattr(request.app.state, "db_session_factory", None)
    if db_session_factory is None:
        raise HTTPException(status_code=500, detail="DB not initialized")

    body = payload or {}
    strategy_raw = str(body.get("strategy") or "incremental").strip().lower()
    strategy = strategy_raw if strategy_raw in {"incremental", "backfill_missing", "backfill_full"} else "incremental"
    reason = str(body.get("reason") or "manual").strip() or "manual"
    force = bool(body.get("force") is True)
    if force and strategy != "backfill_full":
        strategy = "backfill_full"

    before = get_indexation_state()
    state = start_slow_indexation_in_background(
        db_session_factory=db_session_factory,
        reason=reason,
        strategy=strategy,
        force=force,
    )
    status = _to_indexation_status_payload(state)
    if before.running:
        return JSONResponse(status_code=202, content=status)
    return status


@router.get("/progress/index/status")
async def get_progress_index_status(request: Request):
    db_session_factory = getattr(request.app.state, "db_session_factory", None)
    if db_session_factory is None:
        raise HTTPException(status_code=500, detail="DB not initialized")

    state = get_indexation_state()
    return _to_indexation_status_payload(state)


@router.get("/progress/activities")
async def list_progress_activities(
    request: Request,
    from_ts: str | None = Query(None, alias="from"),
    to_ts: str | None = Query(None, alias="to"),
    activity_type: str | None = Query(None, alias="type"),
    limit: int | None = Query(None),
    session_tag: str | None = Query(None),
    terrain_tag: str | None = Query(None),
    race_marker: bool | None = Query(None),
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
        if session_tag is not None and session_tag not in SESSION_TAGS:
            raise HTTPException(status_code=400, detail="Invalid session_tag")
        if terrain_tag is not None and terrain_tag not in TERRAIN_TAGS:
            raise HTTPException(status_code=400, detail="Invalid terrain_tag")

        rows = repo.list_activity_rows(
            session,
            from_ts_utc=from_ts_utc,
            to_ts_utc=to_ts_utc,
            activity_type=activity_type,
            limit=limit,
        )

        activity_ids = [str(r.activity_id) for r in rows]
        tags_map = repo.get_activity_tags_map(session, activity_ids=activity_ids)

        payload = ProgressService.build_activity_list(
            rows, tags_map,
            filters={"session_tag": session_tag, "terrain_tag": terrain_tag, "race_marker": race_marker},
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
        "vo2max",
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

    return ProgressService.compute_time_series(rows, group_by, agg)


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

    return {"points": ProgressService.annotate_prs(points)}


@router.get("/progress/hr-at-pace")
async def get_progress_hr_at_pace(
    request: Request,
    paces_s_per_km: str | None = Query(None),
    from_ts: str | None = Query(None, alias="from"),
    to_ts: str | None = Query(None, alias="to"),
    activity_type: str | None = Query(None, alias="type"),
    session_tag: str | None = Query(None),
    terrain_tag: str | None = Query(None),
    endurance_only: bool = Query(False),
):
    db_session_factory = getattr(request.app.state, "db_session_factory", None)
    if db_session_factory is None:
        raise HTTPException(status_code=500, detail="DB not initialized")

    if activity_type is not None and activity_type not in {"real", "theoretical"}:
        raise HTTPException(status_code=400, detail="Invalid type")
    if session_tag is not None and session_tag not in SESSION_TAGS:
        raise HTTPException(status_code=400, detail="Invalid session_tag")
    if terrain_tag is not None and terrain_tag not in TERRAIN_TAGS:
        raise HTTPException(status_code=400, detail="Invalid terrain_tag")

    refs = _parse_csv_floats(paces_s_per_km, default_values=[300.0, 330.0, 360.0])
    refs = [r for r in refs if 120.0 <= r <= 1200.0]
    if not refs:
        raise HTTPException(status_code=400, detail="Invalid paces_s_per_km")

    from_ts_utc = _parse_ts_utc(from_ts, is_end=False)
    to_ts_utc = _parse_ts_utc(to_ts, is_end=True)

    repo = ProgressRepository()
    session = db_session_factory()
    try:
        rows = repo.list_pace_hr_rows(
            session,
            from_ts_utc=from_ts_utc,
            to_ts_utc=to_ts_utc,
            activity_type=activity_type,
            session_tag=session_tag,
            terrain_tag=terrain_tag,
            endurance_only=bool(endurance_only),
        )
    finally:
        session.close()

    return ProgressService.compute_hr_pace_series(rows, refs, "hr_at_pace")


@router.get("/progress/pace-at-hr")
async def get_progress_pace_at_hr(
    request: Request,
    hrs_bpm: str | None = Query(None),
    from_ts: str | None = Query(None, alias="from"),
    to_ts: str | None = Query(None, alias="to"),
    activity_type: str | None = Query(None, alias="type"),
    session_tag: str | None = Query(None),
    terrain_tag: str | None = Query(None),
    endurance_only: bool = Query(False),
):
    db_session_factory = getattr(request.app.state, "db_session_factory", None)
    if db_session_factory is None:
        raise HTTPException(status_code=500, detail="DB not initialized")

    if activity_type is not None and activity_type not in {"real", "theoretical"}:
        raise HTTPException(status_code=400, detail="Invalid type")
    if session_tag is not None and session_tag not in SESSION_TAGS:
        raise HTTPException(status_code=400, detail="Invalid session_tag")
    if terrain_tag is not None and terrain_tag not in TERRAIN_TAGS:
        raise HTTPException(status_code=400, detail="Invalid terrain_tag")

    refs = _parse_csv_floats(hrs_bpm, default_values=[140.0, 150.0, 160.0])
    refs = [r for r in refs if 80.0 <= r <= 220.0]
    if not refs:
        raise HTTPException(status_code=400, detail="Invalid hrs_bpm")

    from_ts_utc = _parse_ts_utc(from_ts, is_end=False)
    to_ts_utc = _parse_ts_utc(to_ts, is_end=True)

    repo = ProgressRepository()
    session = db_session_factory()
    try:
        rows = repo.list_pace_hr_rows(
            session,
            from_ts_utc=from_ts_utc,
            to_ts_utc=to_ts_utc,
            activity_type=activity_type,
            session_tag=session_tag,
            terrain_tag=terrain_tag,
            endurance_only=bool(endurance_only),
        )
    finally:
        session.close()

    return ProgressService.compute_hr_pace_series(rows, refs, "pace_at_hr")


@router.get("/progress/session-taxonomy")
async def get_progress_session_taxonomy(
    request: Request,
    from_ts: str | None = Query(None, alias="from"),
    to_ts: str | None = Query(None, alias="to"),
    activity_type: str | None = Query(None, alias="type"),
):
    db_session_factory = getattr(request.app.state, "db_session_factory", None)
    if db_session_factory is None:
        raise HTTPException(status_code=500, detail="DB not initialized")

    if activity_type is not None and activity_type not in {"real", "theoretical"}:
        raise HTTPException(status_code=400, detail="Invalid type")

    from_ts_utc = _parse_ts_utc(from_ts, is_end=False)
    to_ts_utc = _parse_ts_utc(to_ts, is_end=True)

    repo = ProgressRepository()
    session = db_session_factory()
    try:
        rows = repo.list_activity_tag_rows(
            session,
            from_ts_utc=from_ts_utc,
            to_ts_utc=to_ts_utc,
            activity_type=activity_type,
        )
    finally:
        session.close()

    return ProgressService.compute_session_taxonomy(rows)


@router.post("/progress/tags")
async def upsert_progress_activity_tag(request: Request, payload: dict):
    db_session_factory = getattr(request.app.state, "db_session_factory", None)
    if db_session_factory is None:
        raise HTTPException(status_code=500, detail="DB not initialized")

    activity_id = str(payload.get("activity_id") or "").strip()
    if not activity_id:
        raise HTTPException(status_code=400, detail="activity_id is required")

    session_tag_raw = payload.get("session_tag")
    terrain_tag_raw = payload.get("terrain_tag")
    race_marker_raw = payload.get("race_marker")

    session_tag = str(session_tag_raw).strip() if session_tag_raw is not None else None
    terrain_tag = str(terrain_tag_raw).strip() if terrain_tag_raw is not None else None
    race_marker = _parse_optional_bool(race_marker_raw)

    if session_tag is not None and session_tag not in SESSION_TAGS:
        raise HTTPException(status_code=400, detail="Invalid session_tag")
    if terrain_tag is not None and terrain_tag not in TERRAIN_TAGS:
        raise HTTPException(status_code=400, detail="Invalid terrain_tag")

    repo = ProgressRepository()
    session = db_session_factory()
    try:
        previous = repo.get_activity_tags_map(session, activity_ids=[activity_id]).get(activity_id)
        merged = ProgressService.merge_tag(previous, {
            "session_tag": session_tag,
            "terrain_tag": terrain_tag,
            "race_marker": race_marker,
        })
        repo.upsert_activity_tag(
            session,
            row=ProgressActivityTag(
                activity_id=activity_id,
                session_tag=merged["session_tag"],
                terrain_tag=merged["terrain_tag"],
                race_marker=merged["race_marker"],
                source="manual",
                updated_at_ts=utc_now_iso(),
            ),
            preserve_manual=False,
        )
        session.commit()
    finally:
        session.close()

    return {"ok": True, "activity_id": activity_id}


@router.get("/progress/pace-hr-waterfall")
async def get_progress_pace_hr_waterfall(
    request: Request,
    from_ts: str | None = Query(None, alias="from"),
    to_ts: str | None = Query(None, alias="to"),
    activity_type: str | None = Query(None, alias="type"),
    limit: int = Query(30, ge=1, le=120),
    bin_step_s_per_km: int = Query(10, ge=1, le=60),
    session_tag: str | None = Query(None),
    terrain_tag: str | None = Query(None),
    endurance_only: bool = Query(False),
):
    db_session_factory = getattr(request.app.state, "db_session_factory", None)
    if db_session_factory is None:
        raise HTTPException(status_code=500, detail="DB not initialized")

    if activity_type is not None and activity_type not in {"real", "theoretical"}:
        raise HTTPException(status_code=400, detail="Invalid type")
    if session_tag is not None and session_tag not in SESSION_TAGS:
        raise HTTPException(status_code=400, detail="Invalid session_tag")
    if terrain_tag is not None and terrain_tag not in TERRAIN_TAGS:
        raise HTTPException(status_code=400, detail="Invalid terrain_tag")

    from_ts_utc = _parse_ts_utc(from_ts, is_end=False)
    to_ts_utc = _parse_ts_utc(to_ts, is_end=True)

    repo = ProgressRepository()
    session = db_session_factory()
    try:
        rows = repo.list_pace_hr_rows(
            session,
            from_ts_utc=from_ts_utc,
            to_ts_utc=to_ts_utc,
            activity_type=activity_type,
            session_tag=session_tag,
            terrain_tag=terrain_tag,
            endurance_only=bool(endurance_only),
        )
        tag_map = repo.get_activity_tags_map(session, activity_ids=sorted({r.activity_id for r in rows}))
    finally:
        session.close()

    activities = ProgressService.compute_waterfall(rows, tag_map, float(bin_step_s_per_km))
    if len(activities) > int(limit):
        activities = activities[-int(limit):]
    return {"activities": activities}


@router.get("/progress/training-load")
async def get_training_load(
    request: Request,
    from_ts: str | None = Query(None, alias="from"),
    to_ts: str | None = Query(None, alias="to"),
):
    """ACWR, monotonie d'entraînement, et strain à partir de la série TRIMP."""
    db_session_factory = getattr(request.app.state, "db_session_factory", None)
    if db_session_factory is None:
        raise HTTPException(status_code=500, detail="DB not initialized")

    from_ts_utc = _parse_ts_utc(from_ts, is_end=False)
    to_ts_utc = _parse_ts_utc(to_ts, is_end=True)

    repo = ProgressRepository()
    session = db_session_factory()
    try:
        rows = repo.list_series_rows(
            session,
            metric="trimp",
            from_ts_utc=from_ts_utc,
            to_ts_utc=to_ts_utc,
            activity_type="real",
        )
    finally:
        session.close()

    return ProgressService.compute_training_load(rows)


@router.get("/progress/calendar")
async def get_calendar(
    request: Request,
    year: int = Query(..., ge=2000, le=2100),
):
    """Données de heatmap calendrier pour une année donnée."""
    db_session_factory = getattr(request.app.state, "db_session_factory", None)
    if db_session_factory is None:
        raise HTTPException(status_code=500, detail="DB not initialized")

    from_ts = f"{year}-01-01T00:00:00Z"
    to_ts = f"{year}-12-31T23:59:59Z"

    repo = ProgressRepository()
    session = db_session_factory()
    try:
        rows = repo.list_activity_rows(
            session,
            from_ts_utc=from_ts,
            to_ts_utc=to_ts,
            activity_type="real",
            limit=None,
        )
    finally:
        session.close()

    return ProgressService.compute_calendar(rows, year)
