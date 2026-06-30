import math
import re
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


_PACE_RE = re.compile(r"^\s*(\d{1,2})\s*[:h]\s*(\d{1,2})(?:\s*[:m]\s*(\d{1,2}))?\s*$")


def parse_ts_utc(value: str | None, *, is_end: bool) -> str | None:
    """Parse une date/heure ISO ou YYYY-MM-DD en UTC ISO string. Leve ValueError si invalide."""
    from datetime import datetime, timezone
    if value is None:
        return None
    raw = str(value).strip()
    if raw == "":
        return None
    if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
        if is_end:
            raw = f"{raw}T23:59:59Z"
        else:
            raw = f"{raw}T00:00:00Z"
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        raise ValueError(f"Invalid datetime: {value}")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc).replace(microsecond=0)
    return dt.isoformat().replace("+00:00", "Z")


def bucket_start(dt, group_by: str):
    """Retourne le debut du bucket (jour/semaine/mois) pour un datetime."""
    from datetime import datetime, timezone, timedelta
    d = dt.astimezone(timezone.utc)
    if group_by == "day":
        return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    if group_by == "month":
        return datetime(d.year, d.month, 1, tzinfo=timezone.utc)
    # group_by == 'week' => ISO week starting Monday.
    base = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    weekday = base.weekday()  # Monday=0
    return base.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=weekday)


def parse_csv_floats(raw: str | None, *, default_values: list[float]) -> list[float]:
    """Parse une chaine CSV de floats. Retourne une liste triee et deduplicatee."""
    if raw is None or str(raw).strip() == "":
        return list(default_values)
    out: list[float] = []
    for part in str(raw).split(","):
        token = part.strip()
        if token == "":
            continue
        try:
            value = float(token)
        except Exception:
            continue
        if math.isfinite(value):
            out.append(value)
    if not out:
        return list(default_values)
    return sorted(set(out))


def parse_optional_bool(value: object) -> bool | None:
    """Parse un booleen optionnel depuis string/bool/None."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in {"1", "true", "yes", "y", "on"}:
        return True
    if s in {"0", "false", "no", "n", "off"}:
        return False
    return None


def is_finite_number(value) -> bool:
    """Retourne True si value est un nombre fini."""
    return isinstance(value, (int, float)) and value == value and math.isfinite(value)


def parse_hms_to_seconds(value: str | None) -> float | None:
    """Parse une duree H:MM:SS ou M:SS en secondes. Retourne float ou None."""
    if value is None:
        return None
    raw = str(value).strip()
    if raw == "":
        return None
    if raw.isdigit():
        out = float(raw)
        return out if out > 0 else None
    match = _PACE_RE.match(raw)
    if not match:
        if ":" in raw:
            parts = [p.strip() for p in raw.split(":")]
            if len(parts) in {2, 3} and all(p.isdigit() for p in parts):
                nums = [int(p) for p in parts]
                if len(nums) == 2:
                    mm, ss = nums
                    return float(mm * 60 + ss)
                hh, mm, ss = nums
                return float(hh * 3600 + mm * 60 + ss)
        return None

    first = int(match.group(1))
    second = int(match.group(2))
    third = match.group(3)
    if third is None:
        return float(first * 60 + second)
    return float(first * 3600 + second * 60 + int(third))


def parse_pace_to_seconds_per_km(value: str | None) -> float | None:
    """Parse une allure (M:SS ou minutes) en s/km. Plage validee [120, 600]."""
    raw = "" if value is None else str(value).strip()
    if raw.isdigit():
        minutes = int(raw)
        if minutes > 0:
            seconds = float(minutes * 60)
        else:
            seconds = None
    else:
        seconds = parse_hms_to_seconds(value)
    if seconds is None:
        return None
    if 120.0 <= seconds <= 600.0:
        return seconds
    return None
