"""Adapters pour assurer la compatibilité entre API et services existants."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import pandas as pd

from services.models import LoadedActivity as ServiceLoadedActivity, ActivityTypeDetection, ActivityType


@dataclass
class LoadedActivity:
    """Version adaptée de LoadedActivity pour l'API."""
    name: str
    df: pd.DataFrame
    type: str
    raw_bytes: bytes
    
    def to_service_model(self) -> ServiceLoadedActivity:
        """Convertit vers le modèle des services"""
        activity_type = ActivityType.REAL_RUN if self.type == "real" else ActivityType.THEORETICAL_ROUTE
        gpx_type = ActivityTypeDetection(type=activity_type, confidence=1.0)
        
        return ServiceLoadedActivity(
            name=self.name,
            df=self.df,
            gpx_type=gpx_type,
            track_count=1
        )
    
    @classmethod
    def from_service_model(cls, activity: ServiceLoadedActivity, raw_bytes: bytes = b"") -> LoadedActivity:
        """Convertit depuis le modèle des services"""
        activity_type = "real" if activity.gpx_type.type == "real_run" else "theoretical"
        
        return cls(
            name=activity.name,
            df=activity.df,
            type=activity_type,
            raw_bytes=raw_bytes
        )