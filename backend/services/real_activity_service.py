from __future__ import annotations

"""Orchestration activite reelle (sans couche UI)."""

import math
from typing import Any

import numpy as np
import pandas as pd

from core.ref_data import get_pro_pace_vs_grade_df
from core.transform_report import TransformReport
from core.metrics import compute_garmin_like_stats, estimate_zone_inputs
from core.real_run_analysis import (
    build_distribution_plots,
    build_pace_elevation_plot,
    build_pace_grade_heatmap,
    build_pace_grade_scatter,
    build_pace_vs_grade_plot,
    build_residuals_vs_grade,
    compute_best_efforts,
    compute_best_efforts_by_duration,
    compute_race_predictions,
    compute_climbs,
    compute_derived_series,
    compute_pause_markers,
    compute_splits,
    compute_summary_stats,
)
from core.utils import seconds_to_mmss
from services.models import (
    RealRunBase,
    RealRunDerived,
    RealRunFigures,
    RealRunMapPayload,
    RealRunParams,
    RealRunResult,
    RealRunPaceMode,
    RealRunViewParams,
)


def _default_cap_min_per_km(summary: dict[str, Any]) -> float:
    avg = summary.get("average_pace_s_per_km")
    if isinstance(avg, (int, float)) and avg == avg and avg > 0:
        return float((avg / 60.0) * 1.4)
    return 8.0


def prepare_base(df: pd.DataFrame) -> RealRunBase:
    derived_raw = compute_derived_series(df)
    derived = RealRunDerived(
        grade_series=derived_raw.grade_series,
        moving_mask=derived_raw.moving_mask,
        gap_series=derived_raw.gap_series,
    )

    summary = compute_summary_stats(df, moving_mask=derived.moving_mask)
    zone_defaults = estimate_zone_inputs(df, moving_mask=derived.moving_mask)
    best_efforts = compute_best_efforts(df)
    best_efforts_time = compute_best_efforts_by_duration(df)
    climbs = compute_climbs(df, grade_series=derived.grade_series)
    pauses = compute_pause_markers(df, moving_mask=derived.moving_mask)
    splits = compute_splits(df)
    default_cap_min_per_km = _default_cap_min_per_km(summary)

    return RealRunBase(
        derived=derived,
        summary=summary,
        zone_defaults=zone_defaults,
        best_efforts=best_efforts,
        best_efforts_time=best_efforts_time,
        climbs=climbs,
        pauses=pauses,
        splits=splits,
        default_cap_min_per_km=default_cap_min_per_km,
    )


def _build_highlights(best_df: pd.DataFrame, climbs: list[dict[str, Any]], garmin_summary: dict[str, Any]) -> list[str]:
    highlights: list[str] = []
    if best_df is not None and not best_df.empty and "distance_km" in best_df:
        row_1k = best_df[best_df["distance_km"] == 1.0]
        if not row_1k.empty:
            time_s = row_1k.iloc[0].get("time_s")
            pace_s = row_1k.iloc[0].get("pace_s_per_km")
            if time_s == time_s and pace_s == pace_s:
                highlights.append(
                    f"Km le plus rapide: {seconds_to_mmss(time_s)} ({seconds_to_mmss(pace_s)} / km)"
                )

    if climbs:
        climb = climbs[0]
        highlights.append(
            f"Plus grande montee: +{climb['elevation_gain_m']:.0f} m sur {climb['distance_km']:.2f} km"
        )

    longest_pause_s = garmin_summary.get("longest_pause_s")
    if isinstance(longest_pause_s, (int, float)) and longest_pause_s == longest_pause_s and longest_pause_s >= 5:
        highlights.append(f"Plus longue pause: {seconds_to_mmss(longest_pause_s)}")

    return highlights


def build_highlights(best_df: pd.DataFrame, climbs: list[dict[str, Any]], garmin_summary: dict[str, Any]) -> list[str]:
    return _build_highlights(best_df, climbs, garmin_summary)


def _colorize(series: pd.Series, vmin: float | None = None, vmax: float | None = None) -> list[list[int]]:
    valid = series.dropna()
    if valid.empty:
        return [[120, 120, 120, 80]] * len(series)

    if vmin is None:
        vmin = float(np.percentile(valid, 5))
    if vmax is None:
        vmax = float(np.percentile(valid, 95))
    if vmax == vmin:
        vmax = vmin + 1e-3

    vals = series.fillna(vmin)
    t = (vals - vmin) / (vmax - vmin)
    t = t.clip(0, 1)
    t_np = t.to_numpy()

    stops = [0.0, 0.5, 1.0]
    r = np.interp(t_np, stops, [70, 110, 240]).astype(int)
    g = np.interp(t_np, stops, [60, 210, 70]).astype(int)
    b = np.interp(t_np, stops, [200, 120, 40]).astype(int)
    alpha = 150
    return [[int(rr), int(gg), int(bb), alpha] for rr, gg, bb in zip(r, g, b)]


def _build_map_payload(
    df: pd.DataFrame,
    *,
    derived: RealRunDerived,
    climbs: list[dict[str, Any]],
    pauses: list[dict[str, Any]],
    map_color_mode: str,
) -> RealRunMapPayload:
    map_df = compute_map_df(df, derived=derived, map_color_mode=map_color_mode)
    if map_df.empty:
        return RealRunMapPayload(map_df=map_df, climb_points=[], pause_points=pauses or [])

    climb_points: list[dict[str, Any]] = []
    for climb in climbs:
        idx = int(climb["end_idx"])
        if 0 <= idx < len(df):
            label = f"+{climb['elevation_gain_m']:.0f} m @ {climb['avg_grade_percent']:.1f} %"
            if climb.get("vam_m_h") == climb.get("vam_m_h"):
                label += f" | VAM {climb['vam_m_h']:.0f}"
            climb_points.append({"lon": df.iloc[idx]["lon"], "lat": df.iloc[idx]["lat"], "label": label})

    return RealRunMapPayload(map_df=map_df, climb_points=climb_points, pause_points=pauses or [])


def compute_map_df(
    df: pd.DataFrame,
    *,
    derived: RealRunDerived,
    map_color_mode: str,
    report: TransformReport | None = None,
) -> pd.DataFrame:
    """Compute the map-ready DataFrame used by build_map_payload.

This function is UI-free and intentionally testable.
    """

    if df.empty:
        return pd.DataFrame()

    rows_in = len(df)
    map_df = df[["lat", "lon", "distance_m"]].dropna().copy()
    if report is not None:
        report.add(
            "map_payload:dropna_lat_lon_distance",
            rows_in=rows_in,
            rows_out=len(map_df),
            reason="drop points without coordinates/distance",
        )
    if map_df.empty:
        return map_df

    pace_s_per_km = df["pace_s_per_km"] if "pace_s_per_km" in df else None
    map_df["pace_min_per_km"] = (pace_s_per_km / 60.0) if pace_s_per_km is not None else math.nan
    map_df["grade_percent"] = derived.grade_series
    map_df["gap_min_per_km"] = (derived.gap_series / 60.0) if derived.gap_series is not None else math.nan

    if map_color_mode == "grade":
        map_df["color"] = _colorize(map_df["grade_percent"].clip(-20, 20))
        map_df["label"] = map_df["grade_percent"].apply(lambda v: f"Pente: {v:.1f} %" if v == v else "Pente: -")
    elif map_color_mode == "gap":
        map_df["color"] = _colorize(map_df["gap_min_per_km"].clip(2.5, 15.0))
        map_df["label"] = map_df["gap_min_per_km"].apply(lambda v: f"GAP: {seconds_to_mmss(v*60)} / km" if v == v else "GAP: -")
    else:
        map_df["color"] = _colorize(map_df["pace_min_per_km"].clip(2.5, 15.0))
        map_df["label"] = map_df["pace_min_per_km"].apply(lambda v: f"Allure: {seconds_to_mmss(v*60)} / km" if v == v else "Allure: -")

    return map_df


def build_map_payload(
    df: pd.DataFrame,
    *,
    derived: RealRunDerived,
    climbs: list[dict[str, Any]],
    pauses: list[dict[str, Any]],
    map_color_mode: str,
) -> RealRunMapPayload:
    return _build_map_payload(
        df,
        derived=derived,
        climbs=climbs,
        pauses=pauses,
        map_color_mode=map_color_mode,
    )


def _compute_pace_series(
    df: pd.DataFrame, *, derived: RealRunDerived, view: RealRunViewParams, cap_min_per_km: float
) -> pd.Series:
    if view.pace_mode == "real_time":
        pace_series = df["pace_s_per_km"]
    else:
        delta_time = df["delta_time_s"].fillna(0)
        delta_dist = df["delta_distance_m"].fillna(0)
        moving_time_cum = delta_time.where(derived.moving_mask, 0).cumsum()
        moving_dist_cum = delta_dist.where(derived.moving_mask, 0).cumsum() / 1000.0
        moving_dist_cum = moving_dist_cum.replace({0: float("nan")})
        pace_series = moving_time_cum / moving_dist_cum

    if view.smoothing_points > 0:
        window = int(view.smoothing_points) + 1
        pace_series = pace_series.rolling(window=window, min_periods=1, center=True).mean()

    pace_series = pace_series.clip(upper=float(cap_min_per_km) * 60.0)
    return pace_series


def compute_pace_series(
    df: pd.DataFrame,
    *,
    derived: RealRunDerived,
    pace_mode: RealRunPaceMode,
    smoothing_points: int,
    cap_min_per_km: float,
) -> pd.Series:
    return _compute_pace_series(
        df,
        derived=derived,
        view=RealRunViewParams(
            pace_mode=pace_mode,
            smoothing_points=smoothing_points,
            cap_min_per_km=cap_min_per_km,
        ),
        cap_min_per_km=cap_min_per_km,
    )


def compute_garmin_stats(
    df: pd.DataFrame,
    *,
    moving_mask: pd.Series,
    gap_series: pd.Series | None,
    grade_series: pd.Series | None = None,
    params: RealRunParams,
) -> dict[str, Any]:
    return compute_garmin_like_stats(
        df,
        moving_mask=moving_mask,
        gap_series=gap_series,
        grade_series=grade_series,
        hr_max=params.hr_max,
        hr_rest=params.hr_rest if params.use_hrr else None,
        use_hrr=params.use_hrr,
        pace_threshold_s_per_km=params.pace_threshold_s_per_km,
        ftp_w=params.ftp_w,
        cadence_target=params.cadence_target,
        use_moving_time=params.use_moving_time,
    )


def build_figures(
    df: pd.DataFrame,
    *,
    pace_series: pd.Series,
    grade_series: pd.Series,
) -> RealRunFigures:
    pro_ref = get_pro_pace_vs_grade_df()
    return RealRunFigures(
        pace_elevation=build_pace_elevation_plot(df, pace_series=pace_series),
        distributions=build_distribution_plots(df, pace_series=pace_series, grade_series=grade_series),
        pace_vs_grade=build_pace_vs_grade_plot(df, pace_series=pace_series, grade_series=grade_series, pro_ref=pro_ref),
        residuals_vs_grade=build_residuals_vs_grade(df, pace_series=pace_series, grade_series=grade_series),
        pace_grade_scatter=build_pace_grade_scatter(df, pace_series=pace_series, grade_series=grade_series),
        pace_grade_heatmap=build_pace_grade_heatmap(df, pace_series=pace_series, grade_series=grade_series),
    )


def analyze_real_activity(
    df: pd.DataFrame,
    *,
    base: RealRunBase | None = None,
    params: RealRunParams | None = None,
    view: RealRunViewParams | None = None,
) -> RealRunResult:
    base = base or prepare_base(df)
    params = params or RealRunParams()
    view = view or RealRunViewParams()

    garmin = compute_garmin_stats(
        df,
        moving_mask=base.derived.moving_mask,
        gap_series=base.derived.gap_series,
        grade_series=base.derived.grade_series,
        params=params,
    )

    performance_predictions = compute_race_predictions(base.best_efforts)

    cap_min_per_km = float(view.cap_min_per_km) if view.cap_min_per_km is not None else base.default_cap_min_per_km
    pace_series = _compute_pace_series(df, derived=base.derived, view=view, cap_min_per_km=cap_min_per_km)

    splits = base.splits
    figures = build_figures(df, pace_series=pace_series, grade_series=base.derived.grade_series)

    map_payload = build_map_payload(
        df,
        derived=base.derived,
        climbs=base.climbs,
        pauses=base.pauses,
        map_color_mode=view.map_color_mode,
    )
    highlights = build_highlights(base.best_efforts, base.climbs, garmin.get("summary", {}))

    return RealRunResult(
        derived=base.derived,
        summary=base.summary,
        garmin=garmin,
        zone_defaults=base.zone_defaults,
        best_efforts=base.best_efforts,
        best_efforts_time=base.best_efforts_time,
        climbs=base.climbs,
        pauses=base.pauses,
        highlights=highlights,
        pace_series=pace_series,
        default_cap_min_per_km=base.default_cap_min_per_km,
        splits=splits,
        performance_predictions=performance_predictions,
        map_payload=map_payload,
        figures=figures,
    )
