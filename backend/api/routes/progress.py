from __future__ import annotations

import math
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Query, Request
from starlette.responses import JSONResponse

from db.models import ProgressActivityTag, utc_now_iso
from db.progress_repository import ProgressRepository
from progress.indexation_runner import (
    get_indexation_state,
    start_fast_indexation_in_background,
    start_slow_indexation_in_background,
)
from progress.verify_runner import get_verify_state, start_verify_in_background


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


def _parse_csv_floats(raw: str | None, *, default_values: list[float]) -> list[float]:
    if raw is None or str(raw).strip() == "":
        return list(default_values)
    out: list[float] = []
    for part in str(raw).split(","):
        token = part.strip()
        if token == "":
            continue
        try:
            value = float(token)
        except Exception:
            continue
        if math.isfinite(value):
            out.append(value)
    if not out:
        return list(default_values)
    return sorted(set(out))


def _dedupe_xy(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not points:
        return []
    grouped: dict[float, list[float]] = {}
    for x, y in points:
        grouped.setdefault(float(x), []).append(float(y))
    out = []
    for x in sorted(grouped.keys()):
        vals = grouped[x]
        out.append((x, float(sum(vals) / len(vals))))
    return out


def _interp_linear(points: list[tuple[float, float]], target_x: float) -> float | None:
    if not points:
        return None
    pts = _dedupe_xy(points)
    if not pts:
        return None
    x0 = pts[0][0]
    x1 = pts[-1][0]
    if target_x < x0 or target_x > x1:
        return None
    for i in range(len(pts) - 1):
        xa, ya = pts[i]
        xb, yb = pts[i + 1]
        if xa == xb:
            continue
        if xa <= target_x <= xb:
            ratio = (target_x - xa) / (xb - xa)
            y = ya + ratio * (yb - ya)
            return float(y) if math.isfinite(y) else None
    if target_x == pts[-1][0]:
        return float(pts[-1][1])
    return None


def _parse_optional_bool(value: object) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in {"1", "true", "yes", "y", "on"}:
        return True
    if s in {"0", "false", "no", "n", "off"}:
        return False
    return None


def _aggregate_curve(points: list[tuple[float, float, float]], bin_step: float) -> list[dict[str, float]]:
    if not points:
        return []
    grouped: dict[float, list[tuple[float, float]]] = {}
    step = max(1.0, float(bin_step))
    for pace, hr, weight in points:
        if not (math.isfinite(pace) and math.isfinite(hr) and math.isfinite(weight) and weight > 0):
            continue
        bucket = round(pace / step) * step
        grouped.setdefault(bucket, []).append((hr, weight))

    out: list[dict[str, float]] = []
    for pace_bin in sorted(grouped.keys()):
        values = grouped[pace_bin]
        total = sum(w for _, w in values)
        if total <= 0:
            continue
        hr_mean = sum(v * w for v, w in values) / total
        out.append({"pace_bin_s_per_km": float(pace_bin), "hr_bpm": float(hr_mean), "time_s_bin": float(total)})
    return out


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

        if session_tag is not None or terrain_tag is not None or race_marker is not None:
            filtered_rows = []
            for r in rows:
                tag = tags_map.get(str(r.activity_id))
                if session_tag is not None and (tag is None or tag.session_tag != session_tag):
                    continue
                if terrain_tag is not None and (tag is None or tag.terrain_tag != terrain_tag):
                    continue
                if race_marker is not None and (tag is None or bool(tag.race_marker) != bool(race_marker)):
                    continue
                filtered_rows.append(r)
            rows = filtered_rows

        payload = []
        for r in rows:
            tag = tags_map.get(str(r.activity_id))
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
                    "vo2max": r.vo2max,
                    "decoupling_pct": r.decoupling_pct,
                    "stability_cv": r.stability_cv,
                    "stability_iqr_ratio": r.stability_iqr_ratio,
                    "has_hr": bool(r.has_hr),
                    "has_power": bool(r.has_power),
                    "has_cadence": bool(r.has_cadence),
                    "data_points": r.data_points,
                    "session_tag": (tag.session_tag if tag is not None else None),
                    "terrain_tag": (tag.terrain_tag if tag is not None else None),
                    "race_marker": (bool(tag.race_marker) if tag is not None else False),
                    "tag_source": (tag.source if tag is not None else None),
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

    per_activity: dict[str, dict] = {}
    for r in rows:
        hr_value = r.hr_q50_w_bpm if r.hr_q50_w_bpm is not None else r.hr_mean_w_bpm
        if hr_value is None:
            continue
        if not math.isfinite(hr_value):
            continue
        if not math.isfinite(r.pace_bin_s_per_km):
            continue
        data = per_activity.setdefault(r.activity_id, {"start_ts_utc": r.start_ts_utc, "pairs": []})
        data["pairs"].append((float(r.pace_bin_s_per_km), float(hr_value)))

    out_series = []
    for ref in refs:
        pts = []
        for activity_id, data in per_activity.items():
            value = _interp_linear(list(data["pairs"]), float(ref))
            if value is None:
                continue
            pts.append(
                {
                    "activity_id": activity_id,
                    "start_ts_utc": data["start_ts_utc"],
                    "value": float(value),
                }
            )
        pts.sort(key=lambda x: str(x["start_ts_utc"]))
        out_series.append({"pace_s_per_km": float(ref), "points": pts})

    return {"series": out_series}


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

    per_activity: dict[str, dict] = {}
    for r in rows:
        hr_value = r.hr_q50_w_bpm if r.hr_q50_w_bpm is not None else r.hr_mean_w_bpm
        if hr_value is None:
            continue
        if not (math.isfinite(hr_value) and math.isfinite(r.pace_bin_s_per_km)):
            continue
        data = per_activity.setdefault(r.activity_id, {"start_ts_utc": r.start_ts_utc, "pairs": []})
        data["pairs"].append((float(hr_value), float(r.pace_bin_s_per_km)))

    out_series = []
    for ref in refs:
        pts = []
        for activity_id, data in per_activity.items():
            value = _interp_linear(list(data["pairs"]), float(ref))
            if value is None:
                continue
            pts.append(
                {
                    "activity_id": activity_id,
                    "start_ts_utc": data["start_ts_utc"],
                    "value": float(value),
                }
            )
        pts.sort(key=lambda x: str(x["start_ts_utc"]))
        out_series.append({"hr_bpm": float(ref), "points": pts})

    return {"series": out_series}


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

    session_counts: dict[str, int] = {}
    terrain_counts: dict[str, int] = {}
    race_markers = 0
    for r in rows:
        s = r.session_tag or "unknown"
        t = r.terrain_tag or "unknown"
        session_counts[s] = session_counts.get(s, 0) + 1
        terrain_counts[t] = terrain_counts.get(t, 0) + 1
        if r.race_marker:
            race_markers += 1

    return {
        "session_counts": [{"tag": k, "count": session_counts[k]} for k in sorted(session_counts.keys())],
        "terrain_counts": [{"tag": k, "count": terrain_counts[k]} for k in sorted(terrain_counts.keys())],
        "race_markers": int(race_markers),
        "total_tagged": int(len(rows)),
    }


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
        repo.upsert_activity_tag(
            session,
            row=ProgressActivityTag(
                activity_id=activity_id,
                session_tag=(session_tag if session_tag is not None else (previous.session_tag if previous is not None else None)),
                terrain_tag=(terrain_tag if terrain_tag is not None else (previous.terrain_tag if previous is not None else None)),
                race_marker=(
                    int(bool(race_marker))
                    if race_marker is not None
                    else (1 if (previous is not None and previous.race_marker) else 0)
                ),
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

    by_activity: dict[str, dict] = {}
    for r in rows:
        hr_value = r.hr_q50_w_bpm if r.hr_q50_w_bpm is not None else r.hr_mean_w_bpm
        if hr_value is None:
            continue
        if not (math.isfinite(hr_value) and math.isfinite(r.pace_bin_s_per_km) and math.isfinite(r.time_s_bin)):
            continue
        item = by_activity.setdefault(
            r.activity_id,
            {
                "activity_id": r.activity_id,
                "start_ts_utc": r.start_ts_utc,
                "points_raw": [],
            },
        )
        item["points_raw"].append((float(r.pace_bin_s_per_km), float(hr_value), float(r.time_s_bin)))

    activities = []
    for activity_id, item in by_activity.items():
        points = _aggregate_curve(list(item["points_raw"]), float(bin_step_s_per_km))
        if len(points) < 1:
            continue
        tag = tag_map.get(activity_id)
        activities.append(
            {
                "activity_id": activity_id,
                "start_ts_utc": item["start_ts_utc"],
                "session_tag": tag.session_tag if tag is not None else "unknown",
                "terrain_tag": tag.terrain_tag if tag is not None else "unknown",
                "race_marker": bool(tag.race_marker) if tag is not None else False,
                "points": points,
            }
        )

    activities.sort(key=lambda x: str(x["start_ts_utc"]))
    if len(activities) > int(limit):
        activities = activities[-int(limit):]
    return {"activities": activities}
