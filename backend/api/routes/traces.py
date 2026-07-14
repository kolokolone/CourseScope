from __future__ import annotations

import hashlib
import logging
from pathlib import Path
import uuid
from typing import Any

import numpy as np

from fastapi import APIRouter, File, Form, Header, HTTPException, Request, UploadFile

from api._helpers import get_db_session_factory
from api.race_schemas import (
    PlanPreviewRequest,
    RacePlanInput,
    RacePlanPatch,
    RaceScenarioInput,
    RaceScenarioPatch,
    RaceStopInput,
    RaceStopPatch,
    ScenarioComparisonRequest,
)
from api.schemas import TraceItem, TracesListResponse, TraceUploadResponse
from core.contracts.activity_df_contract import SCHEMA_VERSION
from core.course_profile import prepare_course_profile
from db.models import RacePlan, RaceScenario, Trace, utc_now_iso
from db.race_plan_repository import RacePlanRepository, plan_to_dict, scenario_to_dict, stop_to_dict
from db.settings_repository import SettingsRepository
from db.trace_repository import TraceCreatePayload, TraceRepository
from services.analysis_service import load_activity
from services.historical_calibration_service import suggest_calibration_factor
from services.race_planning_service import calculate_race_plan_preview
from storage.trace_store import TraceStore, compute_route_fingerprint, format_trace_name
from traces.verify_traces import verify_traces


router = APIRouter()


def _get_trace_store(request: Request) -> TraceStore:
    trace_store = getattr(request.app.state, "trace_store", None)
    if trace_store is None:
        raise HTTPException(status_code=500, detail="Trace store not initialized")
    return trace_store


def _logger(request: Request) -> logging.Logger:
    return getattr(request.app.state, "logger", logging.getLogger("coursescope"))


def _dump(model, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_unset=exclude_unset)
    return model.dict(exclude_unset=exclude_unset)


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


def _parse_trace(filename: str, raw: bytes):
    loaded = load_activity(data=raw, name=filename, activity_type="theoretical")
    if loaded.df is None:
        raise ValueError("Failed to parse trace")
    return loaded.df


def _profile_metrics(dataframe) -> dict[str, float | None]:
    profile = prepare_course_profile(dataframe).dataframe
    elevation = profile["elevation_m"].to_numpy(dtype=float)
    delta = np.diff(elevation)
    return {
        "distance_km": float(profile["distance_km"].iloc[-1]),
        "elevation_gain_m": float(np.clip(delta, 0.0, None).sum()),
        "elevation_loss_m": float(-np.clip(delta, None, 0.0).sum()),
        "elevation_min_m": float(np.min(elevation)),
        "elevation_max_m": float(np.max(elevation)),
    }


def _load_trace_dataframe(request: Request, session, row: Trace):
    store = _get_trace_store(request)
    result = store.load_or_rebuild_dataframe(
        row.id,
        expected_source_hash=row.file_hash_sha256,
        rebuild=_parse_trace,
        logger=_logger(request),
    )
    TraceRepository().update_parquet_metadata(
        session,
        row.id,
        parquet_path=result.parquet_path,
        source_hash_sha256=result.source_hash_sha256,
        dataframe_schema_version=SCHEMA_VERSION,
        generated_at_utc=result.generated_at_utc,
    )
    if row.file_hash_sha256 != result.source_hash_sha256:
        row.file_hash_sha256 = result.source_hash_sha256
        row.parquet_source_hash_sha256 = result.source_hash_sha256
        row.route_fingerprint = compute_route_fingerprint(result.dataframe)
        metrics = _profile_metrics(result.dataframe)
        row.distance_km = float(metrics["distance_km"] or 0.0)
        row.elevation_gain_m = float(metrics["elevation_gain_m"] or 0.0)
        row.elevation_loss_m = metrics["elevation_loss_m"]
        row.elevation_min_m = metrics["elevation_min_m"]
        row.elevation_max_m = metrics["elevation_max_m"]
    return result


def _require_trace(session, trace_id: str) -> Trace:
    row = TraceRepository().get_by_id(session, trace_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    return row


def _require_plan(session, trace_id: str, plan_id: str) -> RacePlan:
    plan = RacePlanRepository().get(session, trace_id, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Race plan not found for this trace")
    return plan


def _require_scenario(repo: RacePlanRepository, plan: RacePlan, scenario_id: str) -> RaceScenario:
    scenario = repo.get_scenario(None, plan, scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Race scenario not found for this plan")
    return scenario


def _with_personal_defaults(session, scenario: dict[str, Any]) -> dict[str, Any]:
    resolved = dict(scenario)
    if resolved.get("objective_type") == "effort" and resolved.get("vma_kmh") is None:
        settings = SettingsRepository().get_or_create(session)
        if settings.vma_kmh is not None:
            resolved["vma_kmh"] = float(settings.vma_kmh)
    return resolved


@router.get("/traces", response_model=TracesListResponse)
async def list_traces(request: Request):
    session = get_db_session_factory(request)()
    try:
        sync_result = verify_traces(session)
        rows = TraceRepository().list_traces(session)
        return TracesListResponse(
            traces=[_to_trace_item(row) for row in rows],
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
    max_size: int = Header(100_000_000),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    if not file.filename.lower().endswith((".gpx", ".fit")):
        raise HTTPException(status_code=400, detail="Invalid file extension. Allowed: .fit, .gpx")
    raw = await file.read()
    if len(raw) > max_size:
        raise HTTPException(status_code=413, detail=f"File too large. Max size: {max_size / (1024 * 1024):.1f}MB")
    if not raw:
        raise HTTPException(status_code=400, detail="Empty trace file")
    try:
        dataframe = _parse_trace(file.filename, raw)
        prepare_course_profile(dataframe)  # validates usable distance/elevation before persistence
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    session = get_db_session_factory(request)()
    trace_repo = TraceRepository()
    plan_repo = RacePlanRepository()
    store = _get_trace_store(request)
    try:
        file_hash = hashlib.sha256(raw).hexdigest()
        existing = trace_repo.get_by_file_hash(session, file_hash)
        if existing is not None:
            plan_repo.ensure_default(session, existing.id)
            session.commit()
            return TraceUploadResponse(trace=_to_trace_item(existing))

        fingerprint = compute_route_fingerprint(dataframe)
        if fingerprint:
            same_route = trace_repo.get_by_route_fingerprint(session, fingerprint)
            if same_route is not None:
                plan_repo.ensure_default(session, same_route.id)
                session.commit()
                return TraceUploadResponse(trace=_to_trace_item(same_route))

        trace_id = str(uuid.uuid4())
        metrics = _profile_metrics(dataframe)
        paths = store.save_trace(trace_id=trace_id, filename=file.filename, raw_bytes=raw, df=dataframe)
        row = trace_repo.create_trace(
            session,
            TraceCreatePayload(
                trace_id=trace_id,
                name=format_trace_name(name, Path(file.filename).name),
                created_at_utc=utc_now_iso(),
                file_hash_sha256=file_hash,
                route_fingerprint=fingerprint,
                distance_km=float(metrics["distance_km"] or 0),
                elevation_gain_m=float(metrics["elevation_gain_m"] or 0),
                elevation_loss_m=metrics["elevation_loss_m"],
                elevation_min_m=metrics["elevation_min_m"],
                elevation_max_m=metrics["elevation_max_m"],
                original_filename=Path(file.filename).name,
                original_path=paths["original_path"],
                parquet_path=paths["parquet_path"],
                parquet_source_hash_sha256=paths["source_sha256"],
                dataframe_schema_version=paths["dataframe_schema_version"],
                parquet_generated_at_utc=paths["generated_at_utc"],
            ),
        )
        plan_repo.ensure_default(session, trace_id)
        session.commit()
        return TraceUploadResponse(trace=_to_trace_item(row))
    except HTTPException:
        session.rollback()
        raise
    except Exception as exc:
        session.rollback()
        store.delete_trace(trace_id) if "trace_id" in locals() else None
        raise HTTPException(status_code=500, detail=f"Failed to upload trace: {exc}") from exc
    finally:
        session.close()


@router.get("/traces/{trace_id}")
async def get_trace(request: Request, trace_id: str):
    session = get_db_session_factory(request)()
    try:
        row = _require_trace(session, trace_id)
        loaded = _load_trace_dataframe(request, session, row)
        prepared = prepare_course_profile(loaded.dataframe)
        plan_repo = RacePlanRepository()
        plan_repo.ensure_default(session, trace_id)
        plans = plan_repo.list_for_trace(session, trace_id)
        active_plan = plans[0] if plans else None
        if active_plan is not None:
            active_plan = next((plan for plan in plans if plan.active_scenario_id), active_plan)
        session.commit()
        metadata = _get_trace_store(request).read_metadata(trace_id)
        return {
            "trace": _dump(_to_trace_item(row)),
            "file": {
                "original_filename": row.original_filename,
                "source_sha256": row.file_hash_sha256,
                "parquet_available": True,
                "parquet_source": loaded.source,
                "parquet_rebuild_reason": loaded.rebuild_reason,
                "dataframe_schema_version": row.dataframe_schema_version or metadata.get("dataframe_schema_version"),
                "parquet_generated_at_utc": loaded.generated_at_utc,
            },
            "static_metrics": {
                "distance_km": float(prepared.dataframe["distance_km"].iloc[-1]),
                "elevation_gain_m": float(row.elevation_gain_m or 0.0),
                "elevation_loss_m": float(row.elevation_loss_m or 0.0),
                "elevation_min_m": float(prepared.dataframe["elevation_m"].min()),
                "elevation_max_m": float(prepared.dataframe["elevation_m"].max()),
            },
            "quality": prepared.quality,
            "active_plan": plan_to_dict(active_plan, full=False) if active_plan is not None else None,
            "plans": [plan_to_dict(plan, full=False) for plan in plans],
        }
    finally:
        session.close()


@router.patch("/traces/{trace_id}", response_model=TraceItem)
async def rename_trace(request: Request, trace_id: str, payload: dict[str, Any]):
    session = get_db_session_factory(request)()
    try:
        row = _require_trace(session, trace_id)
        name = str(payload.get("name") or "").strip() or None
        row.name = name
        session.commit()
        return _to_trace_item(row)
    finally:
        session.close()


@router.delete("/traces")
async def cleanup_traces(request: Request):
    session = get_db_session_factory(request)()
    store = _get_trace_store(request)
    try:
        rows = TraceRepository().list_traces(session)
        trace_ids = [row.id for row in rows]
        for row in rows:
            session.delete(row)
        session.commit()
        for trace_id in trace_ids:
            store.delete_trace(trace_id)
        return {"deleted": len(trace_ids)}
    finally:
        session.close()


@router.delete("/traces/{trace_id}")
async def delete_trace(request: Request, trace_id: str):
    session = get_db_session_factory(request)()
    try:
        row = _require_trace(session, trace_id)
        session.delete(row)
        session.commit()
        _get_trace_store(request).delete_trace(trace_id)
        return {"deleted": True, "trace_id": trace_id}
    finally:
        session.close()


@router.post("/traces/{trace_id}/plan-preview")
async def preview_plan(request: Request, trace_id: str, payload: PlanPreviewRequest):
    session = get_db_session_factory(request)()
    try:
        row = _require_trace(session, trace_id)
        loaded = _load_trace_dataframe(request, session, row)
        repo = RacePlanRepository()
        plan_dict = dict(payload.plan or {})
        scenario_dict = _dump(payload.scenario) if payload.scenario is not None else None
        stops = [_dump(item) for item in payload.stops] if payload.stops is not None else None
        custom_points = [_dump(item) for item in payload.custom_points] if payload.custom_points is not None else None
        custom_segments = [_dump(item) for item in payload.custom_segments] if payload.custom_segments is not None else None
        if payload.plan_id is not None:
            plan = _require_plan(session, trace_id, payload.plan_id)
            persisted_plan = plan_to_dict(plan, full=True)
            persisted_plan.update(plan_dict)
            plan_dict = persisted_plan
            scenario_id = payload.scenario_id or plan.active_scenario_id
            if scenario_dict is None:
                if scenario_id is None:
                    raise HTTPException(status_code=400, detail="The race plan has no active scenario")
                scenario = _require_scenario(repo, plan, scenario_id)
                scenario_dict = scenario_to_dict(scenario, full=True)
                stops = list(scenario_dict.get("stops", [])) if stops is None else stops
                custom_segments = list(scenario_dict.get("strategy_segments", [])) if custom_segments is None else custom_segments
            custom_points = list(persisted_plan.get("course_points", [])) if custom_points is None else custom_points
        if scenario_dict is None:
            raise HTTPException(status_code=400, detail="A scenario or persisted plan_id is required")
        scenario_dict = _with_personal_defaults(session, scenario_dict)
        result = calculate_race_plan_preview(
            loaded.dataframe,
            scenario=scenario_dict,
            stops=stops,
            plan=plan_dict,
            custom_points=custom_points,
            custom_segments=custom_segments,
        )
        session.commit()
        return result
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        session.close()


@router.get("/traces/{trace_id}/calibration")
async def get_historical_calibration(request: Request, trace_id: str, scenario_id: str | None = None):
    session = get_db_session_factory(request)()
    try:
        row = _require_trace(session, trace_id)
        plans = RacePlanRepository().list_for_trace(session, trace_id)
        plan = plans[0] if plans else None
        if plan is None:
            raise HTTPException(status_code=404, detail="Race plan not found for this trace")
        selected_id = scenario_id or plan.active_scenario_id
        scenario = _require_scenario(RacePlanRepository(), plan, selected_id) if selected_id else None
        if scenario is None:
            raise HTTPException(status_code=404, detail="Race scenario not found")
        loaded = _load_trace_dataframe(request, session, row)
        preview = calculate_race_plan_preview(loaded.dataframe, scenario=_with_personal_defaults(session, scenario_to_dict(scenario)), stops=[stop_to_dict(item) for item in scenario.stops], plan=plan_to_dict(plan))
        totals = preview["totals"]
        gain_per_km = float(totals["elevation_gain_m"]) / float(totals["distance_km"]) if float(totals["distance_km"]) > 0 else 0.0
        result = suggest_calibration_factor(session, reference_pace_s_per_km=float(totals["base_pace_s_per_km"]), course_gain_per_km=gain_per_km)
        session.commit()
        return {"trace_id": trace_id, "scenario_id": scenario.id, **result}
    finally:
        session.close()


@router.get("/traces/{trace_id}/plans")
async def list_plans(request: Request, trace_id: str):
    session = get_db_session_factory(request)()
    try:
        _require_trace(session, trace_id)
        return {"plans": [plan_to_dict(plan, full=False) for plan in RacePlanRepository().list_for_trace(session, trace_id)]}
    finally:
        session.close()


@router.post("/traces/{trace_id}/plans", status_code=201)
async def create_plan(request: Request, trace_id: str, payload: RacePlanInput):
    session = get_db_session_factory(request)()
    try:
        _require_trace(session, trace_id)
        plan = RacePlanRepository().create(session, trace_id, _dump(payload))
        session.commit()
        return plan_to_dict(plan)
    finally:
        session.close()


@router.get("/traces/{trace_id}/plans/{plan_id}")
async def get_plan(request: Request, trace_id: str, plan_id: str):
    session = get_db_session_factory(request)()
    try:
        return plan_to_dict(_require_plan(session, trace_id, plan_id))
    finally:
        session.close()


@router.patch("/traces/{trace_id}/plans/{plan_id}")
async def update_plan(request: Request, trace_id: str, plan_id: str, payload: RacePlanPatch):
    session = get_db_session_factory(request)()
    try:
        repo = RacePlanRepository()
        plan = repo.update(session, _require_plan(session, trace_id, plan_id), _dump(payload, exclude_unset=True))
        session.commit()
        return {"plan": plan_to_dict(plan), "preview_required": True}
    finally:
        session.close()


@router.delete("/traces/{trace_id}/plans/{plan_id}")
async def delete_plan(request: Request, trace_id: str, plan_id: str):
    session = get_db_session_factory(request)()
    try:
        RacePlanRepository().delete(session, _require_plan(session, trace_id, plan_id))
        session.commit()
        return {"deleted": True, "plan_id": plan_id}
    finally:
        session.close()


@router.post("/traces/{trace_id}/plans/{plan_id}/scenarios", status_code=201)
async def create_scenario(request: Request, trace_id: str, plan_id: str, payload: RaceScenarioInput):
    session = get_db_session_factory(request)()
    try:
        repo = RacePlanRepository()
        plan = _require_plan(session, trace_id, plan_id)
        scenario = repo.create_scenario(session, plan, _dump(payload))
        if scenario.is_active or plan.active_scenario_id is None:
            repo.update_scenario(plan, scenario, {"is_active": True})
        session.commit()
        return {"scenario": scenario_to_dict(scenario), "preview_required": True}
    finally:
        session.close()


@router.patch("/traces/{trace_id}/plans/{plan_id}/scenarios/{scenario_id}")
async def update_scenario(request: Request, trace_id: str, plan_id: str, scenario_id: str, payload: RaceScenarioPatch):
    session = get_db_session_factory(request)()
    try:
        repo = RacePlanRepository()
        plan = _require_plan(session, trace_id, plan_id)
        scenario = repo.update_scenario(plan, _require_scenario(repo, plan, scenario_id), _dump(payload, exclude_unset=True))
        session.commit()
        return {"scenario": scenario_to_dict(scenario), "preview_required": True}
    finally:
        session.close()


@router.delete("/traces/{trace_id}/plans/{plan_id}/scenarios/{scenario_id}")
async def delete_scenario(request: Request, trace_id: str, plan_id: str, scenario_id: str):
    session = get_db_session_factory(request)()
    try:
        repo = RacePlanRepository()
        plan = _require_plan(session, trace_id, plan_id)
        scenario = _require_scenario(repo, plan, scenario_id)
        repo.delete_scenario(session, plan, scenario)
        session.commit()
        return {"deleted": True, "scenario_id": scenario_id}
    finally:
        session.close()


@router.post("/traces/{trace_id}/plans/{plan_id}/scenarios/{scenario_id}/stops", status_code=201)
async def create_stop(request: Request, trace_id: str, plan_id: str, scenario_id: str, payload: RaceStopInput):
    session = get_db_session_factory(request)()
    try:
        repo = RacePlanRepository()
        plan = _require_plan(session, trace_id, plan_id)
        stop = repo.create_stop(session, _require_scenario(repo, plan, scenario_id), _dump(payload))
        session.commit()
        return {"stop": stop_to_dict(stop), "preview_required": True}
    finally:
        session.close()


@router.patch("/traces/{trace_id}/plans/{plan_id}/scenarios/{scenario_id}/stops/{stop_id}")
async def update_stop(request: Request, trace_id: str, plan_id: str, scenario_id: str, stop_id: str, payload: RaceStopPatch):
    session = get_db_session_factory(request)()
    try:
        repo = RacePlanRepository()
        plan = _require_plan(session, trace_id, plan_id)
        scenario = _require_scenario(repo, plan, scenario_id)
        stop = repo.get_stop(scenario, stop_id)
        if stop is None:
            raise HTTPException(status_code=404, detail="Race stop not found for this scenario")
        repo.update_stop(stop, _dump(payload, exclude_unset=True))
        session.commit()
        return {"stop": stop_to_dict(stop), "preview_required": True}
    finally:
        session.close()


@router.delete("/traces/{trace_id}/plans/{plan_id}/scenarios/{scenario_id}/stops/{stop_id}")
async def delete_stop(request: Request, trace_id: str, plan_id: str, scenario_id: str, stop_id: str):
    session = get_db_session_factory(request)()
    try:
        repo = RacePlanRepository()
        plan = _require_plan(session, trace_id, plan_id)
        scenario = _require_scenario(repo, plan, scenario_id)
        stop = repo.get_stop(scenario, stop_id)
        if stop is None:
            raise HTTPException(status_code=404, detail="Race stop not found for this scenario")
        session.delete(stop)
        session.commit()
        return {"deleted": True, "stop_id": stop_id}
    finally:
        session.close()


@router.post("/traces/{trace_id}/plans/{plan_id}/compare")
async def compare_scenarios(request: Request, trace_id: str, plan_id: str, payload: ScenarioComparisonRequest):
    session = get_db_session_factory(request)()
    try:
        row = _require_trace(session, trace_id)
        plan = _require_plan(session, trace_id, plan_id)
        loaded = _load_trace_dataframe(request, session, row)
        repo = RacePlanRepository()
        results = []
        for scenario_id in payload.scenario_ids:
            scenario = _require_scenario(repo, plan, scenario_id)
            scenario_data = scenario_to_dict(scenario)
            preview = calculate_race_plan_preview(
                loaded.dataframe,
                scenario=_with_personal_defaults(session, scenario_data),
                stops=list(scenario_data["stops"]),
                plan=plan_to_dict(plan),
                custom_points=plan_to_dict(plan)["course_points"],
                custom_segments=list(scenario_data["strategy_segments"]),
            )
            results.append({"scenario": scenario_to_dict(scenario, full=False), "totals": preview["totals"], "alerts": preview["alerts"]})
        baseline = results[0]["totals"]
        for item in results:
            totals = item["totals"]
            item["delta_vs_first"] = {
                "running_time_s": float(totals["running_time_s"]) - float(baseline["running_time_s"]),
                "elapsed_time_s": float(totals["elapsed_time_s"]) - float(baseline["elapsed_time_s"]),
                "stop_time_s": float(totals["stop_time_s"]) - float(baseline["stop_time_s"]),
            }
        session.commit()
        return {"trace_id": trace_id, "plan_id": plan_id, "scenarios": results}
    finally:
        session.close()


# Deprecated cross-domain endpoints intentionally no longer resolve or create
# temporary activity IDs. They remain briefly visible to old clients as 410.
@router.post("/traces/{trace_id}/open", deprecated=True)
async def deprecated_open_trace(trace_id: str):
    raise HTTPException(status_code=410, detail=f"Trace {trace_id} opens directly at /traces/{trace_id}", headers={"Deprecation": "true"})


@router.get("/activity/{activity_id}/trace-status", deprecated=True)
async def deprecated_trace_status(activity_id: str):
    raise HTTPException(status_code=410, detail="Activity-to-trace resolution was removed; use /traces", headers={"Deprecation": "true"})


@router.post("/activity/{activity_id}/trace-save", deprecated=True)
async def deprecated_trace_save(activity_id: str):
    raise HTTPException(status_code=410, detail="Upload theoretical files with POST /traces/upload", headers={"Deprecation": "true"})
