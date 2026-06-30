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
    TheoreticalActivityResponse,
)
from core._shared import compute_elevation_gain, compute_elevation_loss
from core.contracts.activity_df_contract import SCHEMA_VERSION
from core.grade_table import grade_factor
from core.theoretical_segments import (
    build_grade_time_bins,
    build_pace_time_bins,
    build_theoretical_segments,
    compute_secondary_metrics,
)
from core.utils import is_finite_number as _is_finite_number, parse_hms_to_seconds, parse_pace_to_seconds_per_km
from db.settings_repository import SettingsRepository
from db.trace_repository import TraceRepository
from registry.series_registry import SeriesRegistry
from services import activity_service, real_activity_service, theoretical_service
from services.cache import KeyValueCache, NullCache, make_cache_key, sha256_bytes
from services.models import (
    LoadedActivity,
    RealRunParams,
    RealRunResult,
    RealRunViewParams,
    TheoreticalBase,
    TheoreticalFigures,
    TheoreticalParams,
    TheoreticalResult,
)
from services.serialization import df_to_records, to_jsonable
from storage.trace_store import compute_route_fingerprint


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


def analyze_theoretical(
    *,
    loaded: LoadedActivity,
    params: TheoreticalParams,
    cache: KeyValueCache | None = None,
) -> TheoreticalResult:
    cache = cache or NullCache()
    payload: dict[str, Any] = {
        "name": loaded.name,
        "type": loaded.gpx_type.type,
        "confidence": loaded.gpx_type.confidence,
        "params": asdict(params),
    }
    key = make_cache_key(namespace="activity:theoretical", version=SCHEMA_VERSION, payload=payload)
    cached = cache.get(key)
    if isinstance(cached, TheoreticalResult):
        return cached

    df_base, summary_base = theoretical_service.prepare_base(loaded.df, params.base_pace_s_per_km)
    df_display, default_cap_min, _used_cap_min = theoretical_service.compute_display_df(
        df_base,
        smoothing_segments=params.smoothing_segments,
        cap_min_per_km=params.cap_min_per_km,
    )

    base = TheoreticalBase(df_base=df_base, summary_base=summary_base, default_cap_min_per_km=default_cap_min)
    passages = theoretical_service.compute_passages(
        df_base,
        start_datetime=params.start_datetime,
        target_distances_km=params.passage_distances_km,
    )
    fig_base = theoretical_service.build_base_figure(df_display, markers=passages.markers)
    splits = theoretical_service.compute_splits(
        passages.df_calc,
        start_datetime=params.start_datetime,
        split_distance_km=1.0,
    )

    figures = TheoreticalFigures(base=fig_base, advanced=advanced.figure)
    result = TheoreticalResult(
        base=base,
        df_display=df_display,
        passages=passages,
        splits=splits,
        figures=figures,
        advanced=advanced,
    )

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
    def resolve_vma_kmh(request, vma_kmh: float | None = None) -> float:
        if isinstance(vma_kmh, (int, float)) and math.isfinite(float(vma_kmh)) and float(vma_kmh) > 0:
            return float(vma_kmh)

        db_session_factory = getattr(request.app.state, "db_session_factory", None)
        if db_session_factory is None:
            return 16.0

        session = db_session_factory()
        repo = SettingsRepository()
        try:
            row = repo.get_or_create(session)
            session.commit()
            if row.vma_kmh is not None and math.isfinite(float(row.vma_kmh)) and float(row.vma_kmh) > 0:
                return float(row.vma_kmh)
        except Exception:
            session.rollback()
        finally:
            session.close()
        return 16.0

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
    def resolve_target_pace_and_time(
        *,
        activity_df: pd.DataFrame,
        target_mode: str,
        target_pace: str | None,
        target_time: str | None,
    ) -> tuple[str, float, float]:
        distance_m = pd.to_numeric(activity_df.get("distance_m"), errors="coerce") if "distance_m" in activity_df.columns else pd.Series(dtype=float)
        distance_clean = distance_m.dropna()
        total_distance_km = float(distance_clean.iloc[-1] / 1000.0) if not distance_clean.empty else 0.0
        total_distance_km = total_distance_km if total_distance_km > 0 else 1.0

        mode = "time" if str(target_mode).lower() == "time" else "pace"
        pace_s = parse_pace_to_seconds_per_km(target_pace)
        time_s = parse_hms_to_seconds(target_time)

        if mode == "time" and time_s is not None and time_s > 0:
            pace_s = max(120.0, min(1200.0, float(time_s / total_distance_km)))
        elif mode == "pace" and pace_s is not None and pace_s > 0:
            time_s = float(pace_s * total_distance_km)

        if pace_s is None or not math.isfinite(pace_s) or pace_s <= 0:
            pace_s = 300.0
            time_s = float(pace_s * total_distance_km)
            mode = "pace"

        if time_s is None or not math.isfinite(time_s) or time_s <= 0:
            time_s = float(pace_s * total_distance_km)

        return mode, float(pace_s), float(time_s)

    @staticmethod
    def resolve_trace_status(request, activity_df: pd.DataFrame) -> dict:
        db_session_factory = getattr(request.app.state, "db_session_factory", None)
        if db_session_factory is None:
            return {"saved": False}

        fingerprint = compute_route_fingerprint(activity_df)
        if not fingerprint:
            return {"saved": False}

        session = db_session_factory()
        repo = TraceRepository()
        try:
            row = repo.get_by_route_fingerprint(session, fingerprint)
            if row is None:
                return {"saved": False}
            return {"saved": True, "trace_id": row.id, "trace_name": row.name}
        finally:
            session.close()

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

    @staticmethod
    def build_theoretical_response(
        request,
        activity_df: pd.DataFrame,
        registry: SeriesRegistry,
        *,
        target_mode: str,
        target_pace: str | None,
        target_time: str | None,
        vma_kmh: float | None,
        grade_model: str,
    ) -> TheoreticalActivityResponse:
        resolved_mode, target_pace_s, target_time_s = AnalysisService.resolve_target_pace_and_time(
            activity_df=activity_df,
            target_mode=target_mode,
            target_pace=target_pace,
            target_time=target_time,
        )
        effective_vma = AnalysisService.resolve_vma_kmh(request, vma_kmh)

        df_segments = build_theoretical_segments(
            activity_df,
            target_pace_flat_s_per_km=target_pace_s,
            vma_kmh=effective_vma,
            grade_model=grade_model,
        )

        distance_km = float(df_segments["distance_km"].iloc[-1]) if not df_segments.empty else 0.0
        estimated_time_s = float(df_segments["cumulative_time_s"].iloc[-1]) if not df_segments.empty else 0.0
        average_pace_s_per_km = (estimated_time_s / distance_km) if distance_km > 0 else target_pace_s

        elevation = pd.to_numeric(df_segments["elevation_m"], errors="coerce").dropna().to_numpy(dtype=float)
        elev_gain = compute_elevation_gain(elevation)
        elev_loss = compute_elevation_loss(elevation)

        summary = {
            "distance_km": distance_km,
            "elevation_gain_m": elev_gain,
            "elevation_loss_m": elev_loss,
            "d_plus_per_km": (elev_gain / distance_km) if distance_km > 0 else None,
            "target_pace_s_per_km": target_pace_s,
            "estimated_time_s": estimated_time_s,
            "total_time_s": estimated_time_s,
            "total_distance_km": distance_km,
            "average_pace_s_per_km": average_pace_s_per_km,
        }
        if elevation.size > 0:
            summary["elevation_min_m"] = float(np.min(elevation))
            summary["elevation_max_m"] = float(np.max(elevation))

        pace_series = [
            {
                "distance_km": float(row.distance_km),
                "target_pace_s_per_km": float(row.target_pace_s_per_km),
                "elevation_m": float(row.elevation_m) if row.elevation_m == row.elevation_m else None,
            }
            for row in df_segments.itertuples(index=False)
        ]

        series_index = SeriesIndex(available=registry.get_available_series(activity_df))
        trace_status = AnalysisService.resolve_trace_status(request, activity_df)

        return TheoreticalActivityResponse(
            summary=to_jsonable(summary),
            highlights={"items": []},
            zones=None,
            best_efforts=None,
            personal_records=None,
            segment_analysis=None,
            performance_predictions=None,
            pauses=None,
            climbs=None,
            splits=None,
            garmin_summary=None,
            cadence=None,
            power=None,
            running_dynamics=None,
            power_advanced=None,
            pacing=None,
            training_load=None,
            series_index=series_index,
            limits=AnalysisService.build_limits(activity_df),
            target_mode=resolved_mode,
            target_pace_s_per_km=target_pace_s,
            target_time_s=target_time_s,
            vma_kmh=effective_vma,
            pace_elevation_series=pace_series,
            grade_time_bins=build_grade_time_bins(df_segments),
            pace_time_bins=build_pace_time_bins(df_segments),
            secondary_metrics=compute_secondary_metrics(df_segments),
            trace_status=trace_status,
        )
