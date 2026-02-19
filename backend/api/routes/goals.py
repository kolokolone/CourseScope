from __future__ import annotations

from datetime import date
import uuid

from fastapi import APIRouter, HTTPException, Request

from api.schemas import GoalCreateRequest, GoalItem, GoalsListResponse
from db.goals_repository import GoalsRepository
from db.models import utc_now_iso


router = APIRouter()


def _session_factory(request: Request):
    factory = getattr(request.app.state, "db_session_factory", None)
    if factory is None:
        raise HTTPException(status_code=500, detail="Database session factory is unavailable")
    return factory


def _normalize_event_date(raw_value: str) -> str:
    try:
        parsed = date.fromisoformat(str(raw_value).strip())
    except Exception as exc:
        raise HTTPException(status_code=400, detail="event_date must be ISO format YYYY-MM-DD") from exc
    return parsed.isoformat()


def _validate_goal_payload(payload: GoalCreateRequest) -> tuple[float | None, float | None]:
    if payload.distance_km <= 0:
        raise HTTPException(status_code=400, detail="distance_km must be > 0")

    has_time = payload.target_time_s is not None
    has_pace = payload.target_pace_s_per_km is not None
    if has_time == has_pace:
        raise HTTPException(status_code=400, detail="Provide exactly one target: target_time_s or target_pace_s_per_km")

    target_time_s = float(payload.target_time_s) if payload.target_time_s is not None else None
    target_pace_s_per_km = float(payload.target_pace_s_per_km) if payload.target_pace_s_per_km is not None else None

    if target_time_s is not None and target_time_s <= 0:
        raise HTTPException(status_code=400, detail="target_time_s must be > 0")

    if target_pace_s_per_km is not None and not (120.0 <= target_pace_s_per_km <= 1200.0):
        raise HTTPException(status_code=400, detail="target_pace_s_per_km must be between 120 and 1200")

    return target_time_s, target_pace_s_per_km


def _to_goal_item(row) -> GoalItem:
    return GoalItem(
        id=row.id,
        name=row.name,
        event_date=row.event_date,
        distance_km=float(row.distance_km),
        location=row.location,
        target_time_s=float(row.target_time_s) if row.target_time_s is not None else None,
        target_pace_s_per_km=float(row.target_pace_s_per_km) if row.target_pace_s_per_km is not None else None,
        race_type=row.race_type,
        notes=row.notes,
        created_at_utc=row.created_at_utc,
        updated_at_utc=row.updated_at_utc,
    )


@router.get("/goals", response_model=GoalsListResponse)
async def list_goals(request: Request):
    factory = _session_factory(request)
    repo = GoalsRepository()
    session = factory()
    try:
        rows = repo.list_goals(session)
        return GoalsListResponse(goals=[_to_goal_item(row) for row in rows])
    finally:
        session.close()


@router.post("/goals", response_model=GoalItem)
async def create_goal(request: Request, payload: GoalCreateRequest):
    factory = _session_factory(request)
    repo = GoalsRepository()
    session = factory()

    target_time_s, target_pace_s_per_km = _validate_goal_payload(payload)
    event_date = _normalize_event_date(payload.event_date)
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    location = payload.location.strip() if isinstance(payload.location, str) else ""
    notes = payload.notes.strip() if isinstance(payload.notes, str) else ""
    now_utc = utc_now_iso()

    try:
        row = repo.create_goal(
            session,
            goal_id=str(uuid.uuid4()),
            name=name,
            event_date=event_date,
            distance_km=float(payload.distance_km),
            location=location if location else None,
            target_time_s=target_time_s,
            target_pace_s_per_km=target_pace_s_per_km,
            race_type=payload.race_type,
            notes=notes if notes else None,
            now_utc=now_utc,
        )
        session.commit()
        session.refresh(row)
        return _to_goal_item(row)
    except HTTPException:
        raise
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create goal: {str(exc)}")
    finally:
        session.close()


@router.delete("/goals/{goal_id}")
async def delete_goal(request: Request, goal_id: str):
    factory = _session_factory(request)
    repo = GoalsRepository()
    session = factory()
    try:
        deleted = repo.delete_goal(session, goal_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Goal {goal_id} not found")
        session.commit()
        return {"deleted": True}
    except HTTPException:
        raise
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete goal: {str(exc)}")
    finally:
        session.close()
