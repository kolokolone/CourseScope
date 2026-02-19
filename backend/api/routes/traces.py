from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from api.schemas import TraceItem, TraceStatusResponse, TracesListResponse, TraceUploadResponse
from db.models import Trace, utc_now_iso
from db.trace_repository import TraceCreatePayload, TraceRepository
from services.analysis_service import load_activity
from storage.trace_store import TraceStore, compute_route_fingerprint, compute_trace_metrics, format_trace_name
from traces.verify_traces import verify_traces


router = APIRouter()


def _get_db_session_factory(request: Request):
    factory = getattr(request.app.state, "db_session_factory", None)
    if factory is None:
        raise HTTPException(status_code=500, detail="DB not initialized")
    return factory


def _get_trace_store(request: Request) -> TraceStore:
    trace_store = getattr(request.app.state, "trace_store", None)
    if trace_store is None:
        raise HTTPException(status_code=500, detail="Trace store not initialized")
    return trace_store


def _to_trace_item(row: Trace) -> TraceItem:
    return TraceItem(
        id=row.id,
        name=row.name,
        created_at_utc=row.created_at_utc,
        distance_km=float(row.distance_km or 0.0),
        elevation_gain_m=float(row.elevation_gain_m or 0.0),
        elevation_loss_m=row.elevation_loss_m,
        elevation_min_m=row.elevation_min_m,
        elevation_max_m=row.elevation_max_m,
        original_filename=row.original_filename,
    )


def _resolve_activity_payload(request: Request, activity_id: str) -> dict[str, Any]:
    storage = request.app.state.storage
    temp_storage = getattr(request.app.state, "temp_storage", None)

    try:
        return storage.get_activity_payload(activity_id)
    except Exception:
        pass

    if temp_storage is not None:
        try:
            return temp_storage.get_activity_payload(activity_id)
        except Exception:
            pass

    raise FileNotFoundError(f"Activity {activity_id} not found")


def _save_trace_payload(
    *,
    session,
    repo: TraceRepository,
    trace_store: TraceStore,
    payload: dict[str, Any],
    preferred_name: str | None,
) -> tuple[Trace, bool]:
    filename = str(payload.get("filename") or "trace.gpx")
    raw_bytes = payload.get("raw_bytes")
    df = payload.get("df")
    if not isinstance(raw_bytes, (bytes, bytearray)):
        raise ValueError("Missing raw_bytes")
    if df is None:
        raise ValueError("Missing dataframe")

    raw = bytes(raw_bytes)
    file_hash = hashlib.sha256(raw).hexdigest()
    existing = repo.get_by_file_hash(session, file_hash)
    if existing is not None:
        return existing, False

    metrics = compute_trace_metrics(df)
    route_fingerprint = compute_route_fingerprint(df)
    if route_fingerprint:
        existing_by_fp = repo.get_by_route_fingerprint(session, route_fingerprint)
        if existing_by_fp is not None:
            return existing_by_fp, False
    trace_id = str(uuid.uuid4())
    paths = trace_store.save_trace(trace_id=trace_id, filename=filename, raw_bytes=raw, df=df)

    created = repo.create_trace(
        session,
        TraceCreatePayload(
            trace_id=trace_id,
            name=format_trace_name(preferred_name, Path(filename).name),
            created_at_utc=utc_now_iso(),
            file_hash_sha256=file_hash,
            route_fingerprint=route_fingerprint,
            distance_km=float(metrics["distance_km"] or 0.0),
            elevation_gain_m=float(metrics["elevation_gain_m"] or 0.0),
            elevation_loss_m=metrics["elevation_loss_m"],
            elevation_min_m=metrics["elevation_min_m"],
            elevation_max_m=metrics["elevation_max_m"],
            original_filename=Path(filename).name,
            original_path=paths["original_path"],
        ),
    )
    return created, True


@router.get("/traces", response_model=TracesListResponse)
async def list_traces(request: Request):
    db_session_factory = _get_db_session_factory(request)

    session = db_session_factory()
    repo = TraceRepository()
    try:
        sync_result = verify_traces(session)
        rows = repo.list_traces(session)
        return TracesListResponse(
            traces=[_to_trace_item(r) for r in rows],
            sync={
                "scanned": sync_result.scanned,
                "indexed": sync_result.indexed,
                "up_to_date": sync_result.up_to_date,
                "deleted": sync_result.deleted,
                "errors": sync_result.errors,
            },
        )
    finally:
        session.close()


@router.post("/traces/upload", response_model=TraceUploadResponse)
async def upload_trace(
    request: Request,
    file: UploadFile = File(...),
    name: str | None = Form(None),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    if not file.filename.lower().endswith((".gpx", ".fit")):
        raise HTTPException(status_code=400, detail="Invalid file extension")

    raw = await file.read()
    loaded = load_activity(data=raw, name=file.filename, activity_type="theoretical")
    if loaded.df is None:
        raise HTTPException(status_code=400, detail="Failed to parse activity")

    db_session_factory = _get_db_session_factory(request)
    trace_store = _get_trace_store(request)
    session = db_session_factory()
    repo = TraceRepository()
    try:
        trace_row, created = _save_trace_payload(
            session=session,
            repo=repo,
            trace_store=trace_store,
            payload={"filename": file.filename, "raw_bytes": raw, "df": loaded.df},
            preferred_name=name,
        )

        # Keep analysis UX: upload also opens the theoretical page.
        temp_storage = getattr(request.app.state, "temp_storage", None)
        if temp_storage is None:
            raise HTTPException(status_code=500, detail="Temp storage not initialized")
        activity_id = temp_storage.store(loaded, file.filename, raw, name=trace_row.name)

        verify_traces(session)
        if created:
            session.commit()
        return TraceUploadResponse(trace=_to_trace_item(trace_row), activity_id=activity_id)
    except HTTPException:
        session.rollback()
        raise
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to upload trace: {exc}")
    finally:
        session.close()


@router.patch("/traces/{trace_id}", response_model=TraceItem)
async def rename_trace(request: Request, trace_id: str, payload: dict):
    name_raw = payload.get("name") if isinstance(payload, dict) else None
    name: str | None
    if name_raw is None:
        name = None
    else:
        cleaned = str(name_raw).strip()
        name = cleaned if cleaned else None

    db_session_factory = _get_db_session_factory(request)
    session = db_session_factory()
    repo = TraceRepository()
    try:
        ok = repo.rename_trace(session, trace_id, name)
        if not ok:
            raise HTTPException(status_code=404, detail="Trace not found")
        row = repo.get_by_id(session, trace_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Trace not found")
        session.commit()
        return _to_trace_item(row)
    finally:
        session.close()


@router.delete("/traces/{trace_id}")
async def delete_trace(request: Request, trace_id: str):
    db_session_factory = _get_db_session_factory(request)
    trace_store = _get_trace_store(request)
    session = db_session_factory()
    repo = TraceRepository()
    try:
        ok = repo.delete_trace(session, trace_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Trace not found")
        trace_store.delete_trace(trace_id)
        session.commit()
        return {"deleted": True}
    finally:
        session.close()


@router.post("/traces/{trace_id}/open")
async def open_trace_for_theoretical(request: Request, trace_id: str):
    db_session_factory = _get_db_session_factory(request)
    trace_store = _get_trace_store(request)
    session = db_session_factory()
    repo = TraceRepository()
    try:
        row = repo.get_by_id(session, trace_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Trace not found")
        filename, raw = trace_store.load_trace_bytes(trace_id)
        loaded = load_activity(data=raw, name=filename, activity_type="theoretical")
        temp_storage = getattr(request.app.state, "temp_storage", None)
        if temp_storage is None:
            raise HTTPException(status_code=500, detail="Temp storage not initialized")
        activity_id = temp_storage.store(loaded, filename, raw, name=row.name)
        return {"activity_id": activity_id, "trace_id": trace_id}
    finally:
        session.close()


@router.get("/activity/{activity_id}/trace-status", response_model=TraceStatusResponse)
async def get_activity_trace_status(request: Request, activity_id: str):
    db_session_factory = _get_db_session_factory(request)
    session = db_session_factory()
    repo = TraceRepository()
    try:
        payload = _resolve_activity_payload(request, activity_id)
        df = payload.get("df")
        if df is None:
            raise HTTPException(status_code=404, detail="Activity not found")
        fingerprint = compute_route_fingerprint(df)
        if not fingerprint:
            return TraceStatusResponse(saved=False)
        row = repo.get_by_route_fingerprint(session, fingerprint)
        if row is None:
            return TraceStatusResponse(saved=False)
        return TraceStatusResponse(saved=True, trace_id=row.id, trace_name=row.name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Activity not found")
    finally:
        session.close()


@router.post("/activity/{activity_id}/trace-save", response_model=TraceItem)
async def save_activity_trace(request: Request, activity_id: str, payload: dict | None = None):
    db_session_factory = _get_db_session_factory(request)
    trace_store = _get_trace_store(request)
    session = db_session_factory()
    repo = TraceRepository()

    desired_name = None
    if isinstance(payload, dict):
        desired_name = payload.get("name")
        if desired_name is not None:
            desired_name = str(desired_name).strip() or None

    try:
        activity_payload = _resolve_activity_payload(request, activity_id)
        trace_row, _created = _save_trace_payload(
            session=session,
            repo=repo,
            trace_store=trace_store,
            payload=activity_payload,
            preferred_name=desired_name or activity_payload.get("name"),
        )
        verify_traces(session)
        session.commit()
        return _to_trace_item(trace_row)
    except FileNotFoundError:
        session.rollback()
        raise HTTPException(status_code=404, detail="Activity not found")
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save trace: {exc}")
    finally:
        session.close()
