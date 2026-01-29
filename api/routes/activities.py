from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Header, Request
from typing import Optional

from api.schemas import ActivityLoadResponse, SidebarStats, ActivityLimits
from services.analysis_service import load_activity
from storage.activity_store import LocalTempStorage


router = APIRouter()


def get_activity_storage(request: Request) -> LocalTempStorage:
    return request.app.state.storage


def _model_to_dict(model):
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def check_dataframe_limits(df) -> ActivityLimits:
    original_points = len(df)

    if original_points > 10000:
        return ActivityLimits(
            downsampled=True,
            dataframe_limit=10000,
            note=f"Large dataset ({original_points} points). Consider downsampling.",
        )

    return ActivityLimits(
        downsampled=False,
        dataframe_limit=original_points,
    )


@router.post("/activity/load", response_model=ActivityLoadResponse)
async def load_activity_endpoint(
    request: Request,
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    max_size: int = Header(100_000_000),
):
    """Charge une activité GPX/FIT et retourne son ID"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    allowed_extensions = {".gpx", ".fit"}
    if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file extension. Allowed: {', '.join(sorted(allowed_extensions))}",
        )

    file_bytes = await file.read()
    if len(file_bytes) > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {max_size / (1024 * 1024):.1f}MB",
        )

    try:
        display_name = name or file.filename
        activity = load_activity(data=file_bytes, name=display_name)

        storage = get_activity_storage(request)
        activity_id = storage.store(activity, file.filename, file_bytes, name=name)

        stats = storage._compute_sidebar_stats(activity.df)
        limits = check_dataframe_limits(activity.df)

        return ActivityLoadResponse(
            id=activity_id,
            type=activity.type,
            stats_sidebar=SidebarStats(**_model_to_dict(stats)),
            limits=limits,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load activity: {str(e)}")


@router.get("/activities")
async def list_activities(request: Request):
    """Liste toutes les activités stockées"""
    try:
        storage = get_activity_storage(request)
        activities = storage.list_activities()
        return {"activities": [_model_to_dict(activity) for activity in activities]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list activities: {str(e)}")


@router.delete("/activity/{activity_id}")
async def delete_activity(request: Request, activity_id: str):
    """Supprime une activité"""
    try:
        storage = get_activity_storage(request)
        success = storage.delete(activity_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Activity {activity_id} not found")

        return {"message": f"Activity {activity_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete activity: {str(e)}")


@router.delete("/activities")
async def cleanup_all_activities(request: Request):
    """Supprime toutes les activités (vidage)"""
    try:
        storage = get_activity_storage(request)
        storage.cleanup_all()
        return {"message": "All activities cleaned up successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cleanup activities: {str(e)}")
