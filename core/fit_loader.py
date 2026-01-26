from __future__ import annotations

import math
from typing import IO, Any, Dict

import numpy as np
import pandas as pd
from fitparse import FitFile
from gpxpy import geo as gpx_geo

from core.gpx_loader import COLUMNS, MIN_DISTANCE_FOR_SPEED_M, MIN_SPEED_M_S, MAX_SPEED_M_S


SEMICIRCLE_TO_DEG = 180.0 / (2**31)


def _semicircle_to_deg(value: float | int | None) -> float:
    if value is None:
        return math.nan
    try:
        return float(value) * SEMICIRCLE_TO_DEG
    except (TypeError, ValueError):
        return math.nan


def _distance_3d(
    lat1: float | None,
    lon1: float | None,
    ele1: float | None,
    lat2: float | None,
    lon2: float | None,
    ele2: float | None,
) -> float:
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 0.0
    if not (np.isfinite(lat1) and np.isfinite(lon1) and np.isfinite(lat2) and np.isfinite(lon2)):
        return 0.0
    dist_2d = gpx_geo.haversine_distance(lat1, lon1, lat2, lon2)
    if ele1 is None or ele2 is None:
        return dist_2d
    if not (np.isfinite(ele1) and np.isfinite(ele2)):
        return dist_2d
    delta_elev = ele2 - ele1
    return math.sqrt(dist_2d * dist_2d + delta_elev * delta_elev)


def load_fit(file: IO[bytes]) -> FitFile:
    """Lit un fichier FIT (file-like) et retourne l'objet FitFile."""
    return FitFile(file)


def fit_to_dataframe(fitfile: FitFile) -> pd.DataFrame:
    """
    Transforme un FIT en DataFrame avec distances, temps et vitesses.
    """
    rows = []
    cumulative_distance = 0.0
    start_time = None
    prev_time = None
    prev_lat = None
    prev_lon = None
    prev_ele = None
    prev_distance = None

    for record in fitfile.get_messages("record"):
        lat_raw = record.get_value("position_lat")
        lon_raw = record.get_value("position_long")
        lat = _semicircle_to_deg(lat_raw)
        lon = _semicircle_to_deg(lon_raw)

        elev = record.get_value("enhanced_altitude")
        if elev is None:
            elev = record.get_value("altitude")

        current_time = record.get_value("timestamp")
        if start_time is None and current_time is not None:
            start_time = current_time

        if current_time is not None and prev_time is not None:
            delta_time = (current_time - prev_time).total_seconds()
        else:
            delta_time = math.nan
        if delta_time is not None and delta_time <= 0:
            delta_time = math.nan

        elapsed_time = (
            (current_time - start_time).total_seconds()
            if start_time is not None and current_time is not None
            else math.nan
        )

        distance_m = record.get_value("distance")
        use_geo = False
        if distance_m is None or not np.isfinite(distance_m):
            use_geo = True
        elif prev_distance is not None and distance_m < prev_distance:
            use_geo = True

        if use_geo:
            delta_distance = _distance_3d(prev_lat, prev_lon, prev_ele, lat, lon, elev)
            if delta_distance is None or (isinstance(delta_distance, float) and math.isnan(delta_distance)):
                delta_distance = 0.0
            cumulative_distance += delta_distance
            distance_m = cumulative_distance
        else:
            delta_distance = 0.0 if prev_distance is None else distance_m - prev_distance
            cumulative_distance = float(distance_m)

        speed_from_delta = False
        speed_m_s = math.nan
        if delta_time is not None and delta_time > 0 and delta_distance > 0:
            speed_m_s = delta_distance / delta_time
            speed_from_delta = True
        if speed_m_s != speed_m_s:
            speed_m_s = record.get_value("enhanced_speed")
            if speed_m_s is None:
                speed_m_s = record.get_value("speed")

        if speed_from_delta and delta_distance < MIN_DISTANCE_FOR_SPEED_M:
            speed_m_s = math.nan

        if speed_m_s is None or not (MIN_SPEED_M_S <= speed_m_s <= MAX_SPEED_M_S):
            speed_m_s = math.nan

        pace_s_per_km = 1000.0 / speed_m_s if speed_m_s and speed_m_s > 0 else math.nan

        rows.append(
            {
                "lat": lat,
                "lon": lon,
                "elevation": elev,
                "time": current_time,
                "distance_m": distance_m,
                "delta_distance_m": delta_distance,
                "elapsed_time_s": elapsed_time,
                "delta_time_s": delta_time,
                "speed_m_s": speed_m_s,
                "pace_s_per_km": pace_s_per_km,
                "heart_rate": record.get_value("heart_rate"),
                "cadence": record.get_value("cadence"),
                "power": record.get_value("power"),
            }
        )

        prev_time = current_time
        prev_lat = lat
        prev_lon = lon
        prev_ele = elev
        prev_distance = distance_m

    if not rows:
        return pd.DataFrame(columns=COLUMNS)

    return pd.DataFrame(rows, columns=COLUMNS)


def detect_fit_type(df: pd.DataFrame) -> Dict[str, Any]:
    """Reutilise la detection GPX pour classer la trace FIT."""
    from core.gpx_loader import detect_gpx_type

    return detect_gpx_type(df)
