from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .models import Goal


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
            target_time_s=target_time_s,
            target_pace_s_per_km=target_pace_s_per_km,
            race_type=race_type,
            notes=notes,
            created_at_utc=now_utc,
            updated_at_utc=now_utc,
        )
        session.add(row)
        return row

    def delete_goal(self, session: Session, goal_id: str) -> bool:
        res = session.execute(delete(Goal).where(Goal.id == goal_id))
        return bool(getattr(res, "rowcount", 0) or 0)
