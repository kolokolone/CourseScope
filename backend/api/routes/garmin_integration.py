from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from config import get_garmin_tokens_dir
from db.repository import ActivityIndexRepository
from integrations.garmin.client import GarminAuthError, connect_and_save_tokens, connect_with_tokens
from integrations.garmin.sync_service import GarminSyncService


logger = logging.getLogger("coursescope")

router = APIRouter()


class GarminConnectRequest(BaseModel):
    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    otp: str | None = None


class GarminConnectResponse(BaseModel):
    status: str
    tokens_dir: str


class GarminSyncResponse(BaseModel):
    run_id: str
    status: str
    imported_count: int
    skipped_count: int
    cursor_time_utc: str | None
    error: str | None = None


class GarminStatusResponse(BaseModel):
    tokens_present: bool
    tokens_dir: str
    cursor_time_utc: str | None
    last_run: dict | None = None


def _tokens_present(tokens_dir: Path) -> bool:
    if not tokens_dir.exists() or not tokens_dir.is_dir():
        return False
    try:
        for p in tokens_dir.iterdir():
            if p.is_file() and p.stat().st_size > 0:
                return True
    except Exception:
        return False
    return False


@router.post("/integrations/garmin/connect", response_model=GarminConnectResponse)
async def garmin_connect(req: GarminConnectRequest):
    try:
        connect_and_save_tokens(
            email=req.email,
            password=req.password,
            mfa_callback=(lambda: req.otp) if req.otp else None,
        )
        tokens_dir = get_garmin_tokens_dir().resolve()
        return GarminConnectResponse(status="ok", tokens_dir=str(tokens_dir))
    except GarminAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Garmin connect failed: {exc}")


@router.post("/integrations/garmin/sync", response_model=GarminSyncResponse)
async def garmin_sync(request: Request):
    try:
        garmin = connect_with_tokens()
    except GarminAuthError as exc:
        raise HTTPException(status_code=401, detail=f"reauth_required: {exc}")

    storage = request.app.state.storage
    db_session_factory = getattr(request.app.state, "db_session_factory", None)
    if db_session_factory is None:
        raise HTTPException(status_code=500, detail="DB not initialized")

    service = GarminSyncService(
        garmin_client=garmin,
        storage=storage,
        db_session_factory=db_session_factory,
    )
    result = service.sync()
    return GarminSyncResponse(**result.__dict__)


@router.get("/integrations/garmin/status", response_model=GarminStatusResponse)
async def garmin_status(request: Request):
    tokens_dir = get_garmin_tokens_dir().resolve()
    present = _tokens_present(tokens_dir)

    db_session_factory = getattr(request.app.state, "db_session_factory", None)
    cursor = None
    last_run_payload = None
    if db_session_factory is not None:
        repo = ActivityIndexRepository()
        session = db_session_factory()
        try:
            cursor = repo.get_cursor(session, "garmin")
            last_run = repo.get_last_sync_run(session, "garmin")
            if last_run is not None:
                last_run_payload = {
                    "id": last_run.id,
                    "source": last_run.source,
                    "started_at_utc": last_run.started_at_utc,
                    "finished_at_utc": last_run.finished_at_utc,
                    "status": last_run.status,
                    "imported_count": last_run.imported_count,
                    "skipped_count": last_run.skipped_count,
                    "error": last_run.error,
                }
        finally:
            session.close()

    return GarminStatusResponse(
        tokens_present=present,
        tokens_dir=str(tokens_dir),
        cursor_time_utc=cursor,
        last_run=last_run_payload,
    )
