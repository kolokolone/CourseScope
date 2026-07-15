from __future__ import annotations

from datetime import date, datetime
import uuid
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Request

from api._helpers import get_db_session_factory
from api.schemas import GoalCreateRequest, GoalItem, GoalsListResponse, GoalUpdateRequest
from db.goals_repository import GoalsRepository
from db.models import utc_now_iso


router = APIRouter()
APP_TIMEZONE = ZoneInfo("Europe/Paris")


def _session_factory(request: Request):
    return get_db_session_factory(request)


def _today_local() -> date:
    return datetime.now(APP_TIMEZONE).date()


def _normalize_event_date(raw_value: str) -> str:
    try:
        parsed = date.fromisoformat(str(raw_value).strip())
    except Exception as exc:
        raise HTTPException(status_code=400, detail="event_date must be ISO format YYYY-MM-DD") from exc
    return parsed.isoformat()


def _validate_goal_values(
    *,
    distance_km: float,
    target_time_s: float | None,
    target_pace_s_per_km: float | None,
) -> tuple[float | None, float | None]:
    if distance_km <= 0:
        raise HTTPException(status_code=400, detail="distance_km must be > 0")

    has_time = target_time_s is not None
    has_pace = target_pace_s_per_km is not None
    if has_time == has_pace:
        raise HTTPException(status_code=400, detail="Provide exactly one target: target_time_s or target_pace_s_per_km")

    target_time = float(target_time_s) if target_time_s is not None else None
    target_pace = float(target_pace_s_per_km) if target_pace_s_per_km is not None else None

    if target_time is not None and target_time <= 0:
        raise HTTPException(status_code=400, detail="target_time_s must be > 0")

    if target_pace is not None and not (120.0 <= target_pace <= 1200.0):
        raise HTTPException(status_code=400, detail="target_pace_s_per_km must be between 120 and 1200")

    return target_time, target_pace


def _to_goal_item(row) -> GoalItem:
    return GoalItem(
        id=row.id,
        name=row.name,
        event_date=row.event_date,
        distance_km=float(row.distance_km),
        location=row.location,
        location_city=row.location_city,
        location_country=row.location_country,
        location_country_code=row.location_country_code,
        location_lat=float(row.location_lat) if row.location_lat is not None else None,
        location_lon=float(row.location_lon) if row.location_lon is not None else None,
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
        deleted = repo.delete_goals_before(session, _today_local().isoformat())
        if deleted:
            session.commit()
        rows = repo.list_goals(session)
        return GoalsListResponse(goals=[_to_goal_item(row) for row in rows])
    finally:
        session.close()


@router.post("/goals", response_model=GoalItem)
async def create_goal(request: Request, payload: GoalCreateRequest):
    factory = _session_factory(request)
    repo = GoalsRepository()
    session = factory()

    target_time_s, target_pace_s_per_km = _validate_goal_values(
        distance_km=float(payload.distance_km),
        target_time_s=payload.target_time_s,
        target_pace_s_per_km=payload.target_pace_s_per_km,
    )
    event_date = _normalize_event_date(payload.event_date)
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    location = payload.location.strip() if isinstance(payload.location, str) else ""
    location_city = payload.location_city.strip() if isinstance(payload.location_city, str) else ""
    location_country = payload.location_country.strip() if isinstance(payload.location_country, str) else ""
    location_country_code = payload.location_country_code.strip().upper() if isinstance(payload.location_country_code, str) else ""
    location_lat = float(payload.location_lat) if payload.location_lat is not None else None
    location_lon = float(payload.location_lon) if payload.location_lon is not None else None
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
            location_city=location_city if location_city else None,
            location_country=location_country if location_country else None,
            location_country_code=location_country_code if location_country_code else None,
            location_lat=location_lat,
            location_lon=location_lon,
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


@router.patch("/goals/{goal_id}", response_model=GoalItem)
async def update_goal(request: Request, goal_id: str, payload: GoalUpdateRequest):
    factory = _session_factory(request)
    repo = GoalsRepository()
    session = factory()

    try:
        current = repo.get_goal(session, goal_id)
        if current is None:
            raise HTTPException(status_code=404, detail=f"Goal {goal_id} not found")

        patch = payload.model_dump(exclude_unset=True)

        name_raw = patch.get("name", current.name)
        name = str(name_raw).strip() if isinstance(name_raw, str) else ""
        if not name:
            raise HTTPException(status_code=400, detail="name is required")

        event_date_raw = patch.get("event_date", current.event_date)
        event_date = _normalize_event_date(str(event_date_raw))

        distance_km = float(patch.get("distance_km", current.distance_km))

        target_time_s_raw = patch.get("target_time_s", current.target_time_s)
        target_pace_raw = patch.get("target_pace_s_per_km", current.target_pace_s_per_km)

        target_time_s, target_pace_s_per_km = _validate_goal_values(
            distance_km=distance_km,
            target_time_s=float(target_time_s_raw) if target_time_s_raw is not None else None,
            target_pace_s_per_km=float(target_pace_raw) if target_pace_raw is not None else None,
        )

        race_type = patch.get("race_type", current.race_type)

        location_raw = patch.get("location", current.location)
        if location_raw is None:
            location = None
        else:
            location_clean = str(location_raw).strip()
            location = location_clean if location_clean else None

        location_city_raw = patch.get("location_city", current.location_city)
        if location_city_raw is None:
            location_city = None
        else:
            location_city_clean = str(location_city_raw).strip()
            location_city = location_city_clean if location_city_clean else None

        location_country_raw = patch.get("location_country", current.location_country)
        if location_country_raw is None:
            location_country = None
        else:
            location_country_clean = str(location_country_raw).strip()
            location_country = location_country_clean if location_country_clean else None

        location_country_code_raw = patch.get("location_country_code", current.location_country_code)
        if location_country_code_raw is None:
            location_country_code = None
        else:
            location_country_code_clean = str(location_country_code_raw).strip().upper()
            location_country_code = location_country_code_clean if location_country_code_clean else None

        location_lat_raw = patch.get("location_lat", current.location_lat)
        location_lat = float(location_lat_raw) if location_lat_raw is not None else None

        location_lon_raw = patch.get("location_lon", current.location_lon)
        location_lon = float(location_lon_raw) if location_lon_raw is not None else None

        notes_raw = patch.get("notes", current.notes)
        if notes_raw is None:
            notes = None
        else:
            notes_clean = str(notes_raw).strip()
            notes = notes_clean if notes_clean else None

        now_utc = utc_now_iso()
        updated = repo.update_goal(
            session,
            goal_id=goal_id,
            name=name,
            event_date=event_date,
            distance_km=distance_km,
            location=location,
            location_city=location_city,
            location_country=location_country,
            location_country_code=location_country_code,
            location_lat=location_lat,
            location_lon=location_lon,
            target_time_s=target_time_s,
            target_pace_s_per_km=target_pace_s_per_km,
            race_type=str(race_type),
            notes=notes,
            now_utc=now_utc,
        )
        if updated is None:
            raise HTTPException(status_code=404, detail=f"Goal {goal_id} not found")

        session.commit()
        session.refresh(updated)
        return _to_goal_item(updated)
    except HTTPException:
        raise
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update goal: {str(exc)}")
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


@router.delete("/goals")
async def delete_all_goals(request: Request):
    factory = _session_factory(request)
    repo = GoalsRepository()
    session = factory()
    try:
        deleted = repo.delete_all_goals(session)
        session.commit()
        return {"deleted": deleted}
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to cleanup goals: {str(exc)}")
    finally:
        session.close()
