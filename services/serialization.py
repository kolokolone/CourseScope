"""Helpers de serialisation (sans Streamlit).

Convertit des objets backend (dataclasses, pandas, numpy, figures plotly)
en structures 100% JSON-serialisables, compatibles avec une future integration
FastAPI/React.

Ce module ne doit pas importer Streamlit.
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd


def _is_nan(value: Any) -> bool:
    try:
        return bool(value != value)
    except Exception:
        return False


def _dt_to_iso(value: Any) -> str | None:
    if value is None:
        return None
    if value is pd.NaT:
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        if pd.isna(value):
            return None
        # Conserve l'info timezone si presente.
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return None


def df_to_records(df: pd.DataFrame, *, limit: int | None = None) -> list[dict[str, Any]]:
    if df is None:
        return []
    if limit is not None:
        df = df.head(int(limit))
    # Remplace NaN/NaT par None pour JSON.
    # IMPORTANT: cast en object pour conserver None dans les colonnes numeriques.
    safe = df.copy().astype(object)
    safe = safe.where(pd.notna(safe), None)

    # Convertit les timestamps en chaines ISO.
    dt_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
    for col in dt_cols:
        safe[col] = safe[col].apply(lambda v: _dt_to_iso(v))
    return safe.to_dict(orient="records")


def series_to_list(series: pd.Series, *, limit: int | None = None) -> list[Any]:
    if series is None:
        return []
    s = series
    if limit is not None:
        s = s.head(int(limit))
    if pd.api.types.is_datetime64_any_dtype(s):
        return [(_dt_to_iso(v)) for v in s]
    out: list[Any] = []
    for v in s.to_list():
        if v is pd.NaT:
            out.append(None)
        elif _is_nan(v):
            out.append(None)
        else:
            out.append(to_jsonable(v))
    return out


def to_jsonable(obj: Any, *, dataframe_limit: int | None = None) -> Any:
    """Convertit obj en primitives JSON-serialisables.

    Retourne uniquement dict/list/str/int/float/bool/None.
    """

    if obj is None:
        return None

    # Valeurs speciales pandas
    if obj is pd.NaT:
        return None

    if isinstance(obj, (pd.Timestamp, datetime, date)):
        return _dt_to_iso(obj)

    # Scalaire numpy
    if isinstance(obj, np.generic):
        try:
            return obj.item()
        except Exception:
            return str(obj)

    # Scalaires de base
    if isinstance(obj, (str, int, bool)):
        return obj
    if isinstance(obj, float):
        return None if _is_nan(obj) else obj

    # Conteneurs
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v, dataframe_limit=dataframe_limit) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_jsonable(v, dataframe_limit=dataframe_limit) for v in obj]

    # pandas
    if isinstance(obj, pd.DataFrame):
        return {
            "type": "dataframe",
            "shape": [int(obj.shape[0]), int(obj.shape[1])],
            "columns": [str(c) for c in obj.columns],
            "records": df_to_records(obj, limit=dataframe_limit),
        }
    if isinstance(obj, pd.Series):
        return {
            "type": "series",
            "name": str(obj.name) if obj.name is not None else None,
            "values": series_to_list(obj, limit=dataframe_limit),
        }

    # Figures Plotly (ou tout objet exposant to_plotly_json)
    to_plotly_json = getattr(obj, "to_plotly_json", None)
    if callable(to_plotly_json):
        return {
            "type": "plotly",
            "figure": to_jsonable(to_plotly_json(), dataframe_limit=dataframe_limit),
        }

    # dataclasses
    if is_dataclass(obj):
        out: dict[str, Any] = {"type": obj.__class__.__name__}
        for f in fields(obj):
            out[f.name] = to_jsonable(getattr(obj, f.name), dataframe_limit=dataframe_limit)
        return out

    # Fallback
    return str(obj)
