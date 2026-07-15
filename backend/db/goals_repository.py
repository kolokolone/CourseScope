from __future__ import annotations

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from .models import Goal, RacePlan


class GoalsRepository:
    def list_goals(self, session: Session) -> list[Goal]:
        stmt = select(Goal).order_by(Goal.event_date.asc(), Goal.created_at_utc.asc())
        return list(session.execute(stmt).scalars().all())

    def create_goal(
        self,
        session: Session,
        *,
        goal_id: str,
        name: str,
        event_date: str,
        distance_km: float,
        location: str | None,
        location_city: str | None,
        location_country: str | None,
        location_country_code: str | None,
        location_lat: float | None,
        location_lon: float | None,
        target_time_s: float | None,
        target_pace_s_per_km: float | None,
        race_type: str,
        notes: str | None,
        now_utc: str,
    ) -> Goal:
        row = Goal(
            id=goal_id,
            name=name,
            event_date=event_date,
            distance_km=float(distance_km),
            location=location,
            location_city=location_city,
            location_country=location_country,
            location_country_code=location_country_code,
            location_lat=location_lat,
            location_lon=location_lon,
            target_time_s=target_time_s,
            target_pace_s_per_km=target_pace_s_per_km,
            race_type=race_type,
            notes=notes,
            created_at_utc=now_utc,
            updated_at_utc=now_utc,
        )
        session.add(row)
        return row

    def get_goal(self, session: Session, goal_id: str) -> Goal | None:
        return session.get(Goal, goal_id)

    def delete_goals_before(self, session: Session, event_date: str) -> int:
        expired_goal_ids = select(Goal.id).where(Goal.event_date < event_date)
        session.execute(
            update(RacePlan)
            .where(RacePlan.goal_id.in_(expired_goal_ids))
            .values(goal_id=None)
        )
        res = session.execute(delete(Goal).where(Goal.event_date < event_date))
        return int(getattr(res, "rowcount", 0) or 0)

    def update_goal(
        self,
        session: Session,
        *,
        goal_id: str,
        name: str,
        event_date: str,
        distance_km: float,
        location: str | None,
        location_city: str | None,
        location_country: str | None,
        location_country_code: str | None,
        location_lat: float | None,
        location_lon: float | None,
        target_time_s: float | None,
        target_pace_s_per_km: float | None,
        race_type: str,
        notes: str | None,
        now_utc: str,
    ) -> Goal | None:
        row = self.get_goal(session, goal_id)
        if row is None:
            return None

        row.name = name
        row.event_date = event_date
        row.distance_km = float(distance_km)
        row.location = location
        row.location_city = location_city
        row.location_country = location_country
        row.location_country_code = location_country_code
        row.location_lat = location_lat
        row.location_lon = location_lon
        row.target_time_s = target_time_s
        row.target_pace_s_per_km = target_pace_s_per_km
        row.race_type = race_type
        row.notes = notes
        row.updated_at_utc = now_utc
        return row

    def delete_goal(self, session: Session, goal_id: str) -> bool:
        session.execute(update(RacePlan).where(RacePlan.goal_id == goal_id).values(goal_id=None))
        res = session.execute(delete(Goal).where(Goal.id == goal_id))
        return bool(getattr(res, "rowcount", 0) or 0)

    def delete_all_goals(self, session: Session) -> int:
        session.execute(update(RacePlan).where(RacePlan.goal_id.is_not(None)).values(goal_id=None))
        res = session.execute(delete(Goal))
        return int(getattr(res, "rowcount", 0) or 0)
