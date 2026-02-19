from pathlib import Path
import hashlib

import logging

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Header, Request
from typing import Optional, Literal, cast

from api.schemas import ActivityLoadResponse, SidebarStats, ActivityLimits
from services.analysis_service import load_activity
from storage.activity_store import LocalTempStorage
from db.repository import ActivityIndexRepository


router = APIRouter()


def _get_logger(request: Request) -> logging.Logger:
    return request.app.state.logger


def _get_request_id(request: Request) -> str:
    return getattr(getattr(request, "state", None), "request_id", "-")


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
    activity_type: Literal["real", "theoretical"] | None = Form(None),
    max_size: int = Header(100_000_000),
):
    """Charge une activité GPX/FIT et retourne son ID"""
    logger = _get_logger(request)
    request_id = _get_request_id(request)

    logger.info(
        "upload_request_received",
        extra={
            "request_id": request_id,
            "upload_filename": file.filename,
            "upload_content_type": file.content_type,
            "upload_name": name,
        },
    )
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    allowed_extensions = {".gpx", ".fit"}
    if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file extension. Allowed: {', '.join(sorted(allowed_extensions))}",
        )

    file_bytes = await file.read()
    logger.info(
        "upload_file_read",
        extra={
            "request_id": request_id,
            "upload_filename": file.filename,
            "extension": Path(file.filename).suffix.lower(),
            "size_bytes": len(file_bytes),
            "max_size": max_size,
        },
    )
    if len(file_bytes) > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {max_size / (1024 * 1024):.1f}MB",
        )

    try:
        display_name = name or file.filename
        suffix = Path(file.filename).suffix
        parse_name = display_name
        if suffix and not display_name.lower().endswith(suffix.lower()):
            parse_name = f"{display_name}{suffix}"

        logger.info(
            "upload_parse_start",
            extra={
                "request_id": request_id,
                "parse_name": parse_name,
                "display_name": display_name,
                "upload_filename": file.filename,
                "activity_type": activity_type,
            },
        )
        activity = load_activity(data=file_bytes, name=parse_name, activity_type=activity_type)

        storage = get_activity_storage(request)

        file_hash = hashlib.sha256(file_bytes).hexdigest()
        existing_id = getattr(storage, "get_activity_id_by_hash", lambda _h: None)(file_hash)
        if existing_id is not None:
            activity_id = existing_id
        else:
            activity_id = storage.store(activity, file.filename, file_bytes, name=display_name)

        logger.info(
            "upload_store_ok",
            extra={
                "request_id": request_id,
                "activity_id": activity_id,
                "activity_type": getattr(activity, "type", None),
            },
        )
        df = activity.df
        if df is None:
            raise RuntimeError("Loaded activity missing DataFrame")
        stats = storage._compute_sidebar_stats(df)
        limits = check_dataframe_limits(df)

        logger.info(
            "upload_success",
            extra={
                "request_id": request_id,
                "activity_id": activity_id,
                "activity_type": getattr(activity, "type", None),
            },
        )
        chosen_type: Literal["real", "theoretical"]
        if activity_type is not None:
            chosen_type = cast(Literal["real", "theoretical"], activity_type)
        else:
            chosen_type = cast(
                Literal["real", "theoretical"],
                "real" if activity.gpx_type.type == "real_run" else "theoretical",
            )

        return ActivityLoadResponse(
            id=activity_id,
            type=chosen_type,
            stats_sidebar=SidebarStats(**_model_to_dict(stats)),
            limits=limits,
        )
    except ValueError as e:
        # Contract validation errors should be a client error.
        logger.warning(
            "upload_validation_failed",
            extra={
                "request_id": request_id,
                "error": str(e),
                "upload_filename": file.filename,
            },
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(
            "upload_failed",
            extra={
                "request_id": request_id,
                "upload_filename": file.filename,
                "upload_content_type": file.content_type,
            },
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load activity (request_id={request_id})",
        )


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

        # Also clear the DB index so Garmin/manual activities can be re-imported cleanly.
        db_session_factory = getattr(request.app.state, "db_session_factory", None)
        if db_session_factory is not None:
            repo = ActivityIndexRepository()
            session = db_session_factory()
            try:
                repo.delete_all_activities(session)
                repo.delete_sync_state(session, "garmin")
                session.commit()
            finally:
                session.close()

        return {"message": "All activities cleaned up successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cleanup activities: {str(e)}")
