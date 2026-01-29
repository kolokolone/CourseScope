from fastapi import APIRouter, Query, HTTPException, Request
from typing import Optional
import pandas as pd

from api.schemas import ActivityMapResponse, MapMarker


router = APIRouter()


def calculate_bounds(df) -> list:
    """Calcule bounding box [minLon, minLat, maxLon, maxLat]"""
    if "lat" not in df.columns or "lon" not in df.columns:
        return [0, 0, 0, 0]

    valid_coords = df[["lat", "lon"]].dropna()
    if valid_coords.empty:
        return [0, 0, 0, 0]

    min_lat = valid_coords["lat"].min()
    max_lat = valid_coords["lat"].max()
    min_lon = valid_coords["lon"].min()
    max_lon = valid_coords["lon"].max()

    return [min_lon, min_lat, max_lon, max_lat]


def extract_polyline(df, downsample: Optional[int] = None) -> list:
    """Extrait polyline pour carte"""
    if "lat" not in df.columns or "lon" not in df.columns:
        return []

    coords = df[["lat", "lon"]].dropna()
    if coords.empty:
        return []

    if downsample and len(coords) > downsample:
        step = max(1, len(coords) // downsample)
        coords = coords.iloc[::step]

    return [[row["lat"], row["lon"]] for _, row in coords.iterrows()]


def extract_markers(df) -> list:
    """Extrait points remarquables (pauses, climbs, etc.)"""
    markers = []

    if df.empty:
        return markers

    if "speed_m_s" in df.columns and "lat" in df.columns and "lon" in df.columns:
        pauses = df[df["speed_m_s"] < 0.1]
        for _, pause in pauses.iterrows():
            if not pd.isna(pause["lat"]) and not pd.isna(pause["lon"]):
                markers.append(
                    MapMarker(
                        lat=pause["lat"],
                        lon=pause["lon"],
                        label="Pause",
                        type="pause",
                    )
                )

    if "elevation" in df.columns and "lat" in df.columns and "lon" in df.columns:
        max_elev_idx = df["elevation"].idxmax()
        max_elev = df.loc[max_elev_idx]
        if not pd.isna(max_elev["lat"]) and not pd.isna(max_elev["lon"]):
            markers.append(
                MapMarker(
                    lat=max_elev["lat"],
                    lon=max_elev["lon"],
                    label=f"Max Alt: {max_elev['elevation']:.0f}m",
                    type="elevation",
                )
            )

    return markers


@router.get("/activity/{activity_id}/map", response_model=ActivityMapResponse)
async def get_activity_map(
    request: Request,
    activity_id: str,
    downsample: Optional[int] = Query(None, description="Max points after downsampling"),
):
    """Retourne les données cartographiques pour une activité"""
    try:
        storage = request.app.state.storage
        df = storage.load_dataframe(activity_id)

        if df.empty:
            raise HTTPException(status_code=404, detail=f"Activity {activity_id} not found")

        bbox = calculate_bounds(df)
        polyline = extract_polyline(df, downsample)
        markers = extract_markers(df)

        return ActivityMapResponse(
            bbox=bbox,
            polyline=polyline,
            markers=markers if markers else None,
        )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Activity {activity_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get map data: {str(e)}")
