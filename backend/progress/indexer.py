from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from core.metrics import compute_garmin_like_stats
from core.real_run_analysis import compute_best_efforts_by_duration, compute_derived_series
from core.stats.basic_stats import compute_basic_stats
from db.models import ProgressActivityIndex, ProgressActivityTag, ProgressBestEffortPoint, ProgressPaceHrBin, UserSettings
from db.progress_repository import ProgressRepository
from db.models import utc_now_iso


METRICS_VERSION = 4


def _parse_iso_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _format_ts_utc(dt: datetime) -> str:
    dt = _to_utc(dt).replace(microsecond=0)
    return dt.isoformat().replace("+00:00", "Z")


def _infer_started_at_utc_from_df(df: pd.DataFrame) -> str | None:
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


def build_fingerprint(meta: dict[str, Any], parquet_path: Path) -> str:
    file_hash = str(meta.get("file_hash") or "")
    try:
        stat = parquet_path.stat()
        size = int(stat.st_size)
        mtime_ns = int(stat.st_mtime_ns)
    except Exception:
        size = 0
        mtime_ns = 0

    raw = f"{file_hash}:{size}:{mtime_ns}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _finite_or_none(value: object) -> float | None:
    if not isinstance(value, (int, float)):
        return None
    v = float(value)
    if not math.isfinite(v):
        return None
    return v


def _extract_vo2max(df: pd.DataFrame) -> float | None:
    if "vo2max" not in df.columns:
        return None
    values = pd.to_numeric(df["vo2max"], errors="coerce").dropna()
    if values.empty:
        return None
    value = float(values.iloc[-1])
    if not math.isfinite(value):
        return None
    if value < 10.0 or value > 95.0:
        return None
    return value


def _weighted_median(values: list[float], weights: list[float]) -> float | None:
    if len(values) != len(weights) or not values:
        return None
    pairs = sorted(zip(values, weights), key=lambda x: x[0])
    total = float(sum(w for _, w in pairs if math.isfinite(w) and w > 0))
    if total <= 0 or not math.isfinite(total):
        return None
    cutoff = total * 0.5
    acc = 0.0
    for value, weight in pairs:
        if not (math.isfinite(value) and math.isfinite(weight) and weight > 0):
            continue
        acc += float(weight)
        if acc >= cutoff:
            return float(value)
    return float(pairs[-1][0]) if pairs else None


def _classify_session_and_terrain(
    *,
    activity_type: str,
    distance_m: float | None,
    moving_time_s: float | None,
    elevation_gain_m: float | None,
    avg_pace_s_per_km: float | None,
    best_pace_s_per_km: float | None,
    pace_threshold_s_per_km: float | None,
    stability_cv: float | None,
    decoupling_pct: float | None,
) -> tuple[str, str]:
    if activity_type != "real":
        return "unknown", "unknown"

    terrain_tag = "unknown"
    if distance_m is not None and distance_m > 0 and elevation_gain_m is not None and elevation_gain_m >= 0:
        gain_per_km = elevation_gain_m / (distance_m / 1000.0)
        if math.isfinite(gain_per_km):
            if gain_per_km < 20:
                terrain_tag = "flat"
            elif gain_per_km < 60:
                terrain_tag = "rolling"
            else:
                terrain_tag = "hilly"

    session_tag = "easy"
    is_long = bool((distance_m is not None and distance_m >= 18000) or (moving_time_s is not None and moving_time_s >= 5400))
    if is_long:
        session_tag = "long_run"
    else:
        pace_ratio = None
        if avg_pace_s_per_km is not None and avg_pace_s_per_km > 0 and best_pace_s_per_km is not None and best_pace_s_per_km > 0:
            pace_ratio = best_pace_s_per_km / avg_pace_s_per_km

        threshold_ratio = None
        if avg_pace_s_per_km is not None and avg_pace_s_per_km > 0 and pace_threshold_s_per_km is not None and pace_threshold_s_per_km > 0:
            threshold_ratio = avg_pace_s_per_km / pace_threshold_s_per_km

        is_interval = bool(
            (stability_cv is not None and stability_cv >= 0.16)
            or (pace_ratio is not None and pace_ratio <= 0.82)
        )

        is_tempo = bool(
            (threshold_ratio is not None and 0.92 <= threshold_ratio <= 1.12)
            and (stability_cv is None or stability_cv <= 0.11)
            and (decoupling_pct is None or abs(decoupling_pct) <= 8.0)
            and (moving_time_s is None or moving_time_s >= 1200)
        )

        if is_interval:
            session_tag = "interval"
        elif is_tempo:
            session_tag = "tempo"

    return session_tag, terrain_tag


def _build_pace_hr_bins(
    *,
    df: pd.DataFrame,
    activity_id: str,
    activity_type: str,
    start_ts_utc: str,
    pace_bin_step_s_per_km: float = 10.0,
    min_time_s_bin: float = 60.0,
) -> list[ProgressPaceHrBin]:
    required = {"pace_s_per_km", "heart_rate", "delta_time_s", "speed_m_s"}
    if not required.issubset(set(df.columns)):
        return []

    dt_num = pd.to_numeric(df.loc[:, "delta_time_s"], errors="coerce")
    pace_num = pd.to_numeric(df.loc[:, "pace_s_per_km"], errors="coerce")
    hr_num = pd.to_numeric(df.loc[:, "heart_rate"], errors="coerce")
    speed_num = pd.to_numeric(df.loc[:, "speed_m_s"], errors="coerce")

    dt = pd.Series(dt_num, index=df.index).fillna(0.0).astype(float)
    pace = pd.Series(pace_num, index=df.index).astype(float)
    hr = pd.Series(hr_num, index=df.index).astype(float)
    speed = pd.Series(speed_num, index=df.index).fillna(0.0).astype(float)

    moving_mask: pd.Series = (
        (speed > 0.5)
        & (dt > 0)
        & pace.notna()
        & hr.notna()
        & (pace > 0)
        & (pace < 1800)
        & (hr > 40)
        & (hr < 240)
    )
    if not bool(moving_mask.any()):
        return []

    work = pd.DataFrame(
        {
            "pace": pace[moving_mask],
            "hr": hr[moving_mask],
            "dt": dt[moving_mask],
        }
    )
    if work.empty:
        return []

    step = float(pace_bin_step_s_per_km)
    work["pace_bin"] = (work["pace"] / step).round() * step

    rows: list[ProgressPaceHrBin] = []
    for pace_bin, g in work.groupby("pace_bin", sort=True):
        values = g["hr"].astype(float).tolist()
        weights = g["dt"].astype(float).tolist()
        time_s_bin = float(sum(w for w in weights if math.isfinite(w) and w > 0))
        if not math.isfinite(time_s_bin) or time_s_bin < float(min_time_s_bin):
            continue
        weighted_sum = 0.0
        for v, w in zip(values, weights):
            if not (math.isfinite(v) and math.isfinite(w) and w > 0):
                continue
            weighted_sum += float(v) * float(w)
        hr_mean_w_bpm_raw = (weighted_sum / time_s_bin) if time_s_bin > 0 else None
        hr_q50_w_bpm_raw = _weighted_median(values, weights)
        hr_mean_w_bpm: float | None = None
        if hr_mean_w_bpm_raw is not None:
            v = float(hr_mean_w_bpm_raw)
            if math.isfinite(v):
                hr_mean_w_bpm = v
        hr_q50_w_bpm: float | None = None
        if hr_q50_w_bpm_raw is not None:
            v = float(hr_q50_w_bpm_raw)
            if math.isfinite(v):
                hr_q50_w_bpm = v

        pace_bin_num = pd.to_numeric(g["pace_bin"], errors="coerce")
        pace_bin_arr = pd.Series(pace_bin_num).to_numpy(dtype=float)
        if pace_bin_arr.size == 0:
            continue
        pace_bin_value = float(pace_bin_arr[0])

        rows.append(
            ProgressPaceHrBin(
                activity_id=activity_id,
                activity_type=activity_type,
                start_ts_utc=start_ts_utc,
                pace_bin_s_per_km=pace_bin_value,
                time_s_bin=float(time_s_bin),
                hr_mean_w_bpm=hr_mean_w_bpm,
                hr_q50_w_bpm=hr_q50_w_bpm,
            )
        )
    return rows


def index_activity(
    session: Session,
    *,
    activity_id: str,
    df: pd.DataFrame,
    meta: dict[str, Any],
    parquet_path: Path,
) -> None:
    if df is None or df.empty:
        return

    started_at = meta.get("started_at")
    started_dt = _parse_iso_datetime(started_at)
    start_ts_utc = _format_ts_utc(started_dt) if started_dt is not None else None
    if start_ts_utc is None:
        start_ts_utc = _infer_started_at_utc_from_df(df)
    if start_ts_utc is None:
        # Fallback to created_at if everything else fails.
        created_dt = _parse_iso_datetime(meta.get("created_at"))
        if created_dt is not None:
            start_ts_utc = _format_ts_utc(created_dt)
    if start_ts_utc is None:
        # If we can't place the activity on a timeline, skip it.
        return

    local_date = start_ts_utc[:10] if len(start_ts_utc) >= 10 else None
    activity_type = str(meta.get("activity_type") or "real")

    derived = compute_derived_series(df)

    basic = compute_basic_stats(df, moving_mask=derived.moving_mask)
    distance_m = float(basic.distance_m) if basic.distance_m is not None else None
    moving_time_s = float(basic.moving_time_s) if basic.moving_time_s is not None else None
    total_time_s = float(basic.total_time_s) if basic.total_time_s is not None else None
    elevation_gain_m = float(basic.elevation_gain_m) if basic.elevation_gain_m is not None else None

    garmin = compute_garmin_like_stats(
        df,
        moving_mask=derived.moving_mask,
        gap_series=derived.gap_series,
        grade_series=derived.grade_series,
    )
    summary = garmin.get("summary") if isinstance(garmin, dict) else None
    summary = summary if isinstance(summary, dict) else {}
    pacing = garmin.get("pacing") if isinstance(garmin, dict) else None
    pacing = pacing if isinstance(pacing, dict) else {}
    hr = garmin.get("heart_rate") if isinstance(garmin, dict) else None
    hr = hr if isinstance(hr, dict) else {}
    training_load = garmin.get("training_load") if isinstance(garmin, dict) else None
    training_load = training_load if isinstance(training_load, dict) else {}

    avg_pace_s_per_km = _finite_or_none(summary.get("average_pace_s_per_km"))
    best_pace_s_per_km = _finite_or_none(summary.get("best_pace_s_per_km"))
    pace_threshold_s_per_km = _finite_or_none(pacing.get("pace_threshold_s_per_km"))

    avg_hr_bpm = _finite_or_none(hr.get("mean_bpm"))
    max_hr_bpm = _finite_or_none(hr.get("max_bpm"))

    trimp = _finite_or_none(training_load.get("trimp"))
    training_load_method = training_load.get("method")
    training_load_method = str(training_load_method) if isinstance(training_load_method, str) and training_load_method else None

    cardiac_drift_pct = _finite_or_none(pacing.get("cardiac_drift_pct"))
    stability_cv = _finite_or_none(pacing.get("stability_cv"))
    stability_iqr_ratio = _finite_or_none(pacing.get("stability_iqr_ratio"))

    # decoupling_pct is the UI-facing alias for cardiac drift.
    decoupling_pct = cardiac_drift_pct

    aerobic_efficiency = None
    if (
        distance_m is not None
        and moving_time_s is not None
        and avg_hr_bpm is not None
        and moving_time_s > 0
        and avg_hr_bpm > 0
    ):
        speed_m_s = distance_m / moving_time_s
        if math.isfinite(speed_m_s) and speed_m_s > 0:
            aerobic_efficiency = speed_m_s / avg_hr_bpm

    has_hr = 1 if ("heart_rate" in df.columns and bool(df["heart_rate"].notna().any())) else 0
    has_power = 1 if ("power" in df.columns and bool(df["power"].notna().any())) else 0
    has_cadence = 1 if ("cadence" in df.columns and bool(df["cadence"].notna().any())) else 0
    data_points = int(len(df))
    vo2max = _extract_vo2max(df)

    fingerprint = build_fingerprint(meta, parquet_path)
    indexed_at_ts = utc_now_iso()

    repo = ProgressRepository()
    row = ProgressActivityIndex(
        activity_id=activity_id,
        activity_type=activity_type,
        start_ts_utc=start_ts_utc,
        local_date=local_date,
        tz=None,
        fingerprint=fingerprint,
        metrics_version=int(METRICS_VERSION),
        indexed_at_ts=indexed_at_ts,
        distance_m=distance_m,
        moving_time_s=moving_time_s,
        elapsed_time_s=total_time_s,
        elevation_gain_m=elevation_gain_m,
        avg_pace_s_per_km=avg_pace_s_per_km,
        best_pace_s_per_km=best_pace_s_per_km,
        pace_threshold_s_per_km=pace_threshold_s_per_km,
        avg_hr_bpm=avg_hr_bpm,
        max_hr_bpm=max_hr_bpm,
        trimp=trimp,
        training_load_method=training_load_method,
        decoupling_pct=decoupling_pct,
        cardiac_drift_pct=cardiac_drift_pct,
        stability_cv=stability_cv,
        stability_iqr_ratio=stability_iqr_ratio,
        aerobic_efficiency_m_s_per_bpm=aerobic_efficiency,
        vo2max=vo2max,
        has_hr=has_hr,
        has_power=has_power,
        has_cadence=has_cadence,
        data_points=data_points,
    )
    repo.upsert_activity_index(session, row)

    if vo2max is not None:
        settings = session.get(UserSettings, 1)
        if settings is None:
            settings = UserSettings(
                id=1,
                vma_kmh=None,
                vo2max_lastest=vo2max,
                hr_max_manual_bpm=None,
                hr_max_source="detected",
                updated_at_utc=indexed_at_ts,
            )
            session.add(settings)
        else:
            settings.vo2max_lastest = vo2max
            settings.updated_at_utc = indexed_at_ts

    session_tag, terrain_tag = _classify_session_and_terrain(
        activity_type=activity_type,
        distance_m=distance_m,
        moving_time_s=moving_time_s,
        elevation_gain_m=elevation_gain_m,
        avg_pace_s_per_km=avg_pace_s_per_km,
        best_pace_s_per_km=best_pace_s_per_km,
        pace_threshold_s_per_km=pace_threshold_s_per_km,
        stability_cv=stability_cv,
        decoupling_pct=decoupling_pct,
    )
    repo.upsert_activity_tag(
        session,
        row=ProgressActivityTag(
            activity_id=activity_id,
            session_tag=session_tag,
            terrain_tag=terrain_tag,
            race_marker=0,
            source="auto",
            updated_at_ts=indexed_at_ts,
        ),
        preserve_manual=True,
    )

    # Best-efforts timeline (pace) for standard durations.
    durations_s = [60, 180, 300, 720, 1200, 1800, 3600]
    best_time = compute_best_efforts_by_duration(df, durations_s=durations_s)
    points: list[ProgressBestEffortPoint] = []
    if best_time is not None and not best_time.empty:
        for _, r in best_time.iterrows():
            dur = int(r.get("duration_s") or 0)
            pace = _finite_or_none(r.get("pace_s_per_km"))
            if dur <= 0 or pace is None:
                continue
            points.append(
                ProgressBestEffortPoint(
                    activity_id=activity_id,
                    start_ts_utc=start_ts_utc,
                    effort_kind="pace_s_per_km",
                    duration_s=dur,
                    value=float(pace),
                )
            )
    repo.replace_best_efforts(session, activity_id=activity_id, effort_kind="pace_s_per_km", points=points)

    pace_hr_bins = _build_pace_hr_bins(
        df=df,
        activity_id=activity_id,
        activity_type=activity_type,
        start_ts_utc=start_ts_utc,
    )
    repo.replace_pace_hr_bins(session, activity_id=activity_id, bins=pace_hr_bins)
