import math

from fastapi import APIRouter, HTTPException, Request

from core.real_run_analysis import compute_derived_series, compute_pace_series, compute_pace_vs_grade_data, compute_summary_stats
from core.ref_data import get_pro_pace_vs_grade_df

from api.schemas import (
    ActivityLimitsDetail,
    PaceVsGradeBin,
    PaceVsGradeResponse,
    ProPaceVsGradePoint,
    RealActivityResponse,
    SeriesIndex,
    TheoreticalActivityResponse,
)
from registry.series_registry import SeriesRegistry
from services import real_activity_service, theoretical_service
from services.serialization import df_to_records, to_jsonable
from services.models import RealRunViewParams


router = APIRouter()


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

    return cardio or None


def get_series_registry(request: Request) -> SeriesRegistry:
    return request.app.state.registry


def _build_limits(df):
    return ActivityLimitsDetail(
        downsampled=False,
        original_points=len(df),
        returned_points=len(df),
        note=None,
    )


def prepare_real_response(activity_df, registry: SeriesRegistry) -> RealActivityResponse:
    result = real_activity_service.analyze_real_activity(activity_df)
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

    best_efforts_rows = df_to_records(result.best_efforts)
    best_efforts_payload = {"rows": best_efforts_rows} if best_efforts_rows else None

    splits_rows = df_to_records(result.splits)
    splits_payload = {"rows": splits_rows} if splits_rows else None

    segments_rows = df_to_records(result.best_efforts_time)
    segment_analysis_payload = {"rows": segments_rows} if segments_rows else None

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
    personal_records_payload = {"rows": best_efforts_rows} if best_efforts_rows else None

    pauses_payload = {"items": to_jsonable(result.pauses)} if result.pauses else None
    climbs_payload = {"items": to_jsonable(result.climbs)} if result.climbs else None

    summary_payload = to_jsonable(result.summary) or {}
    cardio_payload = _build_cardio_summary(garmin)
    if cardio_payload is not None:
        summary_payload["cardio"] = cardio_payload

    return RealActivityResponse(
        summary=summary_payload,
        highlights={"items": result.highlights},
        zones=to_jsonable(zones_payload),
        best_efforts=best_efforts_payload,
        personal_records=personal_records_payload,
        segment_analysis=segment_analysis_payload,
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
        limits=_build_limits(activity_df),
    )


def prepare_theoretical_response(activity_df, registry: SeriesRegistry) -> TheoreticalActivityResponse:
    base_pace_s_per_km = 300.0
    df_theoretical, summary_base = theoretical_service.prepare_base(activity_df, base_pace_s_per_km)
    _ = df_theoretical

    series_index = SeriesIndex(available=registry.get_available_series(activity_df))

    return TheoreticalActivityResponse(
        summary=to_jsonable(summary_base),
        highlights={},
        zones=None,
        best_efforts=None,
        personal_records=None,
        segment_analysis=None,
        performance_predictions=None,
        pauses=None,
        climbs=None,
        series_index=series_index,
        training_load=None,
        limits=_build_limits(activity_df),
    )


@router.get("/activity/{activity_id}/real", response_model=RealActivityResponse)
async def get_real_activity(request: Request, activity_id: str):
    """Retourne les données d'analyse pour une activité réelle"""
    try:
        storage = request.app.state.storage
        df = storage.load_dataframe(activity_id)

        if df.empty:
            raise HTTPException(status_code=404, detail=f"Activity {activity_id} not found")

        registry = get_series_registry(request)
        return prepare_real_response(df, registry)

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Activity {activity_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get real activity: {str(e)}")


@router.get("/activity/{activity_id}/theoretical", response_model=TheoreticalActivityResponse)
async def get_theoretical_activity(request: Request, activity_id: str):
    """Retourne les données d'analyse pour une activité théorique"""
    try:
        storage = request.app.state.storage
        df = storage.load_dataframe(activity_id)

        if df.empty:
            raise HTTPException(status_code=404, detail=f"Activity {activity_id} not found")

        registry = get_series_registry(request)
        return prepare_theoretical_response(df, registry)

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Activity {activity_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get theoretical activity: {str(e)}")


@router.get("/activity/{activity_id}/pace-vs-grade", response_model=PaceVsGradeResponse)
async def get_pace_vs_grade(request: Request, activity_id: str):
    """Returns binned pace vs grade data (backend-computed)."""

    try:
        storage = request.app.state.storage
        df = storage.load_dataframe(activity_id)

        if df.empty:
            raise HTTPException(status_code=404, detail=f"Activity {activity_id} not found")

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
