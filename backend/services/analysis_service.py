"""Points d'entree backend de haut niveau (sans couche UI).

Ce module expose des points d'entree compatibles FastAPI qui travaillent sur
des bytes et renvoient des objets metier ou des payloads JSON-serialisables.

Ce module est consomme par l'API (FastAPI).
"""

from __future__ import annotations

import math
from dataclasses import asdict
from typing import Any, Literal

import numpy as np
import pandas as pd

from api.schemas import (
    ActivityLimitsDetail,
    RealActivityResponse,
    SeriesIndex,
)
from core.contracts.activity_df_contract import SCHEMA_VERSION
from core.utils import is_finite_number as _is_finite_number
from db.settings_repository import SettingsRepository
from registry.series_registry import SeriesRegistry
from services import activity_service, real_activity_service
from services.cache import KeyValueCache, NullCache, make_cache_key, sha256_bytes
from services.models import (
    LoadedActivity,
    RealRunParams,
    RealRunResult,
    RealRunViewParams,
)
from services.serialization import df_to_records, to_jsonable


def load_activity(
    *,
    data: bytes,
    name: str,
    activity_type: Literal["real", "theoretical"] | None = None,
    cache: KeyValueCache | None = None,
) -> LoadedActivity:
    cache = cache or NullCache()
    key = make_cache_key(
        namespace="activity:load",
        version=SCHEMA_VERSION,
        payload={
            "name": name,
            "sha256": sha256_bytes(data),
            "activity_type": activity_type,
        },
    )
    cached = cache.get(key)
    if isinstance(cached, LoadedActivity):
        return cached
    if activity_type == "real":
        force_type = "real_run"
    elif activity_type == "theoretical":
        force_type = "theoretical_route"
    else:
        force_type = None

    loaded = activity_service.load_activity_from_bytes(data=data, name=name, force_type=force_type)
    cache.set(key, loaded)
    return loaded


def analyze_real(
    *,
    loaded: LoadedActivity,
    params: RealRunParams | None = None,
    view: RealRunViewParams | None = None,
    cache: KeyValueCache | None = None,
) -> RealRunResult:
    cache = cache or NullCache()
    payload = {"name": loaded.name, "type": loaded.gpx_type.type, "confidence": loaded.gpx_type.confidence}
    if params is not None:
        payload["params"] = asdict(params)
    if view is not None:
        payload["view"] = asdict(view)
    key = make_cache_key(namespace="activity:real", version=SCHEMA_VERSION, payload=payload)
    cached = cache.get(key)
    if isinstance(cached, RealRunResult):
        return cached
    result = real_activity_service.analyze_real_activity(loaded.df, params=params, view=view)
    cache.set(key, result)
    return result


class AnalysisService:
    """Stateless service for analysis endpoint computations."""

    @staticmethod
    def build_cardio_summary(garmin: dict) -> dict | None:
        heart_rate = (garmin or {}).get("heart_rate")
        if not isinstance(heart_rate, dict):
            return None

        cardio: dict[str, float] = {}
        mapping = {
            "hr_avg_bpm": "mean_bpm",
            "hr_max_bpm": "max_bpm",
            "hr_min_bpm": "min_bpm",
        }
        for out_key, src_key in mapping.items():
            val = heart_rate.get(src_key)
            if _is_finite_number(val):
                cardio[out_key] = float(val)

        hr_max_used = heart_rate.get("hr_max_used")
        if _is_finite_number(hr_max_used):
            cardio["hr_max_used_bpm"] = float(hr_max_used)

        return cardio or None

    @staticmethod
    def resolve_hr_max_effective(request) -> float | None:
        db_session_factory = getattr(request.app.state, "db_session_factory", None)
        if db_session_factory is None:
            return None

        session = db_session_factory()
        repo = SettingsRepository()
        try:
            row = repo.get_or_create(session)
            detected = repo.get_detected_hr_max(session)
            session.commit()
            effective = detected if row.hr_max_source == "detected" and detected is not None else row.hr_max_manual_bpm
            if effective is None:
                return None
            try:
                numeric = float(effective)
            except Exception:
                return None
            if not math.isfinite(numeric) or numeric <= 0:
                return None
            return numeric
        except Exception:
            session.rollback()
            return None
        finally:
            session.close()

    @staticmethod
    def build_limits(df) -> ActivityLimitsDetail:
        return ActivityLimitsDetail(
            downsampled=False,
            original_points=len(df),
            returned_points=len(df),
            note=None,
        )

    @staticmethod
    def started_at_utc_from_df(activity_df: pd.DataFrame) -> str | None:
        if "time" not in activity_df.columns:
            return None
        try:
            value = pd.to_datetime(activity_df["time"], errors="coerce").min()
        except Exception:
            return None
        if value is None or pd.isna(value):
            return None
        ts = pd.Timestamp(value)
        if ts.tzinfo is not None:
            ts = ts.tz_convert("UTC").tz_localize(None)
        return ts.to_pydatetime().replace(microsecond=0).isoformat() + "Z"

    @staticmethod
    def build_real_response(
        request,
        activity_df,
        registry: SeriesRegistry,
        *,
        activity_name: str | None = None,
    ) -> RealActivityResponse:
        hr_max_effective = AnalysisService.resolve_hr_max_effective(request)
        params = RealRunParams(hr_max=hr_max_effective) if hr_max_effective is not None else None
        result = real_activity_service.analyze_real_activity(activity_df, params=params)
        series_index = SeriesIndex(available=registry.get_available_series(activity_df))

        zones = {}
        garmin = result.garmin or {}
        heart_rate = garmin.get("heart_rate")
        if heart_rate and heart_rate.get("zones") is not None:
            zones["heart_rate"] = heart_rate["zones"]
        if garmin.get("pace_zones") is not None:
            zones["pace"] = garmin["pace_zones"]
        power = garmin.get("power")
        if power and power.get("zones") is not None:
            zones["power"] = power["zones"]
        zones_payload = zones or None

        splits_rows = df_to_records(result.splits)
        splits_payload = {"rows": splits_rows} if splits_rows else None

        garmin_summary_payload = to_jsonable(garmin.get("summary")) if garmin.get("summary") else None
        cadence_payload = to_jsonable(garmin.get("cadence")) if garmin.get("cadence") else None
        power_payload = to_jsonable(garmin.get("power")) if garmin.get("power") else None
        running_dynamics_payload = (
            to_jsonable(garmin.get("running_dynamics")) if garmin.get("running_dynamics") else None
        )
        power_advanced_payload = to_jsonable(garmin.get("power_advanced")) if garmin.get("power_advanced") else None
        pacing_payload = to_jsonable(garmin.get("pacing")) if garmin.get("pacing") else None
        training_load_payload = to_jsonable(garmin.get("training_load")) if garmin.get("training_load") else None
        performance_predictions_payload = (
            {"items": to_jsonable(result.performance_predictions)}
            if result.performance_predictions
            else None
        )
        pauses_payload = {"items": to_jsonable(result.pauses)} if result.pauses else None
        climbs_payload = {"items": to_jsonable(result.climbs)} if result.climbs else None

        summary_payload = to_jsonable(result.summary) or {}
        cardio_payload = AnalysisService.build_cardio_summary(garmin)
        if cardio_payload is not None:
            summary_payload["cardio"] = cardio_payload

        return RealActivityResponse(
            activity_name=activity_name,
            started_at_utc=AnalysisService.started_at_utc_from_df(activity_df),
            summary=summary_payload,
            highlights={"items": result.highlights},
            zones=to_jsonable(zones_payload),
            best_efforts=None,
            personal_records=None,
            segment_analysis=None,
            performance_predictions=performance_predictions_payload,
            pauses=pauses_payload,
            climbs=climbs_payload,
            splits=splits_payload,
            garmin_summary=garmin_summary_payload,
            cadence=cadence_payload,
            power=power_payload,
            running_dynamics=running_dynamics_payload,
            power_advanced=power_advanced_payload,
            pacing=pacing_payload,
            training_load=training_load_payload,
            series_index=series_index,
            limits=None,
        )
