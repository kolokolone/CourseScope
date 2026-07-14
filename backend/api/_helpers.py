from __future__ import annotations

import pandas as pd
from fastapi import HTTPException, Request

from registry.series_registry import SeriesRegistry
from storage.activity_store import LocalTempStorage, _model_to_dict


def get_db_session_factory(request: Request):
    """Retourne la factory de session DB ou lève HTTPException(500)."""
    factory = getattr(request.app.state, "db_session_factory", None)
    if factory is None:
        raise HTTPException(status_code=500, detail="DB not initialized")
    return factory


def resolve_activity_df(request: Request, activity_id: str) -> pd.DataFrame:
    """Resolve a persisted real activity only."""
    storage: LocalTempStorage = request.app.state.storage
    try:
        loaded = storage.load(activity_id)
        if loaded.gpx_type.type != "real_run":
            raise FileNotFoundError(activity_id)
        df = storage.load_dataframe(activity_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Activity {activity_id} not found")

    if df.empty:
        raise HTTPException(status_code=404, detail=f"Activity {activity_id} not found")
    return df


def get_series_registry(request: Request) -> SeriesRegistry:
    return request.app.state.registry


def get_activity_storage(request: Request) -> LocalTempStorage:
    return request.app.state.storage
