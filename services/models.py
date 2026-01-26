from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

import pandas as pd


ActivityType = Literal["real_run", "theoretical_route"]


@dataclass(frozen=True)
class ActivityTypeDetection:
    type: ActivityType
    confidence: float


@dataclass(frozen=True)
class LoadedActivity:
    name: str
    df: pd.DataFrame
    gpx_type: ActivityTypeDetection
    track_count: int


@dataclass(frozen=True)
class SidebarStats:
    distance_km: float | None
    elev_gain_m: float | None
    duration_s: float | None
    start_time: pd.Timestamp | None


@dataclass(frozen=True)
class RealRunParams:
    use_moving_time: bool = True
    hr_max: float | None = None
    hr_rest: float | None = None
    use_hrr: bool = False
    pace_threshold_s_per_km: float | None = None
    ftp_w: float | None = None
    cadence_target: float | None = None


RealRunPaceMode = Literal["real_time", "moving_time"]
RealRunMapColorMode = Literal["pace", "grade", "gap"]


@dataclass(frozen=True)
class RealRunViewParams:
    pace_mode: RealRunPaceMode = "real_time"
    smoothing_points: int = 20
    cap_min_per_km: float | None = None
    map_color_mode: RealRunMapColorMode = "pace"


@dataclass(frozen=True)
class TheoreticalParams:
    base_pace_s_per_km: float
    start_datetime: datetime | None = None
    passage_distances_km: list[float] | None = None
    smoothing_segments: int = 20
    cap_min_per_km: float | None = None
    weather_factor: float = 1.0
    split_bias_pct: float = 0.0
    cap_adv_min_per_km: float | None = None


@dataclass(frozen=True)
class RealRunDerived:
    grade_series: pd.Series
    moving_mask: pd.Series
    gap_series: pd.Series


@dataclass(frozen=True)
class RealRunMapPayload:
    map_df: pd.DataFrame
    climb_points: list[dict[str, Any]]
    pause_points: list[dict[str, Any]]


@dataclass(frozen=True)
class RealRunFigures:
    pace_elevation: Any
    distributions: dict[str, Any]
    pace_vs_grade: Any
    residuals_vs_grade: Any
    pace_grade_scatter: Any
    pace_grade_heatmap: Any


@dataclass(frozen=True)
class RealRunResult:
    derived: RealRunDerived
    summary: dict[str, Any]
    garmin: dict[str, Any]
    zone_defaults: dict[str, Any]
    best_efforts: pd.DataFrame
    climbs: list[dict[str, Any]]
    pauses: list[dict[str, Any]]
    highlights: list[str]
    pace_series: pd.Series
    default_cap_min_per_km: float
    splits: pd.DataFrame
    map_payload: RealRunMapPayload
    figures: RealRunFigures


@dataclass(frozen=True)
class RealRunBase:
    derived: RealRunDerived
    summary: dict[str, Any]
    zone_defaults: dict[str, Any]
    best_efforts: pd.DataFrame
    climbs: list[dict[str, Any]]
    pauses: list[dict[str, Any]]
    splits: pd.DataFrame
    default_cap_min_per_km: float


@dataclass(frozen=True)
class TheoreticalBase:
    df_base: pd.DataFrame
    summary_base: dict[str, Any]
    default_cap_min_per_km: float


@dataclass(frozen=True)
class TheoreticalPassages:
    df_calc: pd.DataFrame
    passages: pd.DataFrame
    markers: list[dict[str, Any]]


@dataclass(frozen=True)
class TheoreticalAdvanced:
    df_adjusted: pd.DataFrame
    df_adjusted_display: pd.DataFrame
    summary_adjusted: dict[str, Any]
    categories: list[dict[str, Any]]
    figure: Any
    csv_data: str


@dataclass(frozen=True)
class TheoreticalFigures:
    base: Any
    advanced: Any


@dataclass(frozen=True)
class TheoreticalResult:
    base: TheoreticalBase
    df_display: pd.DataFrame
    passages: TheoreticalPassages
    splits: pd.DataFrame
    figures: TheoreticalFigures
    advanced: TheoreticalAdvanced
