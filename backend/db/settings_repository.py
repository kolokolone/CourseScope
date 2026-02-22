from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import ProgressActivityIndex, UserSettings, utc_now_iso


class SettingsRepository:
    def get_or_create(self, session: Session) -> UserSettings:
        row = session.get(UserSettings, 1)
        if row is None:
            row = UserSettings(
                id=1,
                vma_kmh=None,
                vo2max_lastest=None,
                hr_max_manual_bpm=None,
                hr_max_source="detected",
                updated_at_utc=utc_now_iso(),
            )
            session.add(row)
            session.flush()
        return row

    def get_detected_hr_max(self, session: Session) -> int | None:
        stmt = select(func.max(ProgressActivityIndex.max_hr_bpm))
        value = session.execute(stmt).scalar_one_or_none()
        if value is None:
            return None
        try:
            numeric = int(round(float(value)))
        except Exception:
            return None
        if numeric <= 0:
            return None
        return numeric
