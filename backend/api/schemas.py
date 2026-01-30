from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime

# 1. POST /activity/load - Request/Response
class SidebarStats(BaseModel):
    distance_km: Optional[float] = None
    elapsed_time_s: Optional[float] = None
    moving_time_s: Optional[float] = None
    elevation_gain_m: Optional[float] = None


class ActivityLimits(BaseModel):
    downsampled: bool
    dataframe_limit: Optional[int] = None
    note: Optional[str] = None


class ActivityLoadResponse(BaseModel):
    id: str = Field(..., description="UUID unique activité")
    type: Literal["real", "theoretical"]
    stats_sidebar: SidebarStats
    limits: Optional[ActivityLimits] = None


# 2. Series Index
class SeriesInfo(BaseModel):
    name: str
    unit: str
    x_axes: List[Literal["time", "distance"]]
    default: bool


class SeriesIndex(BaseModel):
    available: List[SeriesInfo]


class ActivityLimitsDetail(BaseModel):
    downsampled: bool
    original_points: Optional[int] = None
    returned_points: Optional[int] = None
    note: Optional[str] = None


# 3. GET /activity/{id}/real - Response
class RealActivityResponse(BaseModel):
    summary: dict  # Structure existante services/
    highlights: dict
    zones: Optional[dict] = None
    best_efforts: Optional[dict] = None
    personal_records: Optional[dict] = None
    segment_analysis: Optional[dict] = None
    performance_predictions: Optional[dict] = None
    pauses: Optional[dict] = None
    climbs: Optional[dict] = None
    splits: Optional[dict] = None
    garmin_summary: Optional[dict] = None
    cadence: Optional[dict] = None
    power: Optional[dict] = None
    running_dynamics: Optional[dict] = None
    power_advanced: Optional[dict] = None
    pacing: Optional[dict] = None
    training_load: Optional[dict] = None
    series_index: SeriesIndex
    limits: Optional[ActivityLimitsDetail] = None


# 4. GET /activity/{id}/theoretical - Response
class TheoreticalActivityResponse(RealActivityResponse):
    pass  # Hérite structure identique


# 5. GET /activity/{id}/series/{name} - Response
class SeriesMeta(BaseModel):
    downsampled: Optional[bool] = None
    original_points: Optional[int] = None
    returned_points: Optional[int] = None


class SeriesResponse(BaseModel):
    name: str
    x_axis: Literal["time", "distance"]
    unit: str
    x: List[float]  # Coordonnées x
    y: List[float]  # Coordonnées y
    meta: Optional[SeriesMeta] = None


# 6. GET /activity/{id}/map - Response
class MapMarker(BaseModel):
    lat: float
    lon: float
    label: Optional[str] = None
    type: Optional[str] = None


class ActivityMapResponse(BaseModel):
    bbox: List[float]  # [minLon, minLat, maxLon, maxLat]
    polyline: List[List[float]]  # [[lat, lon], ...]
    markers: Optional[List[MapMarker]] = None


# Storage metadata
class ActivityMetadata(BaseModel):
    id: str
    filename: str
    name: Optional[str] = None
    activity_type: Literal["real", "theoretical"]
    created_at: datetime
    stats_sidebar: SidebarStats
    file_hash: str


# API Request models
class ActivityLoadRequest(BaseModel):
    name: Optional[str] = None


class SeriesRequest(BaseModel):
    activity_id: str
    series_name: str
    x_axis: Optional[Literal["time", "distance"]] = "time"
    from_val: Optional[float] = None
    to_val: Optional[float] = None
    downsample: Optional[int] = None
