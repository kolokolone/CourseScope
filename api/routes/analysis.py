from fastapi import APIRouter, HTTPException, Request

from api.schemas import RealActivityResponse, SeriesIndex, ActivityLimitsDetail, TheoreticalActivityResponse
from registry.series_registry import SeriesRegistry
from services import real_activity_service, theoretical_service
from services.serialization import df_to_records, to_jsonable


router = APIRouter()


def get_series_registry(request: Request) -> SeriesRegistry:
    return request.app.state.registry


def _build_limits(df):
    return ActivityLimitsDetail(
        downsampled=False,
        original_points=len(df),
        returned_points=len(df),
        note=None,
    )


def prepare_real_response(activity_df, registry: SeriesRegistry) -> RealActivityResponse:
    result = real_activity_service.analyze_real_activity(activity_df)
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

    best_efforts_rows = df_to_records(result.best_efforts)
    best_efforts_payload = {"rows": best_efforts_rows} if best_efforts_rows else None

    pauses_payload = {"items": to_jsonable(result.pauses)} if result.pauses else None
    climbs_payload = {"items": to_jsonable(result.climbs)} if result.climbs else None

    return RealActivityResponse(
        summary=to_jsonable(result.summary),
        highlights={"items": result.highlights},
        zones=to_jsonable(zones_payload),
        best_efforts=best_efforts_payload,
        pauses=pauses_payload,
        climbs=climbs_payload,
        series_index=series_index,
        limits=_build_limits(activity_df),
    )


def prepare_theoretical_response(activity_df, registry: SeriesRegistry) -> TheoreticalActivityResponse:
    base_pace_s_per_km = 300.0
    df_theoretical, summary_base = theoretical_service.prepare_base(activity_df, base_pace_s_per_km)
    _ = df_theoretical

    series_index = SeriesIndex(available=registry.get_available_series(activity_df))

    return TheoreticalActivityResponse(
        summary=to_jsonable(summary_base),
        highlights={},
        zones=None,
        best_efforts=None,
        pauses=None,
        climbs=None,
        series_index=series_index,
        limits=_build_limits(activity_df),
    )


@router.get("/activity/{activity_id}/real", response_model=RealActivityResponse)
async def get_real_activity(request: Request, activity_id: str):
    """Retourne les données d'analyse pour une activité réelle"""
    try:
        storage = request.app.state.storage
        df = storage.load_dataframe(activity_id)

        if df.empty:
            raise HTTPException(status_code=404, detail=f"Activity {activity_id} not found")

        registry = get_series_registry(request)
        return prepare_real_response(df, registry)

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Activity {activity_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get real activity: {str(e)}")


@router.get("/activity/{activity_id}/theoretical", response_model=TheoreticalActivityResponse)
async def get_theoretical_activity(request: Request, activity_id: str):
    """Retourne les données d'analyse pour une activité théorique"""
    try:
        storage = request.app.state.storage
        df = storage.load_dataframe(activity_id)

        if df.empty:
            raise HTTPException(status_code=404, detail=f"Activity {activity_id} not found")

        registry = get_series_registry(request)
        return prepare_theoretical_response(df, registry)

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Activity {activity_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get theoretical activity: {str(e)}")
