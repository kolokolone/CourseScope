import math

from fastapi import APIRouter, HTTPException, Request
import numpy as np
import pandas as pd

from core.derived import compute_derived_series, compute_pace_series, compute_summary_stats
from core.pace_grade import compute_pace_vs_grade_data
from core.ref_data import get_pro_pace_vs_grade_df
from core.real_activity_bins import build_real_activity_bins as _build_real_activity_bins
from core.theoretical_segments import (
    interp_pro_pace_s_per_km as _interp_pro_pace_s_per_km,
)

from api._helpers import get_series_registry, resolve_activity_df
from api.schemas import (
    PaceVsGradeBin,
    PaceVsGradeResponse,
    ProPaceVsGradePoint,
    RealActivityBinsResponse,
    RealActivityResponse,
    TheoreticalActivityResponse,
)
from services.analysis_service import AnalysisService
from services.models import RealRunViewParams
from services.cache import InMemoryCache, make_cache_key


router = APIRouter()

real_activity_cache = InMemoryCache(max_items=256)
REAL_ACTIVITY_CACHE_VERSION = "2"


@router.get("/activity/{activity_id}/real", response_model=RealActivityResponse)
async def get_real_activity(request: Request, activity_id: str):
    """Retourne les données d'analyse pour une activité réelle"""
    try:
        # Cache lookup
        hr_max_effective = AnalysisService.resolve_hr_max_effective(request)
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
        result = AnalysisService.build_real_response(request, df, registry, activity_name=activity_name)
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
        return AnalysisService.build_theoretical_response(
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
