from __future__ import annotations

from dataclasses import dataclass
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
    df: pd.DataFrame | None
    gpx_type: ActivityTypeDetection
    track_count: int

    # Champs ajoutés pour compatibilité API
    @property
    def type(self) -> str:
        """Retourne le type pour l'API ('real' ou 'theoretical')"""
        return "real" if self.gpx_type.type == "real_run" else "theoretical"

    @property
    def raw_bytes(self) -> bytes:
        """Placeholder - à implémenter avec stockage réel"""
        return b""


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
    best_efforts_time: pd.DataFrame
    climbs: list[dict[str, Any]]
    pauses: list[dict[str, Any]]
    highlights: list[str]
    pace_series: pd.Series
    default_cap_min_per_km: float
    splits: pd.DataFrame
    performance_predictions: list[dict[str, Any]]
    map_payload: RealRunMapPayload
    figures: RealRunFigures


@dataclass(frozen=True)
class RealRunBase:
    derived: RealRunDerived
    summary: dict[str, Any]
    zone_defaults: dict[str, Any]
    best_efforts: pd.DataFrame
    best_efforts_time: pd.DataFrame
    climbs: list[dict[str, Any]]
    pauses: list[dict[str, Any]]
    splits: pd.DataFrame
    default_cap_min_per_km: float
