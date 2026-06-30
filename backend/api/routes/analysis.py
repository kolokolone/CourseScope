import math
import re

from fastapi import APIRouter, HTTPException, Request
import numpy as np
import pandas as pd

from core._shared import compute_elevation_gain, compute_elevation_loss
from core.real_run_analysis import compute_derived_series, compute_pace_series, compute_pace_vs_grade_data, compute_summary_stats
from core.ref_data import get_pro_pace_vs_grade_df
from core.grade_table import grade_factor

from api._helpers import get_series_registry, resolve_activity_df
from api.schemas import (
    ActivityLimitsDetail,
    PaceVsGradeBin,
    PaceVsGradeResponse,
    ProPaceVsGradePoint,
    RealActivityBinsResponse,
    RealActivityResponse,
    SeriesIndex,
    TheoreticalActivityResponse,
)
from registry.series_registry import SeriesRegistry
from services import real_activity_service
from services.serialization import df_to_records, to_jsonable
from services.models import RealRunParams, RealRunViewParams
from services.cache import InMemoryCache, make_cache_key
from db.settings_repository import SettingsRepository
from db.trace_repository import TraceRepository
from storage.trace_store import compute_route_fingerprint


router = APIRouter()

real_activity_cache = InMemoryCache(max_items=256)
REAL_ACTIVITY_CACHE_VERSION = "2"


def _interp_pro_pace_s_per_km(grade: float, pro_ref_rows: list[dict[str, float]]) -> float | None:
    if not pro_ref_rows:
        return None

    # Expect rows sorted by grade_percent.
    first_g = float(pro_ref_rows[0]["grade_percent"])
    last_g = float(pro_ref_rows[-1]["grade_percent"])

    if grade <= first_g:
        try:
            return float(pro_ref_rows[0]["pace_s_per_km_pro"])
        except Exception:
            return None
    if grade >= last_g:
        try:
            return float(pro_ref_rows[-1]["pace_s_per_km_pro"])
        except Exception:
            return None

    for i in range(len(pro_ref_rows) - 1):
        a = pro_ref_rows[i]
        b = pro_ref_rows[i + 1]
        ga = float(a["grade_percent"])
        gb = float(b["grade_percent"])
        if ga <= grade <= gb and gb != ga:
            pa = float(a["pace_s_per_km_pro"])
            pb = float(b["pace_s_per_km_pro"])
            t = (grade - ga) / (gb - ga)
            return pa + t * (pb - pa)
    return None


def _is_finite_number(value) -> bool:
    return isinstance(value, (int, float)) and value == value and math.isfinite(value)


def _build_cardio_summary(garmin: dict) -> dict | None:
    heart_rate = (garmin or {}).get("heart_rate")
    if not isinstance(heart_rate, dict):
        return None

    cardio: dict[str, float] = {}
    mapping = {
        "hr_avg_bpm": "mean_bpm",
        "hr_max_bpm": "max_bpm",
        "hr_min_bpm": "min_bpm",
    }
    for out_key, src_key in mapping.items():
        val = heart_rate.get(src_key)
        if _is_finite_number(val):
            cardio[out_key] = float(val)

    hr_max_used = heart_rate.get("hr_max_used")
    if _is_finite_number(hr_max_used):
        cardio["hr_max_used_bpm"] = float(hr_max_used)

    return cardio or None


def _resolve_hr_max_effective(request: Request) -> float | None:
    db_session_factory = getattr(request.app.state, "db_session_factory", None)
    if db_session_factory is None:
        return None

    session = db_session_factory()
    repo = SettingsRepository()
    try:
        row = repo.get_or_create(session)
        detected = repo.get_detected_hr_max(session)
        session.commit()
        effective = detected if row.hr_max_source == "detected" and detected is not None else row.hr_max_manual_bpm
        if effective is None:
            return None
        try:
            numeric = float(effective)
        except Exception:
            return None
        if not math.isfinite(numeric) or numeric <= 0:
            return None
        return numeric
    except Exception:
        session.rollback()
        return None
    finally:
        session.close()


def _build_limits(df):
    return ActivityLimitsDetail(
        downsampled=False,
        original_points=len(df),
        returned_points=len(df),
        note=None,
    )


def prepare_real_response(
    request: Request,
    activity_df,
    registry: SeriesRegistry,
    *,
    activity_name: str | None = None,
) -> RealActivityResponse:
    hr_max_effective = _resolve_hr_max_effective(request)
    params = RealRunParams(hr_max=hr_max_effective) if hr_max_effective is not None else None
    result = real_activity_service.analyze_real_activity(activity_df, params=params)
    series_index = SeriesIndex(available=registry.get_available_series(activity_df))

    zones = {}
    garmin = result.garmin or {}
    heart_rate = garmin.get("heart_rate")
    if heart_rate and heart_rate.get("zones") is not None:
        zones["heart_rate"] = heart_rate["zones"]
    if garmin.get("pace_zones") is not None:
        zones["pace"] = garmin["pace_zones"]
    power = garmin.get("power")
    if power and power.get("zones") is not None:
        zones["power"] = power["zones"]
    zones_payload = zones or None

    splits_rows = df_to_records(result.splits)
    splits_payload = {"rows": splits_rows} if splits_rows else None

    garmin_summary_payload = to_jsonable(garmin.get("summary")) if garmin.get("summary") else None
    cadence_payload = to_jsonable(garmin.get("cadence")) if garmin.get("cadence") else None
    power_payload = to_jsonable(garmin.get("power")) if garmin.get("power") else None
    running_dynamics_payload = (
        to_jsonable(garmin.get("running_dynamics")) if garmin.get("running_dynamics") else None
    )
    power_advanced_payload = to_jsonable(garmin.get("power_advanced")) if garmin.get("power_advanced") else None
    pacing_payload = to_jsonable(garmin.get("pacing")) if garmin.get("pacing") else None
    training_load_payload = to_jsonable(garmin.get("training_load")) if garmin.get("training_load") else None
    performance_predictions_payload = (
        {"items": to_jsonable(result.performance_predictions)}
        if result.performance_predictions
        else None
    )
    pauses_payload = {"items": to_jsonable(result.pauses)} if result.pauses else None
    climbs_payload = {"items": to_jsonable(result.climbs)} if result.climbs else None

    summary_payload = to_jsonable(result.summary) or {}
    cardio_payload = _build_cardio_summary(garmin)
    if cardio_payload is not None:
        summary_payload["cardio"] = cardio_payload

    return RealActivityResponse(
        activity_name=activity_name,
        started_at_utc=_started_at_utc_from_df(activity_df),
        summary=summary_payload,
        highlights={"items": result.highlights},
        zones=to_jsonable(zones_payload),
        best_efforts=None,
        personal_records=None,
        segment_analysis=None,
        performance_predictions=performance_predictions_payload,
        pauses=pauses_payload,
        climbs=climbs_payload,
        splits=splits_payload,
        garmin_summary=garmin_summary_payload,
        cadence=cadence_payload,
        power=power_payload,
        running_dynamics=running_dynamics_payload,
        power_advanced=power_advanced_payload,
        pacing=pacing_payload,
        training_load=training_load_payload,
        series_index=series_index,
        limits=None,
    )


def _started_at_utc_from_df(activity_df: pd.DataFrame) -> str | None:
    if "time" not in activity_df.columns:
        return None
    try:
        value = pd.to_datetime(activity_df["time"], errors="coerce").min()
    except Exception:
        return None
    if value is None or pd.isna(value):
        return None
    ts = pd.Timestamp(value)
    if ts.tzinfo is not None:
        ts = ts.tz_convert("UTC").tz_localize(None)
    return ts.to_pydatetime().replace(microsecond=0).isoformat() + "Z"


def _build_real_activity_bins(activity_df: pd.DataFrame) -> RealActivityBinsResponse:
    required = {"distance_m", "time", "elevation"}
    if not required.issubset(set(activity_df.columns)):
        return RealActivityBinsResponse(pace_elevation_series=[], pace_time_bins=[], grade_time_bins=[])

    work = activity_df.copy()
    work["distance_m"] = pd.to_numeric(work["distance_m"], errors="coerce")
    work["elevation"] = pd.to_numeric(work["elevation"], errors="coerce")
    work["time"] = pd.to_datetime(work["time"], errors="coerce")

    d1 = work["distance_m"].to_numpy(dtype=float)[1:]
    d0 = work["distance_m"].to_numpy(dtype=float)[:-1]
    delta_m = d1 - d0

    t1 = work["time"].to_numpy()[1:]
    t0 = work["time"].to_numpy()[:-1]
    delta_t_s = ((t1 - t0) / np.timedelta64(1, "s")).astype(float)

    e1 = work["elevation"].to_numpy(dtype=float)[1:]
    e0 = work["elevation"].to_numpy(dtype=float)[:-1]
    grade_pct = ((e1 - e0) / np.maximum(delta_m, 1e-9)) * 100.0

    derived = compute_derived_series(work)
    moving_mask = np.asarray(derived.moving_mask, dtype=bool)
    if moving_mask.shape[0] == work.shape[0]:
        moving_seg = moving_mask[1:]
    else:
        moving_seg = np.ones_like(delta_m, dtype=bool)

    valid = (
        np.isfinite(delta_m)
        & np.isfinite(delta_t_s)
        & np.isfinite(grade_pct)
        & np.isfinite(e1)
        & np.isfinite(d1)
        & (delta_m > 1.0)
        & (delta_t_s > 0.0)
        & (delta_t_s < 120.0)
        & moving_seg
    )

    if not np.any(valid):
        return RealActivityBinsResponse(pace_elevation_series=[], pace_time_bins=[], grade_time_bins=[])

    seg_dist_km = delta_m[valid] / 1000.0
    seg_time_s = delta_t_s[valid]
    seg_pace = np.clip(seg_time_s / np.maximum(seg_dist_km, 1e-6), 120.0, 1200.0)
    seg_grade = np.clip(grade_pct[valid], -20.0, 20.0)

    pace_table: dict[float, float] = {}
    pace_bin_width = 15.0
    pace_floor = np.floor(seg_pace / pace_bin_width) * pace_bin_width
    for floor_s, t in zip(pace_floor, seg_time_s):
        if not (math.isfinite(floor_s) and math.isfinite(t) and t > 0):
            continue
        pace_table[float(floor_s)] = pace_table.get(float(floor_s), 0.0) + float(t)
    pace_time_bins = [
        {
            "pace_bin_floor_s_per_km": floor_s,
            "label": _format_pace_bucket_label(floor_s, pace_bin_width),
            "time_s": pace_table[floor_s],
        }
        for floor_s in sorted(pace_table.keys())
    ]

    grade_table: dict[float, float] = {}
    grade_center = np.round(seg_grade * 2.0) / 2.0
    for center, t in zip(grade_center, seg_time_s):
        if not (math.isfinite(center) and math.isfinite(t) and t > 0):
            continue
        grade_table[float(center)] = grade_table.get(float(center), 0.0) + float(t)
    grade_time_bins = [
        {
            "grade_bin_center_pct": center,
            "label": f"{center:.1f}%",
            "time_s": grade_table[center],
        }
        for center in sorted(grade_table.keys())
    ]

    series = [
        {
            "distance_km": float(dist_m) / 1000.0,
            "pace_s_per_km": float(pace_s),
            "elevation_m": float(elev),
        }
        for dist_m, pace_s, elev in zip(d1[valid], seg_pace, e1[valid])
    ]

    return RealActivityBinsResponse(
        pace_elevation_series=series,
        pace_time_bins=pace_time_bins,
        grade_time_bins=grade_time_bins,
    )


_PACE_RE = re.compile(r"^\s*(\d{1,2})\s*[:h]\s*(\d{1,2})(?:\s*[:m]\s*(\d{1,2}))?\s*$")


def _parse_hms_to_seconds(value: str | None) -> float | None:
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


def _parse_pace_to_seconds_per_km(value: str | None) -> float | None:
    raw = "" if value is None else str(value).strip()
    if raw.isdigit():
        minutes = int(raw)
        if minutes > 0:
            seconds = float(minutes * 60)
        else:
            seconds = None
    else:
        seconds = _parse_hms_to_seconds(value)
    if seconds is None:
        return None
    if 120.0 <= seconds <= 600.0:
        return seconds
    return None


def _format_pace_bucket_label(start_s: float, width_s: float) -> str:
    a = int(round(start_s))
    b = int(round(start_s + width_s))
    return f"{a // 60}:{a % 60:02d}-{b // 60}:{b % 60:02d}/km"


def _interp_pro_pace_vectorized(grades: np.ndarray, pro_rows: list[dict[str, float]]) -> np.ndarray:
    if grades.size == 0:
        return np.array([], dtype=float)
    if not pro_rows:
        return np.full_like(grades, np.nan, dtype=float)
    x = np.array([float(r["grade_percent"]) for r in pro_rows], dtype=float)
    y = np.array([float(r["pace_s_per_km_pro"]) for r in pro_rows], dtype=float)
    return np.interp(grades, x, y, left=y[0], right=y[-1])


def _minetti_cost_ratio_from_grade(grade_pct: np.ndarray) -> np.ndarray:
    grade_decimal = np.asarray(grade_pct, dtype=float) / 100.0
    grade_decimal = np.clip(grade_decimal, -0.30, 0.30)

    cost = (
        155.4 * np.power(grade_decimal, 5)
        - 30.4 * np.power(grade_decimal, 4)
        - 43.3 * np.power(grade_decimal, 3)
        + 46.3 * np.power(grade_decimal, 2)
        + 19.5 * grade_decimal
        + 3.6
    )
    flat_cost = 3.6
    ratio = cost / flat_cost

    ratio = np.clip(ratio, 0.84, 2.4)
    return ratio


def _constant_effort_target_pace(
    *,
    target_pace_flat_s_per_km: float,
    vma_kmh: float,
    grade_pct: np.ndarray,
) -> np.ndarray:
    vma_safe = float(vma_kmh if math.isfinite(vma_kmh) and vma_kmh > 0 else 16.0)
    base_pace = float(target_pace_flat_s_per_km if math.isfinite(target_pace_flat_s_per_km) and target_pace_flat_s_per_km > 0 else 300.0)

    base_speed_kmh = 3600.0 / base_pace
    raw_effort_ratio = base_speed_kmh / vma_safe
    effort_ratio = min(max(raw_effort_ratio, 0.45), 0.98)
    effort_speed_kmh = vma_safe * effort_ratio

    cost_ratio = _minetti_cost_ratio_from_grade(grade_pct)
    slope_speed_kmh = effort_speed_kmh / cost_ratio
    slope_speed_kmh = np.clip(slope_speed_kmh, 3.0, 30.0)

    target_pace = 3600.0 / slope_speed_kmh
    return np.clip(target_pace, 120.0, 1200.0)


def _build_theoretical_segments(
    activity_df: pd.DataFrame,
    *,
    target_pace_flat_s_per_km: float,
    vma_kmh: float,
    grade_model: str,
) -> pd.DataFrame:
    required = {"distance_m", "elevation"}
    if not required.issubset(set(activity_df.columns)):
        return pd.DataFrame(
            columns=[
                "distance_km",
                "target_pace_s_per_km",
                "elevation_m",
                "segment_time_s",
                "segment_grade_percent",
                "segment_distance_km",
                "cumulative_time_s",
            ]
        )

    distance = pd.to_numeric(activity_df["distance_m"], errors="coerce").to_numpy(dtype=float)
    elevation = pd.to_numeric(activity_df["elevation"], errors="coerce").to_numpy(dtype=float)
    if distance.size < 2:
        return pd.DataFrame(
            columns=[
                "distance_km",
                "target_pace_s_per_km",
                "elevation_m",
                "segment_time_s",
                "segment_grade_percent",
                "segment_distance_km",
                "cumulative_time_s",
            ]
        )

    d0 = distance[:-1]
    d1 = distance[1:]
    dist_delta_m = d1 - d0
    valid = np.isfinite(d0) & np.isfinite(d1) & (dist_delta_m > 0)
    if not valid.any():
        return pd.DataFrame(
            columns=[
                "distance_km",
                "target_pace_s_per_km",
                "elevation_m",
                "segment_time_s",
                "segment_grade_percent",
                "segment_distance_km",
                "cumulative_time_s",
            ]
        )

    seg_distance_m = dist_delta_m[valid]
    seg_distance_km = seg_distance_m / 1000.0

    e0 = elevation[:-1][valid]
    e1 = elevation[1:][valid]
    elev_delta = np.where(np.isfinite(e0) & np.isfinite(e1), e1 - e0, 0.0)
    grade_pct = (elev_delta / seg_distance_m) * 100.0

    if grade_model == "pro_ref":
        target_pace = _constant_effort_target_pace(
            target_pace_flat_s_per_km=target_pace_flat_s_per_km,
            vma_kmh=vma_kmh,
            grade_pct=grade_pct,
        )
    else:
        grade_factor_arr = grade_factor(grade_pct)
        target_pace = np.asarray(target_pace_flat_s_per_km * grade_factor_arr, dtype=float)
        target_pace = np.clip(target_pace, 120.0, 1200.0)
    segment_time_s = target_pace * seg_distance_km
    cumulative_time_s = np.cumsum(segment_time_s)

    return pd.DataFrame(
        {
            "distance_km": d1[valid] / 1000.0,
            "target_pace_s_per_km": target_pace,
            "elevation_m": e1,
            "segment_time_s": segment_time_s,
            "segment_grade_percent": grade_pct,
            "segment_distance_km": seg_distance_km,
            "cumulative_time_s": cumulative_time_s,
        }
    )


def _build_grade_time_bins(df_segments: pd.DataFrame) -> list[dict[str, float | str]]:
    if df_segments.empty:
        return []
    grades = df_segments["segment_grade_percent"].to_numpy(dtype=float)
    time_s = df_segments["segment_time_s"].to_numpy(dtype=float)
    grades = np.clip(grades, -20.0, 20.0)
    centers = np.round(grades * 2.0) / 2.0
    table: dict[float, float] = {}
    for center, t in zip(centers, time_s):
        if not (math.isfinite(center) and math.isfinite(t) and t > 0):
            continue
        table[float(center)] = table.get(float(center), 0.0) + float(t)
    out = []
    for center in sorted(table.keys()):
        out.append(
            {
                "grade_bin_center_pct": center,
                "label": f"{center:.1f}%",
                "time_s": table[center],
            }
        )
    return out


def _build_pace_time_bins(df_segments: pd.DataFrame) -> list[dict[str, float | str]]:
    if df_segments.empty:
        return []
    pace = df_segments["target_pace_s_per_km"].to_numpy(dtype=float)
    time_s = df_segments["segment_time_s"].to_numpy(dtype=float)
    bin_width_s = 15.0
    floors = np.floor(pace / bin_width_s) * bin_width_s
    table: dict[float, float] = {}
    for floor_s, t in zip(floors, time_s):
        if not (math.isfinite(floor_s) and math.isfinite(t) and t > 0):
            continue
        table[float(floor_s)] = table.get(float(floor_s), 0.0) + float(t)
    out = []
    for floor_s in sorted(table.keys()):
        out.append(
            {
                "pace_bin_floor_s_per_km": floor_s,
                "label": _format_pace_bucket_label(floor_s, bin_width_s),
                "time_s": table[floor_s],
            }
        )
    return out


def _compute_secondary_metrics(df_segments: pd.DataFrame) -> dict:
    if df_segments.empty:
        return {}

    grades = df_segments["segment_grade_percent"].to_numpy(dtype=float)
    dist = df_segments["segment_distance_km"].to_numpy(dtype=float)
    time_s = df_segments["segment_time_s"].to_numpy(dtype=float)
    elev = pd.to_numeric(df_segments["elevation_m"], errors="coerce").to_numpy(dtype=float)

    total_dist = float(np.nansum(dist)) if dist.size else 0.0
    weighted_grade = float(np.nansum(grades * dist) / total_dist) if total_dist > 0 else math.nan

    finite_grades = grades[np.isfinite(grades)]
    robust_min = float(np.quantile(finite_grades, 0.01)) if finite_grades.size else math.nan
    robust_max = float(np.quantile(finite_grades, 0.99)) if finite_grades.size else math.nan

    bins = {
        "climb": grades > 0.5,
        "flat": (grades >= -0.5) & (grades <= 0.5),
        "descent": grades < -0.5,
    }

    terrain = {}
    for key, mask in bins.items():
        d = float(np.nansum(dist[mask]))
        t = float(np.nansum(time_s[mask]))
        pace = (t / d) if d > 0 else math.nan
        terrain[key] = {
            "distance_km": d,
            "time_s": t,
            "avg_pace_s_per_km": pace,
        }

    grade_bins = _build_grade_time_bins(df_segments)
    top3 = sorted(grade_bins, key=lambda r: float(r["time_s"]), reverse=True)[:3]

    return {
        "weighted_avg_grade_pct": weighted_grade,
        "robust_grade_min_pct": robust_min,
        "robust_grade_max_pct": robust_max,
        "terrain_breakdown": terrain,
        "time_by_grade_top3": top3,
        "elevation_min_m": float(np.nanmin(elev)) if elev.size else None,
        "elevation_max_m": float(np.nanmax(elev)) if elev.size else None,
    }


def _resolve_vma_kmh(request: Request, vma_kmh: float | None) -> float:
    if isinstance(vma_kmh, (int, float)) and math.isfinite(float(vma_kmh)) and float(vma_kmh) > 0:
        return float(vma_kmh)

    db_session_factory = getattr(request.app.state, "db_session_factory", None)
    if db_session_factory is None:
        return 16.0

    session = db_session_factory()
    repo = SettingsRepository()
    try:
        row = repo.get_or_create(session)
        session.commit()
        if row.vma_kmh is not None and math.isfinite(float(row.vma_kmh)) and float(row.vma_kmh) > 0:
            return float(row.vma_kmh)
    except Exception:
        session.rollback()
    finally:
        session.close()
    return 16.0


def _resolve_target_pace_and_time(
    *,
    activity_df: pd.DataFrame,
    target_mode: str,
    target_pace: str | None,
    target_time: str | None,
) -> tuple[str, float, float]:
    distance_m = pd.to_numeric(activity_df.get("distance_m"), errors="coerce") if "distance_m" in activity_df.columns else pd.Series(dtype=float)
    distance_clean = distance_m.dropna()
    total_distance_km = float(distance_clean.iloc[-1] / 1000.0) if not distance_clean.empty else 0.0
    total_distance_km = total_distance_km if total_distance_km > 0 else 1.0

    mode = "time" if str(target_mode).lower() == "time" else "pace"
    pace_s = _parse_pace_to_seconds_per_km(target_pace)
    time_s = _parse_hms_to_seconds(target_time)

    if mode == "time" and time_s is not None and time_s > 0:
        pace_s = max(120.0, min(1200.0, float(time_s / total_distance_km)))
    elif mode == "pace" and pace_s is not None and pace_s > 0:
        time_s = float(pace_s * total_distance_km)

    if pace_s is None or not math.isfinite(pace_s) or pace_s <= 0:
        pace_s = 300.0
        time_s = float(pace_s * total_distance_km)
        mode = "pace"

    if time_s is None or not math.isfinite(time_s) or time_s <= 0:
        time_s = float(pace_s * total_distance_km)

    return mode, float(pace_s), float(time_s)


def _resolve_trace_status(request: Request, activity_df: pd.DataFrame) -> dict:
    db_session_factory = getattr(request.app.state, "db_session_factory", None)
    if db_session_factory is None:
        return {"saved": False}

    fingerprint = compute_route_fingerprint(activity_df)
    if not fingerprint:
        return {"saved": False}

    session = db_session_factory()
    repo = TraceRepository()
    try:
        row = repo.get_by_route_fingerprint(session, fingerprint)
        if row is None:
            return {"saved": False}
        return {"saved": True, "trace_id": row.id, "trace_name": row.name}
    finally:
        session.close()


def prepare_theoretical_response(
    request: Request,
    activity_df: pd.DataFrame,
    registry: SeriesRegistry,
    *,
    target_mode: str,
    target_pace: str | None,
    target_time: str | None,
    vma_kmh: float | None,
    grade_model: str,
) -> TheoreticalActivityResponse:
    resolved_mode, target_pace_s, target_time_s = _resolve_target_pace_and_time(
        activity_df=activity_df,
        target_mode=target_mode,
        target_pace=target_pace,
        target_time=target_time,
    )
    effective_vma = _resolve_vma_kmh(request, vma_kmh)

    df_segments = _build_theoretical_segments(
        activity_df,
        target_pace_flat_s_per_km=target_pace_s,
        vma_kmh=effective_vma,
        grade_model=grade_model,
    )

    distance_km = float(df_segments["distance_km"].iloc[-1]) if not df_segments.empty else 0.0
    estimated_time_s = float(df_segments["cumulative_time_s"].iloc[-1]) if not df_segments.empty else 0.0
    average_pace_s_per_km = (estimated_time_s / distance_km) if distance_km > 0 else target_pace_s

    elevation = pd.to_numeric(df_segments["elevation_m"], errors="coerce").dropna().to_numpy(dtype=float)
    elev_gain = compute_elevation_gain(elevation)
    elev_loss = compute_elevation_loss(elevation)

    summary = {
        "distance_km": distance_km,
        "elevation_gain_m": elev_gain,
        "elevation_loss_m": elev_loss,
        "d_plus_per_km": (elev_gain / distance_km) if distance_km > 0 else None,
        "target_pace_s_per_km": target_pace_s,
        "estimated_time_s": estimated_time_s,
        # Backward-compatible keys used by existing UI blocks.
        "total_time_s": estimated_time_s,
        "total_distance_km": distance_km,
        "average_pace_s_per_km": average_pace_s_per_km,
    }
    if elevation.size > 0:
        summary["elevation_min_m"] = float(np.min(elevation))
        summary["elevation_max_m"] = float(np.max(elevation))

    pace_series = [
        {
            "distance_km": float(row.distance_km),
            "target_pace_s_per_km": float(row.target_pace_s_per_km),
            "elevation_m": float(row.elevation_m) if row.elevation_m == row.elevation_m else None,
        }
        for row in df_segments.itertuples(index=False)
    ]

    series_index = SeriesIndex(available=registry.get_available_series(activity_df))
    trace_status = _resolve_trace_status(request, activity_df)

    return TheoreticalActivityResponse(
        summary=to_jsonable(summary),
        highlights={"items": []},
        zones=None,
        best_efforts=None,
        personal_records=None,
        segment_analysis=None,
        performance_predictions=None,
        pauses=None,
        climbs=None,
        splits=None,
        garmin_summary=None,
        cadence=None,
        power=None,
        running_dynamics=None,
        power_advanced=None,
        pacing=None,
        training_load=None,
        series_index=series_index,
        limits=_build_limits(activity_df),
        target_mode=resolved_mode,
        target_pace_s_per_km=target_pace_s,
        target_time_s=target_time_s,
        vma_kmh=effective_vma,
        pace_elevation_series=pace_series,
        grade_time_bins=_build_grade_time_bins(df_segments),
        pace_time_bins=_build_pace_time_bins(df_segments),
        secondary_metrics=_compute_secondary_metrics(df_segments),
        trace_status=trace_status,
    )


@router.get("/activity/{activity_id}/real", response_model=RealActivityResponse)
async def get_real_activity(request: Request, activity_id: str):
    """Retourne les données d'analyse pour une activité réelle"""
    try:
        # Cache lookup
        hr_max_effective = _resolve_hr_max_effective(request)
        cache_key = make_cache_key(
            namespace="real_activity",
            version=REAL_ACTIVITY_CACHE_VERSION,
            payload={"activity_id": activity_id, "hr_max": hr_max_effective},
        )
        cached = real_activity_cache.get(cache_key)
        if cached is not None:
            return cached

        df = resolve_activity_df(request, activity_id)
        activity_name: str | None = None
        try:
            loaded_name = request.app.state.storage.load(activity_id).name
        except Exception:
            temp_storage = getattr(request.app.state, "temp_storage", None)
            if temp_storage is not None:
                try:
                    loaded_name = temp_storage.load(activity_id).name
                except Exception:
                    loaded_name = None
            else:
                loaded_name = None
        if isinstance(loaded_name, str) and loaded_name.strip():
            activity_name = loaded_name.strip()

        registry = get_series_registry(request)
        result = prepare_real_response(request, df, registry, activity_name=activity_name)
        real_activity_cache.set(cache_key, result, ttl_s=60)
        return result

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Activity {activity_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get real activity: {str(e)}")


@router.get("/activity/{activity_id}/theoretical", response_model=TheoreticalActivityResponse)
async def get_theoretical_activity(
    request: Request,
    activity_id: str,
    target_mode: str = "pace",
    target_pace: str | None = None,
    target_time: str | None = None,
    vma_kmh: float | None = None,
    grade_model: str = "grade_table_v1",
):
    """Retourne les données d'analyse pour une activité théorique"""
    try:
        df = resolve_activity_df(request, activity_id)

        registry = get_series_registry(request)
        return prepare_theoretical_response(
            request,
            df,
            registry,
            target_mode=target_mode,
            target_pace=target_pace,
            target_time=target_time,
            vma_kmh=vma_kmh,
            grade_model=grade_model,
        )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Activity {activity_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get theoretical activity: {str(e)}")


@router.get("/activity/{activity_id}/pace-vs-grade", response_model=PaceVsGradeResponse)
async def get_pace_vs_grade(
    request: Request,
    activity_id: str,
):
    """Returns binned pace vs grade data (backend-computed)."""

    try:
        df = resolve_activity_df(request, activity_id)

        # Keep this endpoint consistent with the "real activity figures" defaults.
        derived = compute_derived_series(df)
        summary = compute_summary_stats(df, moving_mask=derived.moving_mask)
        avg = summary.get("average_pace_s_per_km")
        if isinstance(avg, (int, float)) and avg == avg and avg > 0:
            cap_min_per_km = float((avg / 60.0) * 1.4)
        else:
            cap_min_per_km = 8.0
        view = RealRunViewParams()
        pace_series = compute_pace_series(
            df,
            moving_mask=derived.moving_mask,
            pace_mode=view.pace_mode,
            smoothing_points=view.smoothing_points,
            cap_min_per_km=cap_min_per_km,
        )

        data = compute_pace_vs_grade_data(
            df,
            pace_series=pace_series,
            grade_series=derived.grade_series,
            moving_mask=derived.moving_mask,
        )
        bins: list[PaceVsGradeBin] = []
        if data is not None and not data.empty:
            # pace_* values are in s/km.
            pro_df = get_pro_pace_vs_grade_df()
            pro_rows: list[dict[str, float]] = []
            if pro_df is not None and not pro_df.empty:
                expected_cols = {"grade_percent", "pace_s_per_km_pro"}
                if expected_cols.issubset(set(pro_df.columns)):
                    pro_df_sorted = pro_df.sort_values("grade_percent")
                    for _, row in pro_df_sorted.iterrows():
                        g = float(row["grade_percent"])
                        p = float(row["pace_s_per_km_pro"])
                        if not (math.isfinite(g) and math.isfinite(p)):
                            continue
                        pro_rows.append({"grade_percent": g, "pace_s_per_km_pro": p})

            for _, row in data.iterrows():
                grade_center = float(row["grade_center"])
                pace_med_s = float(row["pace_med_s_per_km"])
                pace_std_s = float(row["pace_std_s_per_km"])
                pace_n = int(row.get("pace_n", 0) or 0)

                time_s_bin = row.get("time_s_bin")
                pace_mean_w_s = row.get("pace_mean_w_s_per_km")
                pace_q25_w_s = row.get("pace_q25_w_s_per_km")
                pace_q50_w_s = row.get("pace_q50_w_s_per_km")
                pace_q75_w_s = row.get("pace_q75_w_s_per_km")
                pace_iqr_w_s = row.get("pace_iqr_w_s_per_km")
                pace_std_w_s = row.get("pace_std_w_s_per_km")
                pace_n_eff = row.get("pace_n_eff")
                outlier_clip_frac = row.get("outlier_clip_frac")

                pro_pace = _interp_pro_pace_s_per_km(grade_center, pro_rows)

                bins.append(
                    PaceVsGradeBin(
                        grade_center=grade_center,
                        pace_med_s_per_km=pace_med_s,
                        pace_std_s_per_km=pace_std_s,
                        pace_n=pace_n,
                        pro_pace_s_per_km=pro_pace,
                        time_s_bin=float(time_s_bin) if time_s_bin == time_s_bin else None,
                        pace_mean_w_s_per_km=float(pace_mean_w_s) if pace_mean_w_s == pace_mean_w_s else None,
                        pace_q25_w_s_per_km=float(pace_q25_w_s) if pace_q25_w_s == pace_q25_w_s else None,
                        pace_q50_w_s_per_km=float(pace_q50_w_s) if pace_q50_w_s == pace_q50_w_s else None,
                        pace_q75_w_s_per_km=float(pace_q75_w_s) if pace_q75_w_s == pace_q75_w_s else None,
                        pace_iqr_w_s_per_km=float(pace_iqr_w_s) if pace_iqr_w_s == pace_iqr_w_s else None,
                        pace_std_w_s_per_km=float(pace_std_w_s) if pace_std_w_s == pace_std_w_s else None,
                        pace_n_eff=float(pace_n_eff) if pace_n_eff == pace_n_eff else None,
                        outlier_clip_frac=float(outlier_clip_frac) if outlier_clip_frac == outlier_clip_frac else None,
                    )
                )

        # Always return pro_ref list (may be empty) for drawing the dashed curve.
        pro_ref_points: list[ProPaceVsGradePoint] = []
        pro_df = get_pro_pace_vs_grade_df()
        if pro_df is not None and not pro_df.empty:
            expected_cols = {"grade_percent", "pace_s_per_km_pro"}
            if expected_cols.issubset(set(pro_df.columns)):
                pro_df_sorted = pro_df.sort_values("grade_percent")
                for _, row in pro_df_sorted.iterrows():
                    g = float(row["grade_percent"])
                    p = float(row["pace_s_per_km_pro"])
                    if not (math.isfinite(g) and math.isfinite(p)):
                        continue
                    pro_ref_points.append(ProPaceVsGradePoint(grade_percent=g, pace_s_per_km_pro=p))

        return PaceVsGradeResponse(bins=bins, pro_ref=pro_ref_points)

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Activity {activity_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute pace-vs-grade: {str(e)}")


@router.get("/activity/{activity_id}/real-bins", response_model=RealActivityBinsResponse)
async def get_real_activity_bins(request: Request, activity_id: str):
    try:
        df = resolve_activity_df(request, activity_id)

        return _build_real_activity_bins(df)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Activity {activity_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute real activity bins: {str(e)}")
