from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.fit_loader import _extract_fit_vo2max, load_fit
from db.models import (
    ProgressActivityIndex,
    UserSettings,
    utc_now_iso,
)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_iso(value: object) -> str | None:
    """Parse une chaine ISO 8601 et retourne une chaine UTC normalisee (ou None)."""
    if not isinstance(value, str) or not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc).replace(microsecond=0)
    return dt.isoformat().replace("+00:00", "Z")


def _parse_iso_datetime(value: object) -> datetime | None:
    """Parse une chaine ISO 8601 et retourne un objet datetime (ou None)."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _to_utc(dt: datetime) -> datetime:
    """Normalise un datetime en UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _format_ts_utc(dt: datetime) -> str:
    """Formate un datetime en chaine ISO UTC (ex: '2024-01-15T10:30:00Z')."""
    dt = _to_utc(dt).replace(microsecond=0)
    return dt.isoformat().replace("+00:00", "Z")


def _infer_started_at_utc_from_df(df: pd.DataFrame) -> str | None:
    """Extrait le timestamp de debut d'un DataFrame et le formate en UTC."""
    if df is None or df.empty:
        return None
    if "time" not in df.columns:
        return None
    try:
        v = df["time"].min()
        if v is None:
            return None
        if isinstance(v, pd.Timestamp):
            dt = v.to_pydatetime()
        elif isinstance(v, datetime):
            dt = v
        else:
            dt = pd.to_datetime(v).to_pydatetime()
        return _format_ts_utc(dt)
    except Exception:
        return None


def _has_valid_vo2max(df: pd.DataFrame) -> bool:
    if df is None or df.empty or "vo2max" not in df.columns:
        return False

    values = pd.to_numeric(df["vo2max"], errors="coerce").dropna()
    if values.empty:
        return False

    value = float(values.iloc[-1])
    return bool(math.isfinite(value) and 10.0 <= value <= 95.0)


def _maybe_backfill_vo2max_from_fit(
    activity_dir: Path, parquet_path: Path, df: pd.DataFrame
) -> pd.DataFrame:
    # Le Parquet est la source enrichie persistante. S'il contient deja une
    # valeur exploitable, ne pas reparcourir le FIT ni reecrire le fichier.
    if _has_valid_vo2max(df):
        return df

    fit_path = _find_original_fit_path(activity_dir)
    if fit_path is None or not fit_path.exists():
        return df

    try:
        with fit_path.open("rb") as fh:
            fit = load_fit(fh)
            fit_vo2 = _extract_fit_vo2max(fit)

        if not math.isfinite(fit_vo2):
            return df
        if fit_vo2 < 10.0 or fit_vo2 > 95.0:
            return df

        fit_vo2_value = float(fit_vo2)
        fit_df = df.copy()
        fit_df["vo2max"] = fit_vo2_value

        # Persist enriched parquet so future reindex passes stay fast.
        try:
            fit_df.to_parquet(parquet_path, engine="pyarrow")
        except Exception:
            pass
        return fit_df
    except Exception:
        return df


def _sync_vo2max_latest_from_index(session: Session) -> None:
    latest_stmt = (
        select(ProgressActivityIndex.vo2max)
        .where(ProgressActivityIndex.vo2max.is_not(None))
        .order_by(ProgressActivityIndex.start_ts_utc.desc())
        .limit(1)
    )
    latest_vo2 = session.execute(latest_stmt).scalar_one_or_none()
    latest_value = float(latest_vo2) if latest_vo2 is not None else None

    settings = session.get(UserSettings, 1)
    if settings is None:
        settings = UserSettings(
            id=1,
            vma_kmh=None,
            vo2max_lastest=latest_value,
            hr_max_manual_bpm=None,
            hr_max_source="detected",
            updated_at_utc=utc_now_iso(),
        )
        session.add(settings)
        return

    if settings.vo2max_lastest != latest_value:
        settings.vo2max_lastest = latest_value
        settings.updated_at_utc = utc_now_iso()


def _find_original_path(activity_dir: Path) -> str | None:
    """Trouve le premier fichier 'original.*' dans un dossier d'activite."""
    try:
        for p in activity_dir.iterdir():
            if p.is_file() and p.name.startswith("original."):
                return str(p.resolve())
    except Exception:
        return None
    return None


def _find_original_fit_path(activity_dir: Path) -> Path | None:
    """Trouve le premier fichier 'original.*.fit' dans un dossier d'activite."""
    try:
        for p in activity_dir.iterdir():
            if not p.is_file():
                continue
            name = p.name.lower()
            if name.startswith("original.") and name.endswith(".fit"):
                return p
    except Exception:
        return None
    return None
