from __future__ import annotations

import pandas as pd
from fastapi import HTTPException, Request

from registry.series_registry import SeriesRegistry
from storage.activity_store import LocalTempStorage, _model_to_dict


def resolve_activity_df(request: Request, activity_id: str) -> pd.DataFrame:
    """Resout un DataFrame d'activite avec fallback temp_storage.

    Leve HTTPException(404) si l'activite n'est pas trouvee.
    """
    storage: LocalTempStorage = request.app.state.storage
    try:
        df = storage.load_dataframe(activity_id)
    except FileNotFoundError:
        temp_storage = getattr(request.app.state, "temp_storage", None)
        if temp_storage is None:
            raise HTTPException(status_code=404, detail=f"Activity {activity_id} not found")
        try:
            df = temp_storage.load_dataframe(activity_id)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Activity {activity_id} not found")

    if df.empty:
        raise HTTPException(status_code=404, detail=f"Activity {activity_id} not found")
    return df


def get_series_registry(request: Request) -> SeriesRegistry:
    return request.app.state.registry


def get_activity_storage(request: Request) -> LocalTempStorage:
    return request.app.state.storage
