from __future__ import annotations

"""Chargement d'activite + metadonnees legeres.

Ce module est sans Streamlit et peut etre reutilise depuis une future API.
"""

import io
from pathlib import Path

import pandas as pd

from core import fit_loader, gpx_loader
from core.contracts.activity_df_contract import coerce_activity_df, validate_activity_df
from core.stats.basic_stats import compute_basic_stats
from services.models import ActivityTypeDetection, LoadedActivity, SidebarStats


def load_activity_from_bytes(data: bytes, name: str) -> LoadedActivity:
    extension = Path(name).suffix.lower()
    if extension == ".fit":
        fit = fit_loader.load_fit(io.BytesIO(data))
        df = fit_loader.fit_to_dataframe(fit)
        gpx_type_raw = fit_loader.detect_fit_type(df)
        track_count = 1 if not df.empty else 0
    else:
        gpx = gpx_loader.load_gpx(io.BytesIO(data))
        df = gpx_loader.gpx_to_dataframe(gpx)
        gpx_type_raw = gpx_loader.detect_gpx_type(df)
        track_count = len(gpx.tracks)

    # Coerce schema/dtypes canoniques et valide une seule fois a la frontiere service.
    # Pour une entree GPX, les colonnes running dynamics sont typiquement a NaN.
    # Pour une entree FIT, les running dynamics sont optionnelles (beaucoup de FIT n'en ont pas).
    df = coerce_activity_df(df)
    if extension == ".fit":
        # FIT : running dynamics optionnelles (pas d'attente)
        expect_running_dynamics_all_nan = None
    else:
        # GPX : attendu que toutes les running dynamics soient a NaN
        expect_running_dynamics_all_nan = True
    
    report = validate_activity_df(
        df,
        expect_running_dynamics_all_nan=expect_running_dynamics_all_nan,
    )
    report.raise_for_issues()

    detection = ActivityTypeDetection(type=gpx_type_raw["type"], confidence=float(gpx_type_raw["confidence"]))
    return LoadedActivity(name=name, df=df, gpx_type=detection, track_count=int(track_count))


def compute_sidebar_stats(df: pd.DataFrame) -> SidebarStats:
    stats = compute_basic_stats(df)
    return SidebarStats(
        distance_km=stats.distance_km if stats.distance_km > 0 else None,
        elev_gain_m=stats.elevation_gain_m if stats.elevation_gain_m > 0 else None,
        duration_s=stats.total_time_s if stats.total_time_s > 0 else None,
        start_time=stats.start_time,
    )


def suggest_default_view(activity_type: ActivityTypeDetection) -> str:
    return "real" if activity_type.type == "real_run" else "theoretical"
