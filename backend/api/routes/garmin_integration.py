from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from config import get_garmin_tokens_dir
from db.repository import ActivityIndexRepository
from integrations.garmin.client import GarminAuthError, GarminMfaState, resume_login_with_otp, start_login, connect_with_tokens
from integrations.garmin.credentials_store import credentials_status, load_credentials, save_credentials
from integrations.garmin.sync_service import GarminSyncService


logger = logging.getLogger("coursescope")

router = APIRouter()


class GarminConnectRequest(BaseModel):
    email: str | None = None
    password: str | None = None
    otp: str | None = None
    mfa_session_id: str | None = None


class GarminCredentialsRequest(BaseModel):
    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class GarminConnectResponse(BaseModel):
    status: str
    mfa_session_id: str | None = None


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
    cursor_updated_at_utc: str | None = None
    last_run: dict | None = None


class GarminCredentialsStatusResponse(BaseModel):
    configured: bool
    email: str | None
    path: str


class GarminResetResponse(BaseModel):
    status: str
    deleted_sources: int
    deleted_cursor: int


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
async def garmin_connect(request: Request, req: GarminConnectRequest):
    try:
        # Resume MFA flow if requested.
        if req.mfa_session_id and req.otp:
            store = getattr(request.app.state, "garmin_mfa_states", {})
            state = store.get(req.mfa_session_id)
            if not isinstance(state, GarminMfaState):
                raise HTTPException(status_code=400, detail="Invalid or expired mfa_session_id")
            resume_login_with_otp(mfa_state=state, otp=req.otp)
            try:
                store.pop(req.mfa_session_id, None)
            except Exception:
                pass
            return GarminConnectResponse(status="ok", mfa_session_id=None)

        email = req.email
        password = req.password
        if not email or not password:
            saved = load_credentials()
            if saved is None:
                raise HTTPException(status_code=400, detail="Missing credentials and no saved credentials")
            email = saved.email
            password = saved.password

        mfa_state = start_login(email=email, password=password)
        if mfa_state is not None:
            session_id = str(uuid.uuid4())
            store = getattr(request.app.state, "garmin_mfa_states", None)
            if not isinstance(store, dict):
                raise HTTPException(status_code=500, detail="MFA store not initialized")
            store[session_id] = mfa_state
            return GarminConnectResponse(status="otp_required", mfa_session_id=session_id)

        return GarminConnectResponse(status="ok", mfa_session_id=None)
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
    from anyio.to_thread import run_sync

    result = await run_sync(service.sync)
    return GarminSyncResponse(**result.__dict__)


@router.post("/integrations/garmin/reset", response_model=GarminResetResponse)
async def garmin_reset(request: Request):
    """Reset Garmin sync cursor and source mappings.

    Use this before a full resync.
    """

    db_session_factory = getattr(request.app.state, "db_session_factory", None)
    if db_session_factory is None:
        raise HTTPException(status_code=500, detail="DB not initialized")

    repo = ActivityIndexRepository()
    session = db_session_factory()
    try:
        deleted_sources = repo.delete_activity_sources_by_source(session, "garmin")
        deleted_cursor = repo.delete_sync_state(session, "garmin")
        session.commit()
        return GarminResetResponse(status="ok", deleted_sources=deleted_sources, deleted_cursor=deleted_cursor)
    finally:
        session.close()


@router.get("/integrations/garmin/status", response_model=GarminStatusResponse)
async def garmin_status(request: Request):
    tokens_dir = get_garmin_tokens_dir().resolve()
    present = _tokens_present(tokens_dir)

    db_session_factory = getattr(request.app.state, "db_session_factory", None)
    cursor = None
    cursor_updated_at_utc = None
    last_run_payload = None
    if db_session_factory is not None:
        repo = ActivityIndexRepository()
        session = db_session_factory()
        try:
            state = repo.get_sync_state(session, "garmin")
            if state is not None:
                cursor = state.cursor_time_utc
                cursor_updated_at_utc = state.updated_at_utc
            last_run = repo.get_last_sync_run(session, "garmin")
            if last_run is not None:
                duration_s = None
                try:
                    if last_run.finished_at_utc:
                        a = datetime.fromisoformat(last_run.started_at_utc.replace("Z", "+00:00"))
                        b = datetime.fromisoformat(last_run.finished_at_utc.replace("Z", "+00:00"))
                        duration_s = int((b - a).total_seconds())
                except Exception:
                    duration_s = None
                last_run_payload = {
                    "id": last_run.id,
                    "source": last_run.source,
                    "started_at_utc": last_run.started_at_utc,
                    "finished_at_utc": last_run.finished_at_utc,
                    "status": last_run.status,
                    "imported_count": last_run.imported_count,
                    "skipped_count": last_run.skipped_count,
                    "processed_count": int(last_run.imported_count) + int(last_run.skipped_count),
                    "duration_s": duration_s,
                    "error": last_run.error,
                }
        finally:
            session.close()

    return GarminStatusResponse(
        tokens_present=present,
        tokens_dir=str(tokens_dir),
        cursor_time_utc=cursor,
        cursor_updated_at_utc=cursor_updated_at_utc,
        last_run=last_run_payload,
    )


@router.get(
    "/integrations/garmin/credentials/status",
    response_model=GarminCredentialsStatusResponse,
)
async def garmin_credentials_status():
    return GarminCredentialsStatusResponse(**credentials_status())


@router.post(
    "/integrations/garmin/credentials",
    response_model=GarminCredentialsStatusResponse,
)
async def garmin_save_credentials(req: GarminCredentialsRequest):
    try:
        save_credentials(email=req.email, password=req.password)
        return GarminCredentialsStatusResponse(**credentials_status())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
