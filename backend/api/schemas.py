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
    type: Literal["real"]
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
    activity_name: Optional[str] = None
    started_at_utc: Optional[str] = None
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


# 4. GET /activity/{id}/series/{name} - Response
class SeriesMeta(BaseModel):
    downsampled: Optional[bool] = None
    original_points: Optional[int] = None
    returned_points: Optional[int] = None


class SeriesResponse(BaseModel):
    name: str
    x_axis: Literal["time", "distance"]
    x_unit: Literal["s", "km"]
    unit: str
    x: List[float]  # Coordonnées x
    y: List[Optional[float]]  # Coordonnées y (null si valeur manquante/invalidée)
    meta: Optional[SeriesMeta] = None


# 6. GET /activity/{id}/map - Response
class MapMarker(BaseModel):
    lat: float
    lon: float
    label: Optional[str] = None
    type: Optional[str] = None


class ActivityMapPoint(BaseModel):
    distance_km: float
    lat: float
    lon: float


class ActivityMapResponse(BaseModel):
    bbox: List[float]  # [minLon, minLat, maxLon, maxLat]
    polyline: List[List[float]]  # [[lat, lon], ...]
    markers: Optional[List[MapMarker]] = None
    points: Optional[List[ActivityMapPoint]] = None


# Storage metadata
class ActivityMetadata(BaseModel):
    id: str
    filename: str
    name: Optional[str] = None
    activity_type: Literal["real"]
    created_at: datetime
    started_at: Optional[datetime] = None
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


# 7. GET /activity/{id}/pace-vs-grade - Response
class PaceVsGradeBin(BaseModel):
    grade_center: float
    pace_med_s_per_km: float
    pace_std_s_per_km: float
    pace_n: int
    pro_pace_s_per_km: Optional[float] = None

    # Optional, richer stats (time-weighted / robust).
    time_s_bin: Optional[float] = None
    pace_mean_w_s_per_km: Optional[float] = None
    pace_q25_w_s_per_km: Optional[float] = None
    pace_q50_w_s_per_km: Optional[float] = None
    pace_q75_w_s_per_km: Optional[float] = None
    pace_iqr_w_s_per_km: Optional[float] = None
    pace_std_w_s_per_km: Optional[float] = None
    pace_n_eff: Optional[float] = None
    outlier_clip_frac: Optional[float] = None


class ProPaceVsGradePoint(BaseModel):
    grade_percent: float
    pace_s_per_km_pro: float


class PaceVsGradeResponse(BaseModel):
    bins: List[PaceVsGradeBin]
    pro_ref: List[ProPaceVsGradePoint]


class TraceItem(BaseModel):
    id: str
    name: Optional[str] = None
    created_at_utc: str
    distance_km: float
    elevation_gain_m: float
    elevation_loss_m: Optional[float] = None
    elevation_min_m: Optional[float] = None
    elevation_max_m: Optional[float] = None
    original_filename: Optional[str] = None


class TracesListResponse(BaseModel):
    traces: List[TraceItem]
    sync: Optional[dict] = None


class TraceUploadResponse(BaseModel):
    trace: TraceItem


class TraceStatusResponse(BaseModel):
    saved: bool
    trace_id: Optional[str] = None
    trace_name: Optional[str] = None


class PersonalSettingsResponse(BaseModel):
    vma_kmh: Optional[float] = None
    vo2max_lastest: Optional[float] = None
    hr_max_manual_bpm: Optional[int] = None
    hr_max_source: Literal["detected", "manual"] = "detected"
    hr_max_detected_bpm: Optional[int] = None
    hr_max_effective_bpm: Optional[int] = None
    updated_at_utc: str


class PersonalSettingsPatchRequest(BaseModel):
    vma_kmh: Optional[float] = None
    hr_max_manual_bpm: Optional[int] = None
    hr_max_source: Optional[Literal["detected", "manual"]] = None


class GoalItem(BaseModel):
    id: str
    name: str
    event_date: str
    distance_km: float
    location: Optional[str] = None
    location_city: Optional[str] = None
    location_country: Optional[str] = None
    location_country_code: Optional[str] = None
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None
    target_time_s: Optional[float] = None
    target_pace_s_per_km: Optional[float] = None
    race_type: Literal["road", "trail"]
    notes: Optional[str] = None
    created_at_utc: str
    updated_at_utc: str


class GoalCreateRequest(BaseModel):
    name: str
    event_date: str
    distance_km: float
    location: Optional[str] = None
    location_city: Optional[str] = None
    location_country: Optional[str] = None
    location_country_code: Optional[str] = None
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None
    target_time_s: Optional[float] = None
    target_pace_s_per_km: Optional[float] = None
    race_type: Literal["road", "trail"]
    notes: Optional[str] = None


class GoalUpdateRequest(BaseModel):
    name: Optional[str] = None
    event_date: Optional[str] = None
    distance_km: Optional[float] = None
    location: Optional[str] = None
    location_city: Optional[str] = None
    location_country: Optional[str] = None
    location_country_code: Optional[str] = None
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None
    target_time_s: Optional[float] = None
    target_pace_s_per_km: Optional[float] = None
    race_type: Optional[Literal["road", "trail"]] = None
    notes: Optional[str] = None


class GoalsListResponse(BaseModel):
    goals: List[GoalItem]


class GeoCityItem(BaseModel):
    label: str
    city: str
    country: str
    country_code: Optional[str] = None
    lat: float
    lon: float


class GeoCitiesResponse(BaseModel):
    query: str
    results: List[GeoCityItem]


class RealActivityPaceElevationPoint(BaseModel):
    distance_km: float
    pace_s_per_km: float
    elevation_m: Optional[float] = None


class RealActivityBinsResponse(BaseModel):
    pace_elevation_series: List[RealActivityPaceElevationPoint]
    pace_time_bins: List[dict]
    grade_time_bins: List[dict]
    pace_histogram: dict
    grade_histogram: dict
