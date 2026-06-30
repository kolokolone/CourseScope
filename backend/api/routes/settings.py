from __future__ import annotations

from typing import Literal, cast

from fastapi import APIRouter, HTTPException, Request

from api._helpers import get_db_session_factory
from api.schemas import PersonalSettingsPatchRequest, PersonalSettingsResponse
from db.settings_repository import SettingsRepository
from db.models import utc_now_iso


router = APIRouter()


def _to_response(vma_kmh: float | None, vo2max_lastest: float | None, hr_manual: int | None, hr_source: Literal["detected", "manual"], hr_detected: int | None, updated_at: str) -> PersonalSettingsResponse:
    effective = hr_detected if hr_source == "detected" and hr_detected is not None else hr_manual
    return PersonalSettingsResponse(
        vma_kmh=vma_kmh,
        vo2max_lastest=vo2max_lastest,
        hr_max_manual_bpm=hr_manual,
        hr_max_source=cast(Literal["detected", "manual"], hr_source),
        hr_max_detected_bpm=hr_detected,
        hr_max_effective_bpm=effective,
        updated_at_utc=updated_at,
    )


@router.get("/settings/personal", response_model=PersonalSettingsResponse)
async def get_personal_settings(request: Request):
    db_session_factory = get_db_session_factory(request)

    session = db_session_factory()
    repo = SettingsRepository()
    try:
        row = repo.get_or_create(session)
        detected = repo.get_detected_hr_max(session)
        source: Literal["detected", "manual"] = "manual" if row.hr_max_source == "manual" else "detected"
        session.commit()
        return _to_response(row.vma_kmh, row.vo2max_lastest, row.hr_max_manual_bpm, source, detected, row.updated_at_utc)
    finally:
        session.close()


@router.patch("/settings/personal", response_model=PersonalSettingsResponse)
async def patch_personal_settings(request: Request, payload: PersonalSettingsPatchRequest):
    db_session_factory = get_db_session_factory(request)

    patch = payload.model_dump(exclude_unset=True)
    session = db_session_factory()
    repo = SettingsRepository()
    try:
        row = repo.get_or_create(session)

        if "vma_kmh" in patch:
            vma = patch["vma_kmh"]
            if vma is not None and (vma < 6.0 or vma > 30.0):
                raise HTTPException(status_code=400, detail="vma_kmh out of range")
            row.vma_kmh = vma

        if "hr_max_manual_bpm" in patch:
            hr_manual = patch["hr_max_manual_bpm"]
            if hr_manual is not None and (hr_manual < 80 or hr_manual > 240):
                raise HTTPException(status_code=400, detail="hr_max_manual_bpm out of range")
            row.hr_max_manual_bpm = hr_manual

        if "hr_max_source" in patch:
            source = patch["hr_max_source"]
            if source not in {"detected", "manual"}:
                raise HTTPException(status_code=400, detail="Invalid hr_max_source")
            row.hr_max_source = source

        row.updated_at_utc = utc_now_iso()

        detected = repo.get_detected_hr_max(session)
        source: Literal["detected", "manual"] = "manual" if row.hr_max_source == "manual" else "detected"
        session.commit()
        return _to_response(row.vma_kmh, row.vo2max_lastest, row.hr_max_manual_bpm, source, detected, row.updated_at_utc)
    finally:
        session.close()


@router.get("/settings/personal/hr-max-detected")
async def get_detected_hr_max(request: Request):
    db_session_factory = get_db_session_factory(request)

    session = db_session_factory()
    repo = SettingsRepository()
    try:
        detected = repo.get_detected_hr_max(session)
        return {"hr_max_detected_bpm": detected}
    finally:
        session.close()
