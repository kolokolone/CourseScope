from __future__ import annotations

import datetime
import math
from typing import IO, Any, Dict

import numpy as np
import pandas as pd
from fitparse import FitFile
from gpxpy import geo as gpx_geo

from core.constants import MAX_SPEED_M_S, MIN_DISTANCE_FOR_SPEED_M, MIN_SPEED_M_S
from core.contracts.activity_df_contract import COLUMNS


SEMICIRCLE_TO_DEG = 180.0 / (2**31)


def _patch_fitparse_datetime() -> None:
    """Remplace utcfromtimestamp (deprecated) par une conversion UTC moderne."""
    try:
        from fitparse import processors as fit_processors
    except Exception:
        return

    if getattr(fit_processors, "_coursescope_datetime_patch", False):
        return

    def _to_utc_naive(value: float) -> datetime.datetime:
        dt = datetime.datetime.fromtimestamp(fit_processors.UTC_REFERENCE + value, datetime.UTC)
        return dt.replace(tzinfo=None)

    def _process_type_date_time(self, field_data):
        value = field_data.value
        if value is not None and value >= 0x10000000:
            field_data.value = _to_utc_naive(value)
            field_data.units = None

    def _process_type_local_date_time(self, field_data):
        if field_data.value is not None:
            field_data.value = _to_utc_naive(field_data.value)
            field_data.units = None

    fit_processors.FitFileDataProcessor.process_type_date_time = _process_type_date_time
    fit_processors.FitFileDataProcessor.process_type_local_date_time = _process_type_local_date_time
    fit_processors._coursescope_datetime_patch = True


_patch_fitparse_datetime()


def _build_field_lookup(record) -> dict[str, tuple[Any, str | None]]:
    lookup: dict[str, tuple[Any, str | None]] = {}
    try:
        fields = getattr(record, "fields", None)
    except Exception:
        fields = None
    if not fields:
        return lookup
    try:
        for f in fields:
            fname = getattr(f, "name", None)
            if not fname:
                continue
            lookup[str(fname)] = (getattr(f, "value", None), getattr(f, "units", None))
    except Exception:
        return lookup
    return lookup


def _get_value(record, name: str, lookup: dict[str, tuple[Any, str | None]] | None) -> Any:
    if lookup is not None and name in lookup:
        return lookup[name][0]
    try:
        return record.get_value(name)
    except Exception:
        return None


def _field_value_and_units(
    record,
    name: str,
    *,
    lookup: dict[str, tuple[Any, str | None]] | None = None,
) -> tuple[float, str | None]:
    """Retourne (valeur, unites) pour un champ FIT, converti en float si possible."""

    raw = None
    units = None
    if lookup is not None and name in lookup:
        raw, units = lookup[name]
    else:
        raw = _get_value(record, name, lookup)

    if raw is None:
        return math.nan, units
    try:
        return float(raw), units
    except (TypeError, ValueError):
        return math.nan, units


def _convert_stride_length_m(value: float, units: str | None) -> float:
    if not np.isfinite(value):
        return math.nan
    u = (units or "").lower()
    if u in {"m", "meter", "meters"}:
        return float(value)
    if u in {"cm", "centimeter", "centimeters"}:
        return float(value) / 100.0
    # Heuristique: des valeurs > 3 sont probablement en centimetres
    if value > 3:
        return float(value) / 100.0
    return float(value)


def _convert_vertical_oscillation_cm(value: float, units: str | None) -> float:
    if not np.isfinite(value):
        return math.nan
    u = (units or "").lower()
    if u in {"cm", "centimeter", "centimeters"}:
        return float(value)
    if u in {"mm", "millimeter", "millimeters"}:
        return float(value) / 10.0
    if u in {"m", "meter", "meters"}:
        return float(value) * 100.0
    # Heuristique: VO typique ~5-15 cm; des grandes valeurs sont souvent en mm
    if value > 40:
        return float(value) / 10.0
    if 0 < value < 1:
        return float(value) * 100.0
    return float(value)


def _convert_vertical_ratio_pct(value: float, units: str | None) -> float:
    if not np.isfinite(value):
        return math.nan
    u = (units or "").lower()
    if "%" in u or "percent" in u:
        return float(value)
    # Heuristique: ratio 0-1 -> %
    if 0 <= value <= 1.0:
        return float(value) * 100.0
    return float(value)


def _convert_ground_contact_time_ms(value: float, units: str | None) -> float:
    if not np.isfinite(value):
        return math.nan
    u = (units or "").lower()
    if u in {"ms", "millisecond", "milliseconds"}:
        return float(value)
    if u in {"s", "sec", "second", "seconds"}:
        return float(value) * 1000.0
    # Heuristique: 0.2-0.4 secondes vs 200-400 ms
    if value < 10:
        return float(value) * 1000.0
    return float(value)


def _convert_gct_balance_pct(value: float, units: str | None) -> float:
    if not np.isfinite(value):
        return math.nan
    u = (units or "").lower()
    if "%" in u or "percent" in u:
        return float(value)
    if 0 <= value <= 1.0:
        return float(value) * 100.0
    return float(value)


def _first_value_and_units(
    record,
    names: list[str],
    *,
    lookup: dict[str, tuple[Any, str | None]] | None = None,
) -> tuple[float, str | None]:
    for name in names:
        value, units = _field_value_and_units(record, name, lookup=lookup)
        if np.isfinite(value):
            return value, units
    return math.nan, None


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
        lookup = _build_field_lookup(record)

        lat_raw = _get_value(record, "position_lat", lookup)
        lon_raw = _get_value(record, "position_long", lookup)
        lat = _semicircle_to_deg(lat_raw)
        lon = _semicircle_to_deg(lon_raw)

        elev = _get_value(record, "enhanced_altitude", lookup)
        if elev is None:
            elev = _get_value(record, "altitude", lookup)

        current_time = _get_value(record, "timestamp", lookup)
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

        distance_m = _get_value(record, "distance", lookup)
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
            speed_m_s = _get_value(record, "enhanced_speed", lookup)
            if speed_m_s is None:
                speed_m_s = _get_value(record, "speed", lookup)

        if speed_from_delta and delta_distance < MIN_DISTANCE_FOR_SPEED_M:
            speed_m_s = math.nan

        if speed_m_s is None or not (MIN_SPEED_M_S <= speed_m_s <= MAX_SPEED_M_S):
            speed_m_s = math.nan

        pace_s_per_km = 1000.0 / speed_m_s if speed_m_s and speed_m_s > 0 else math.nan

        stride_value, stride_units = _first_value_and_units(
            record,
            ["stride_length", "enhanced_stride_length"],
            lookup=lookup,
        )
        stride_length_m = _convert_stride_length_m(stride_value, stride_units)

        vo_value, vo_units = _first_value_and_units(
            record,
            ["vertical_oscillation", "enhanced_vertical_oscillation"],
            lookup=lookup,
        )
        vertical_oscillation_cm = _convert_vertical_oscillation_cm(vo_value, vo_units)

        vr_value, vr_units = _first_value_and_units(record, ["vertical_ratio"], lookup=lookup)
        vertical_ratio_pct = _convert_vertical_ratio_pct(vr_value, vr_units)

        gct_value, gct_units = _first_value_and_units(record, ["ground_contact_time"], lookup=lookup)
        ground_contact_time_ms = _convert_ground_contact_time_ms(gct_value, gct_units)

        gctb_value, gctb_units = _first_value_and_units(record, ["ground_contact_time_balance"], lookup=lookup)
        gct_balance_pct = _convert_gct_balance_pct(gctb_value, gctb_units)

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
                "heart_rate": _get_value(record, "heart_rate", lookup),
                "cadence": _get_value(record, "cadence", lookup),
                "power": _get_value(record, "power", lookup),
                "stride_length_m": stride_length_m,
                "vertical_oscillation_cm": vertical_oscillation_cm,
                "vertical_ratio_pct": vertical_ratio_pct,
                "ground_contact_time_ms": ground_contact_time_ms,
                "gct_balance_pct": gct_balance_pct,
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
