from __future__ import annotations

import time
from threading import Lock

import httpx
from fastapi import APIRouter, HTTPException, Query

from api.schemas import GeoCitiesResponse, GeoCityItem


router = APIRouter()

_CACHE_TTL_S = 24 * 60 * 60
_cache_lock = Lock()
_cache: dict[str, tuple[float, GeoCitiesResponse]] = {}


def _normalize_query(value: str) -> str:
    return str(value or "").strip().lower()


def _from_cache(key: str) -> GeoCitiesResponse | None:
    now = time.time()
    with _cache_lock:
        hit = _cache.get(key)
        if hit is None:
            return None
        expires_at, payload = hit
        if expires_at <= now:
            _cache.pop(key, None)
            return None
        return payload


def _to_cache(key: str, payload: GeoCitiesResponse) -> None:
    with _cache_lock:
        _cache[key] = (time.time() + _CACHE_TTL_S, payload)


@router.get("/geo/cities", response_model=GeoCitiesResponse)
async def get_geo_cities(
    query: str = Query(..., min_length=2),
    limit: int = Query(8, ge=1, le=10),
    language: str = Query("fr", min_length=2, max_length=8),
):
    normalized = _normalize_query(query)
    if len(normalized) < 2:
        raise HTTPException(status_code=400, detail="query must contain at least 2 characters")

    cache_key = f"{normalized}|{limit}|{language.strip().lower()}"
    cached = _from_cache(cache_key)
    if cached is not None:
        return cached

    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": normalized,
        "count": int(limit),
        "language": language.strip().lower() or "fr",
    }

    try:
        timeout = httpx.Timeout(4.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Geocoding provider error: {str(exc)}")

    results_raw = payload.get("results") if isinstance(payload, dict) else None
    rows = results_raw if isinstance(results_raw, list) else []

    items: list[GeoCityItem] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        city = str(row.get("name") or "").strip()
        country = str(row.get("country") or "").strip()
        lat = row.get("latitude")
        lon = row.get("longitude")
        if not city or not country:
            continue
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            continue
        items.append(
            GeoCityItem(
                label=f"{city}, {country}",
                city=city,
                country=country,
                country_code=str(row.get("country_code") or "").upper() or None,
                lat=float(lat),
                lon=float(lon),
            )
        )

    out = GeoCitiesResponse(query=normalized, results=items)
    _to_cache(cache_key, out)
    return out
