"""Conservative calibration suggestions based on persisted real activities."""

from __future__ import annotations

import math

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import ProgressActivityIndex


def suggest_calibration_factor(
    session: Session,
    *,
    reference_pace_s_per_km: float,
    course_gain_per_km: float,
    minimum_samples: int = 3,
) -> dict[str, object]:
    statement = (
        select(ProgressActivityIndex)
        .where(
            ProgressActivityIndex.activity_type == "real",
            ProgressActivityIndex.avg_pace_s_per_km.is_not(None),
            ProgressActivityIndex.distance_m.is_not(None),
            ProgressActivityIndex.distance_m >= 5_000,
        )
        .order_by(ProgressActivityIndex.start_ts_utc.desc())
        .limit(40)
    )
    rows = list(session.execute(statement).scalars().all())
    comparable: list[float] = []
    for row in rows:
        pace = float(row.avg_pace_s_per_km or 0.0)
        distance_km = float(row.distance_m or 0.0) / 1000.0
        gain_per_km = float(row.elevation_gain_m or 0.0) / distance_km if distance_km > 0 else 0.0
        tolerance = max(20.0, abs(course_gain_per_km) * 0.65)
        if math.isfinite(pace) and pace > 0 and abs(gain_per_km - course_gain_per_km) <= tolerance:
            comparable.append(pace)
    if len(comparable) < minimum_samples:
        return {
            "status": "insufficient_data",
            "sample_count": len(comparable),
            "minimum_samples": minimum_samples,
            "recommended_calibration_factor": None,
            "method": "median_pace_on_comparable_real_activities",
        }
    median_pace = float(np.median(comparable))
    factor = float(np.clip(median_pace / reference_pace_s_per_km, 0.75, 1.35))
    return {
        "status": "available",
        "sample_count": len(comparable),
        "minimum_samples": minimum_samples,
        "median_historical_pace_s_per_km": median_pace,
        "recommended_calibration_factor": factor,
        "method": "median_pace_on_comparable_real_activities",
    }
