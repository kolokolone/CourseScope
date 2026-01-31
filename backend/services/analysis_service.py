"""Points d'entree backend de haut niveau (sans couche UI).

Ce module expose des points d'entree compatibles FastAPI qui travaillent sur
des bytes et renvoient des objets metier ou des payloads JSON-serialisables.

Ce module est consomme par l'API (FastAPI).
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from core.contracts.activity_df_contract import SCHEMA_VERSION
from services import activity_service, real_activity_service, theoretical_service
from services.cache import KeyValueCache, NullCache, make_cache_key, sha256_bytes
from services.models import (
    LoadedActivity,
    RealRunParams,
    RealRunResult,
    RealRunViewParams,
    TheoreticalBase,
    TheoreticalFigures,
    TheoreticalParams,
    TheoreticalResult,
)


def load_activity(
    *,
    data: bytes,
    name: str,
    cache: KeyValueCache | None = None,
) -> LoadedActivity:
    cache = cache or NullCache()
    key = make_cache_key(
        namespace="activity:load",
        version=SCHEMA_VERSION,
        payload={"name": name, "sha256": sha256_bytes(data)},
    )
    cached = cache.get(key)
    if isinstance(cached, LoadedActivity):
        return cached
    loaded = activity_service.load_activity_from_bytes(data=data, name=name)
    cache.set(key, loaded)
    return loaded


def analyze_real(
    *,
    loaded: LoadedActivity,
    params: RealRunParams | None = None,
    view: RealRunViewParams | None = None,
    cache: KeyValueCache | None = None,
) -> RealRunResult:
    cache = cache or NullCache()
    payload = {"name": loaded.name, "type": loaded.gpx_type.type, "confidence": loaded.gpx_type.confidence}
    if params is not None:
        payload["params"] = asdict(params)
    if view is not None:
        payload["view"] = asdict(view)
    key = make_cache_key(namespace="activity:real", version=SCHEMA_VERSION, payload=payload)
    cached = cache.get(key)
    if isinstance(cached, RealRunResult):
        return cached
    result = real_activity_service.analyze_real_activity(loaded.df, params=params, view=view)
    cache.set(key, result)
    return result


def analyze_theoretical(
    *,
    loaded: LoadedActivity,
    params: TheoreticalParams,
    cache: KeyValueCache | None = None,
) -> TheoreticalResult:
    cache = cache or NullCache()
    payload: dict[str, Any] = {
        "name": loaded.name,
        "type": loaded.gpx_type.type,
        "confidence": loaded.gpx_type.confidence,
        "params": asdict(params),
    }
    key = make_cache_key(namespace="activity:theoretical", version=SCHEMA_VERSION, payload=payload)
    cached = cache.get(key)
    if isinstance(cached, TheoreticalResult):
        return cached

    df_base, summary_base = theoretical_service.prepare_base(loaded.df, params.base_pace_s_per_km)
    df_display, default_cap_min, _used_cap_min = theoretical_service.compute_display_df(
        df_base,
        smoothing_segments=params.smoothing_segments,
        cap_min_per_km=params.cap_min_per_km,
    )

    base = TheoreticalBase(df_base=df_base, summary_base=summary_base, default_cap_min_per_km=default_cap_min)
    passages = theoretical_service.compute_passages(
        df_base,
        start_datetime=params.start_datetime,
        target_distances_km=params.passage_distances_km,
    )
    fig_base = theoretical_service.build_base_figure(df_display, markers=passages.markers)
    splits = theoretical_service.compute_splits(
        passages.df_calc,
        start_datetime=params.start_datetime,
        split_distance_km=1.0,
    )

    advanced, _used_cap_adv = theoretical_service.compute_advanced(
        passages.df_calc,
        weather_factor=params.weather_factor,
        split_bias=params.split_bias_pct,
        smoothing_segments=params.smoothing_segments,
        cap_adv_min_per_km=params.cap_adv_min_per_km,
    )
    figures = TheoreticalFigures(base=fig_base, advanced=advanced.figure)
    result = TheoreticalResult(
        base=base,
        df_display=df_display,
        passages=passages,
        splits=splits,
        figures=figures,
        advanced=advanced,
    )

    cache.set(key, result)
    return result
