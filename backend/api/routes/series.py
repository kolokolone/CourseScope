from fastapi import APIRouter, Query, HTTPException, Request
from typing import Optional, Literal

from api._helpers import _model_to_dict, get_series_registry, resolve_activity_df
from api.schemas import SeriesResponse


router = APIRouter()


@router.get("/activity/{activity_id}/series/{series_name}", response_model=SeriesResponse)
async def get_series(
    request: Request,
    activity_id: str,
    series_name: str,
    x_axis: Literal["time", "distance"] = Query("time", description="X axis type"),
    from_val: Optional[float] = Query(None, alias="from", description="Start value in x_axis units"),
    to_val: Optional[float] = Query(None, alias="to", description="End value in x_axis units"),
    downsample: Optional[int] = Query(None, description="Max points after downsampling"),
):
    """Retourne les données d'une série spécifique avec slicing et downsampling"""
    try:
        df = resolve_activity_df(request, activity_id)

        registry = get_series_registry(request)
        series_response = registry.get_series_data(
            df=df,
            name=series_name,
            x_axis=x_axis,
            from_val=from_val,
            to_val=to_val,
            downsample=downsample,
        )

        return series_response

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Activity {activity_id} not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get series {series_name}: {str(e)}")


@router.get("/activity/{activity_id}/series")
async def list_available_series(request: Request, activity_id: str):
    """Liste toutes les séries disponibles pour une activité"""
    try:
        df = resolve_activity_df(request, activity_id)

        registry = get_series_registry(request)
        available_series = registry.get_available_series(df)

        return {
            "activity_id": activity_id,
            "series": [_model_to_dict(series) for series in available_series],
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Activity {activity_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list series: {str(e)}")
