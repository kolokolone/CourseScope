import math
from typing import Union


def mmss_to_seconds(value: str) -> int:
    """
    Convertit une chaîne "M:SS" ou "MM:SS" en nombre de secondes.
    """
    if not isinstance(value, str):
        raise ValueError("La valeur doit être une chaîne.")

    text = value.strip()
    if ":" not in text:
        raise ValueError("Format attendu M:SS.")

    minutes_str, seconds_str = text.split(":", 1)
    minutes = int(minutes_str)
    seconds = int(seconds_str)
    if minutes < 0:
        raise ValueError("Minutes négatives interdites.")
    if seconds < 0 or seconds >= 60:
        raise ValueError("Secondes invalides dans l'allure.")
    return minutes * 60 + seconds


def seconds_to_mmss(seconds: Union[int, float]) -> str:
    """
    Convertit un nombre de secondes en format M:SS.
    """
    total_seconds = int(round(seconds))
    minutes = total_seconds // 60
    secs = total_seconds % 60
    return f"{minutes}:{secs:02d}"


def pace_min_per_km_to_m_s(pace_s_per_km: float) -> float:
    """
    Convertit une allure en s/km vers m/s.
    """
    if pace_s_per_km <= 0:
        return math.nan
    return 1000.0 / pace_s_per_km


def pace_min_per_km_to_min_per_mile(pace_s_per_km: float) -> float:
    """
    Convertit s/km vers s/mile (1 mile = 1.609344 km).
    """
    return pace_s_per_km * 1.609344


def min_per_mile_to_pace_min_per_km(pace_s_per_mile: float) -> float:
    """
    Convertit s/mile vers s/km.
    """
    return pace_s_per_mile / 1.609344
