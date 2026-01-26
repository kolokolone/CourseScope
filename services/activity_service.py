from __future__ import annotations

"""Activity loading + light metadata.

This module is Streamlit-free and can be reused from a future API.
"""

import io
from pathlib import Path

import pandas as pd

from core import fit_loader, gpx_loader
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

    detection = ActivityTypeDetection(type=gpx_type_raw["type"], confidence=float(gpx_type_raw["confidence"]))
    return LoadedActivity(name=name, df=df, gpx_type=detection, track_count=int(track_count))


def compute_sidebar_stats(df: pd.DataFrame) -> SidebarStats:
    distance_km = None
    elev_gain_m = None
    duration_s = None
    start_time = None

    if "distance_m" in df:
        dist_m = df["distance_m"].dropna()
        distance_km = float(dist_m.max() / 1000.0) if not dist_m.empty else None

    if "elevation" in df:
        elev = df["elevation"].dropna()
        if len(elev) > 1:
            gain = elev.diff().clip(lower=0).sum()
            elev_gain_m = float(gain)

    if "time" in df:
        times = pd.to_datetime(df["time"]).dropna()
        if len(times) >= 2:
            start = times.iloc[0]
            end = times.iloc[-1]
            start_time = start
            duration_s = float((end - start).total_seconds())

    return SidebarStats(distance_km=distance_km, elev_gain_m=elev_gain_m, duration_s=duration_s, start_time=start_time)


def suggest_default_view(activity_type: ActivityTypeDetection) -> str:
    return "real" if activity_type.type == "real_run" else "theoretical"
