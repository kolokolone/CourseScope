from __future__ import annotations

import math
from typing import IO, Any, Dict
from xml.etree import ElementTree as ET

import gpxpy
import pandas as pd

COLUMNS = [
    "lat",
    "lon",
    "elevation",
    "time",
    "distance_m",
    "delta_distance_m",
    "elapsed_time_s",
    "delta_time_s",
    "speed_m_s",
    "pace_s_per_km",
    "heart_rate",
    "cadence",
    "power",
    "stride_length_m",
    "vertical_oscillation_cm",
    "vertical_ratio_pct",
    "ground_contact_time_ms",
    "gct_balance_pct",
]

MIN_SPEED_M_S = 0.5  # ~33 min/km
MAX_SPEED_M_S = 8.0  # ~2:05 min/km
MIN_DISTANCE_FOR_SPEED_M = 0.5

HR_TAGS = {"hr", "heart_rate", "heartrate"}
CAD_TAGS = {"cad", "cadence"}
POWER_TAGS = {"power", "watts"}


def _decode_gpx_bytes(content: bytes) -> str:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return content.decode("latin-1")
        except UnicodeDecodeError:
            return content.decode("utf-8", errors="replace")


def _local_tag(tag: str | None) -> str:
    if not tag:
        return ""
    return tag.split("}")[-1].lower()


def _extract_extension_value(extensions: list[ET.Element] | None, targets: set[str]) -> float:
    if not extensions:
        return math.nan
    for ext in extensions:
        for elem in ext.iter():
            local = _local_tag(elem.tag)
            if local in targets:
                try:
                    return float(elem.text)
                except (TypeError, ValueError):
                    continue
    return math.nan


def load_gpx(file: IO[bytes]) -> gpxpy.gpx.GPX:
    """
    Lit un fichier GPX (Streamlit UploadedFile ou file-like) et retourne l'objet GPX.
    """
    content = file.read()
    if isinstance(content, (bytes, bytearray)):
        text = _decode_gpx_bytes(content)
    else:
        text = str(content)
    return gpxpy.parse(text)


def gpx_to_dataframe(gpx: gpxpy.gpx.GPX) -> pd.DataFrame:
    """
    Transforme un GPX en DataFrame avec distances, temps et vitesses.
    """
    rows = []
    cumulative_distance = 0.0
    start_time = None

    for track in gpx.tracks:
        for segment in track.segments:
            prev_point = None
            prev_time = None

            for point in segment.points:
                delta_distance = point.distance_3d(prev_point) if prev_point is not None else 0.0
                if delta_distance is None or (isinstance(delta_distance, float) and math.isnan(delta_distance)):
                    delta_distance = 0.0
                cumulative_distance += delta_distance

                current_time = point.time
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

                speed_m_s = (
                    delta_distance / delta_time if delta_time is not None and delta_time > 0 else math.nan
                )

                if delta_distance < MIN_DISTANCE_FOR_SPEED_M:
                    speed_m_s = math.nan

                # Filtre les vitesses irréalistes pour éviter des pics d'allure
                if not (MIN_SPEED_M_S <= speed_m_s <= MAX_SPEED_M_S):
                    speed_m_s = math.nan

                pace_s_per_km = 1000.0 / speed_m_s if speed_m_s and speed_m_s > 0 else math.nan

                heart_rate = _extract_extension_value(point.extensions, HR_TAGS)
                cadence = _extract_extension_value(point.extensions, CAD_TAGS)
                power = _extract_extension_value(point.extensions, POWER_TAGS)

                rows.append(
                    {
                        "lat": point.latitude,
                        "lon": point.longitude,
                        "elevation": point.elevation,
                        "time": current_time,
                        "distance_m": cumulative_distance,
                        "delta_distance_m": delta_distance,
                        "elapsed_time_s": elapsed_time,
                        "delta_time_s": delta_time,
                        "speed_m_s": speed_m_s,
                        "pace_s_per_km": pace_s_per_km,
                        "heart_rate": heart_rate,
                        "cadence": cadence,
                        "power": power,
                    }
                )

                prev_point = point
                prev_time = current_time

    if not rows:
        return pd.DataFrame(columns=COLUMNS)

    return pd.DataFrame(rows, columns=COLUMNS)


def detect_gpx_type(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Détermine si la trace ressemble à une vraie sortie ou à un tracé théorique.
    """
    delta_time = df["delta_time_s"].dropna()
    speeds = df["speed_m_s"].dropna()

    score_time = 0.0
    if len(delta_time) > 0:
        within = delta_time[(delta_time >= 1) & (delta_time <= 10)]
        score_time = len(within) / len(delta_time)

    score_speed = 0.0
    if len(speeds) > 0:
        score_speed = (speeds > MIN_SPEED_M_S).sum() / len(speeds)

    confidence = 0.6 * score_time + 0.4 * score_speed
    run_type = "real_run" if confidence >= 0.5 else "theoretical_route"
    return {"type": run_type, "confidence": round(confidence, 3)}
