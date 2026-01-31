import math
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from core.grade_table import grade_factor
from core.ref_data import get_pro_pace_vs_grade_df
from core.transform_report import TransformReport
from core.derived import DerivedSeries
from core.utils import seconds_to_mmss
from core.stats.basic_stats import compute_basic_stats
from core.constants import (
    DEFAULT_GRADE_SMOOTH_WINDOW,
    DEFAULT_MIN_PAUSE_DURATION_S,
    MOVING_SPEED_THRESHOLD_M_S,
)

MIN_GRADE_DISTANCE_M = 1.0


def compute_moving_mask(
    df: pd.DataFrame,
    pause_threshold_m_s: float = MOVING_SPEED_THRESHOLD_M_S,
    min_pause_duration_s: float = DEFAULT_MIN_PAUSE_DURATION_S,
) -> pd.Series:
    """
    Approche type Strava :
    - Lisse la vitesse instantanee (mediane glissante) pour eviter les a-coups GPS.
    - Declare une pause si la vitesse lissee reste sous le seuil pendant >= min_pause_duration_s.
    Retourne un masque booleen (True = en mouvement).
    """
    speed = df["speed_m_s"].fillna(0)
    delta_time = df["delta_time_s"].fillna(0).to_numpy()
    speed_med = speed.rolling(window=3, center=True, min_periods=1).median().to_numpy()

    dt = np.where(delta_time > 0, delta_time, 0.0)
    moving = np.ones(len(df), dtype=bool)

    # Preserve le comportement historique :
    # - l'accumulation de pause ne considere que les indices avec dt>0
    # - quand une pause se termine, le premier index apres la pause est aussi marque comme non-mouvant
    active = np.flatnonzero(dt > 0)
    if active.size:
        low_active = speed_med[active] < float(pause_threshold_m_s)
        if low_active.any():
            # Encodage RLE (run-length) des sequences contigues "low speed" sur l'espace des index actifs.
            starts = np.flatnonzero(
                np.concatenate(([low_active[0]], low_active[1:] & ~low_active[:-1]))
            )
            ends = np.flatnonzero(
                np.concatenate((low_active[:-1] & ~low_active[1:], [low_active[-1]]))
            )
            for s_pos, e_pos in zip(starts, ends):
                if not low_active[s_pos]:
                    continue
                duration = float(dt[active[s_pos : e_pos + 1]].sum())
                if duration >= float(min_pause_duration_s):
                    start_idx = int(active[s_pos])
                    if (e_pos + 1) < active.size:
                        stop_idx = int(active[e_pos + 1])
                    else:
                        stop_idx = int(len(df) - 1)
                    moving[start_idx : stop_idx + 1] = False

    return pd.Series(moving, index=df.index)


def compute_derived_series(
    df: pd.DataFrame,
    pace_series: pd.Series | None = None,
    grade_smooth_window: int = DEFAULT_GRADE_SMOOTH_WINDOW,
    pause_threshold_m_s: float = MOVING_SPEED_THRESHOLD_M_S,
    min_pause_duration_s: float = DEFAULT_MIN_PAUSE_DURATION_S,
) -> DerivedSeries:
    """Calcule un ensemble de derives reutilisables (pente, moving mask, GAP)."""
    grade_series = compute_grade_percent_series(df, smooth_window=grade_smooth_window)
    moving_mask = compute_moving_mask(
        df, pause_threshold_m_s=pause_threshold_m_s, min_pause_duration_s=min_pause_duration_s
    )
    pace_series = pace_series if pace_series is not None else df["pace_s_per_km"]
    gap_series = compute_gap_series(df, pace_series=pace_series, grade_series=grade_series)
    return DerivedSeries(grade_series=grade_series, moving_mask=moving_mask, gap_series=gap_series)


def compute_summary_stats(df: pd.DataFrame, moving_mask: pd.Series | None = None) -> Dict[str, float]:
    """Calcule les statistiques principales d'une sortie reelle."""
    moving_mask = moving_mask if moving_mask is not None else compute_moving_mask(df)
    stats = compute_basic_stats(df, moving_mask=moving_mask)

    average_pace_s_per_km = stats.total_time_s / stats.distance_km if stats.distance_km > 0 else math.nan
    average_speed_kmh = (stats.distance_km) / (stats.total_time_s / 3600.0) if stats.total_time_s > 0 else math.nan

    return {
        "distance_km": stats.distance_km,
        "total_time_s": stats.total_time_s,
        "moving_time_s": stats.moving_time_s,
        "average_pace_s_per_km": average_pace_s_per_km,
        "average_speed_kmh": average_speed_kmh,
        "elevation_gain_m": stats.elevation_gain_m,
    }


def compute_splits(df: pd.DataFrame, split_distance_km: float = 1.0) -> pd.DataFrame:
    """Decoupe la course en splits de ~1 km."""
    if df.empty:
        return pd.DataFrame(
            columns=["split_index", "distance_km", "time_s", "pace_s_per_km", "elevation_gain_m"]
        )

    split_distance_m = split_distance_km * 1000.0
    working = df[["distance_m", "elapsed_time_s", "elevation"]].dropna(subset=["distance_m"]).copy()
    working["split_index"] = (working["distance_m"] // split_distance_m).astype(int)

    splits = []
    for idx, group in working.groupby("split_index"):
        group = group.sort_values("distance_m")
        dist_start = group["distance_m"].iloc[0]
        dist_end = group["distance_m"].iloc[-1]
        distance_km = (dist_end - dist_start) / 1000.0

        time_start = group["elapsed_time_s"].iloc[0]
        time_end = group["elapsed_time_s"].iloc[-1]
        time_s = float(time_end - time_start) if not math.isnan(time_start) and not math.isnan(time_end) else math.nan

        pace_s_per_km = time_s / distance_km if distance_km > 0 and time_s == time_s else math.nan

        elevation_series = group["elevation"].ffill().bfill().to_numpy()
        elevation_gain_m = (
            float(np.clip(np.diff(elevation_series), 0, None).sum()) if len(elevation_series) > 1 else 0.0
        )

        splits.append(
            {
                "split_index": int(idx + 1),
                "distance_km": distance_km,
                "time_s": time_s,
                "pace_s_per_km": pace_s_per_km,
                "elevation_gain_m": elevation_gain_m,
            }
        )

    return pd.DataFrame(splits)


def _prepare_effort_arrays(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    if df.empty:
        return np.array([]), np.array([])

    working = df[["distance_m", "elapsed_time_s", "delta_time_s"]].copy()
    if working["elapsed_time_s"].isna().all():
        working["elapsed_time_s"] = working["delta_time_s"].fillna(0).cumsum()
    working = working.dropna(subset=["distance_m", "elapsed_time_s"])
    if working.empty:
        return np.array([]), np.array([])

    distances_m = working["distance_m"].to_numpy(dtype=float)
    times_s = working["elapsed_time_s"].to_numpy(dtype=float)
    return distances_m, times_s


def compute_best_efforts(df: pd.DataFrame) -> pd.DataFrame:
    """Detecte les meilleurs temps sur des distances cibles (1k, 5k, 10k, semi, marathon)."""
    distances_m, times_s = _prepare_effort_arrays(df)
    if distances_m.size == 0 or times_s.size == 0:
        return pd.DataFrame(columns=["distance_km", "time_s", "pace_s_per_km"])

    targets_km = [1, 5, 10, 21.097, 42.195]
    results = []

    for target_km in targets_km:
        target_m = target_km * 1000.0
        best_time = math.nan
        start_idx = 0
        for end_idx in range(len(distances_m)):
            # Avance le debut tant que la fenetre depasse la distance cible
            while start_idx < end_idx and (distances_m[end_idx] - distances_m[start_idx]) >= target_m:
                current_time = times_s[end_idx] - times_s[start_idx]
                if current_time > 0 and (math.isnan(best_time) or current_time < best_time):
                    best_time = current_time
                start_idx += 1
        pace = best_time / target_km if target_km > 0 and not math.isnan(best_time) else math.nan
        results.append({"distance_km": target_km, "time_s": best_time, "pace_s_per_km": pace})

    return pd.DataFrame(results)


def compute_best_efforts_by_duration(
    df: pd.DataFrame, durations_s: list[int] | None = None
) -> pd.DataFrame:
    """Detecte les meilleures distances sur des durées cibles (ex: 1, 5, 10, 20, 30 min)."""
    durations_s = durations_s or [60, 300, 600, 1200, 1800]
    distances_m, times_s = _prepare_effort_arrays(df)
    if distances_m.size == 0 or times_s.size == 0:
        return pd.DataFrame(columns=["duration_s", "distance_km", "time_s", "pace_s_per_km"])

    results = []
    for duration_s in durations_s:
        best_distance = 0.0
        best_time = math.nan
        start_idx = 0
        for end_idx in range(len(times_s)):
            while start_idx < end_idx and (times_s[end_idx] - times_s[start_idx]) >= duration_s:
                time_window = times_s[end_idx] - times_s[start_idx]
                dist_window = distances_m[end_idx] - distances_m[start_idx]
                if time_window > 0 and dist_window > best_distance:
                    best_distance = float(dist_window)
                    best_time = float(time_window)
                start_idx += 1
        distance_km = best_distance / 1000.0 if best_distance > 0 else math.nan
        pace = best_time / distance_km if distance_km > 0 and best_time == best_time else math.nan
        results.append(
            {
                "duration_s": float(duration_s),
                "distance_km": float(distance_km),
                "time_s": float(best_time) if best_time == best_time else math.nan,
                "pace_s_per_km": float(pace) if pace == pace else math.nan,
            }
        )

    return pd.DataFrame(results)


def compute_race_predictions(
    best_efforts_df: pd.DataFrame,
    targets_km: list[float] | None = None,
    exponent: float = 1.06,
) -> list[dict[str, float]]:
    """Predictions temps via formule de Riegel a partir des best efforts."""
    if best_efforts_df is None or best_efforts_df.empty:
        return []

    targets_km = targets_km or [5.0, 10.0, 21.097, 42.195]
    base = best_efforts_df.dropna(subset=["distance_km", "time_s"])
    if base.empty:
        return []

    out: list[dict[str, float]] = []
    for target in targets_km:
        best_time = math.nan
        best_base_dist = math.nan
        best_base_time = math.nan
        for _, row in base.iterrows():
            dist_km = float(row["distance_km"])
            time_s = float(row["time_s"])
            if dist_km <= 0 or time_s <= 0:
                continue
            predicted = time_s * (target / dist_km) ** exponent
            if predicted > 0 and (math.isnan(best_time) or predicted < best_time):
                best_time = predicted
                best_base_dist = dist_km
                best_base_time = time_s
        if best_time == best_time:
            out.append(
                {
                    "target_distance_km": float(target),
                    "predicted_time_s": float(best_time),
                    "base_distance_km": float(best_base_dist),
                    "base_time_s": float(best_base_time),
                    "exponent": float(exponent),
                }
            )

    return out


def build_distribution_plots(
    df: pd.DataFrame, pace_series: pd.Series | None = None, grade_series: pd.Series | None = None
) -> Dict[str, go.Figure]:
    """Construit des histogrammes pour l'allure et la pente."""
    figs: Dict[str, go.Figure] = {}

    pace_raw = pace_series if pace_series is not None else df["pace_s_per_km"]
    delta_t = df["delta_time_s"].fillna(0)
    mask_pace = pace_raw.notna() & (delta_t > 0)
    pace = pace_raw[mask_pace]
    if not pace.empty:
        pace_min = (pace / 60.0).clip(upper=15)
        pace_bins = 0.25  # 15 s -> 0.25 min
        tick_start = math.floor(pace_min.min() * 4) / 4.0
        tick_end = math.ceil(pace_min.max() * 4) / 4.0
        edges = np.arange(tick_start, tick_end + pace_bins, pace_bins)
        counts, _ = np.histogram(pace_min, bins=edges, weights=delta_t[mask_pace])
        centers = edges[:-1] + pace_bins / 2.0
        custom_range = [
            f"{seconds_to_mmss(start * 60.0)} - {seconds_to_mmss(end * 60.0)}"
            for start, end in zip(edges[:-1], edges[1:])
        ]
        custom_time = [seconds_to_mmss(v) if v == v else "-" for v in counts]
        fig_pace = go.Figure()
        fig_pace.add_trace(
            go.Bar(
                x=centers,
                y=counts,
                marker_color="#4c78a8",
                name="Allure (min/km)",
                customdata=list(zip(custom_range, custom_time)),
                hovertemplate="Allure: %{customdata[0]}<br>Temps: %{customdata[1]}<extra></extra>",
            )
        )
        tick_vals = edges
        tick_text = [seconds_to_mmss(v * 60.0) for v in tick_vals]
        max_y = float(counts.max()) if len(counts) else 0.0
        y_tick_step = max(60.0, max_y / 5.0) if max_y > 0 else 60.0
        y_tick_vals = np.arange(0, max_y + y_tick_step, y_tick_step)
        y_tick_text = [seconds_to_mmss(v) for v in y_tick_vals]
        fig_pace.update_layout(
            xaxis_title="Allure (min/km)",
            yaxis_title="Temps (mm:ss)",
            bargap=0.05,
            margin=dict(t=40, b=40),
            xaxis=dict(tickmode="array", tickvals=tick_vals, ticktext=tick_text),
            yaxis=dict(tickmode="array", tickvals=y_tick_vals, ticktext=y_tick_text),
        )
        # Ligne pointillée pour l'allure moyenne
        pace_mean_min = float(pace_min.mean()) if len(pace_min) else math.nan
        if pace_mean_min == pace_mean_min:
            fig_pace.add_vline(
                x=pace_mean_min,
                line=dict(color="rgba(76,120,168,0.6)", dash="dash"),
                annotation_text=f"Moyenne: {seconds_to_mmss(pace_mean_min*60)}",
                annotation_position="top",
                annotation_font=dict(color="rgba(76,120,168,0.8)", size=12),
            )
        pace_median_min = float(pace_min.median()) if len(pace_min) else math.nan
        if pace_median_min == pace_median_min:
            fig_pace.add_vline(
                x=pace_median_min,
                line=dict(color="rgba(76,120,168,0.4)", dash="dot"),
                annotation_text=f"Médiane: {seconds_to_mmss(pace_median_min*60)}",
                annotation_position="top",
                annotation_font=dict(color="rgba(76,120,168,0.7)", size=12),
            )
        figs["pace"] = fig_pace

    # Pente par segment
    # Histogramme de pente pondéré par le temps (bins 1 % centrés sur 0)
    if grade_series is not None:
        grade = grade_series.reindex(df.index)
    else:
        grade = _compute_grade_percent(df, smooth_window=5)

    grade = grade.replace([np.inf, -np.inf], np.nan)
    delta_t = df["delta_time_s"].fillna(0)
    mask_grade = grade.notna() & (delta_t > 0)
    if mask_grade.any():
        bins = np.arange(-20.5, 21.5, 1.0)
        values = grade.clip(lower=-20, upper=20)
        weights = delta_t
        hist, edges = np.histogram(values[mask_grade], bins=bins, weights=weights[mask_grade])
        centers = (edges[:-1] + edges[1:]) / 2
        hist_mmss = [seconds_to_mmss(v) if v == v else "-" for v in hist]
        fig_grade = go.Figure(
            data=go.Bar(
                x=centers,
                y=hist,
                marker_color="#f28e2b",
                name="Pente (%)",
                customdata=hist_mmss,
                hovertemplate="Pente: %{x:.1f} %<br>Temps: %{customdata}<extra></extra>",
            )
        )
        max_y = float(hist.max()) if len(hist) else 0.0
        tick_step = max(60.0, (max_y / 5.0)) if max_y > 0 else 60.0
        tick_vals = np.arange(0, max_y + tick_step, tick_step)
        tick_text = [seconds_to_mmss(v) for v in tick_vals]
        fig_grade.update_layout(
            xaxis_title="Pente (%)",
            yaxis_title="Temps (mm:ss)",
            yaxis=dict(tickmode="array", tickvals=tick_vals, ticktext=tick_text),
            bargap=0.05,
            margin=dict(t=40, b=40),
        )
        figs["grade"] = fig_grade

    return figs


def compute_pace_vs_grade_data(
    df: pd.DataFrame,
    *,
    pace_series: pd.Series | None = None,
    grade_series: pd.Series | None = None,
    report: TransformReport | None = None,
) -> pd.DataFrame:
    """Compute the data used by build_pace_vs_grade_plot.

    Returns a DataFrame with columns: grade_center, pace_med, pace_std, pace_n.
    - grade_center: median grade (%) in the bin
    - pace_med: median pace (min/km) in the bin
    - pace_std: stddev pace (min/km) in the bin
    - pace_n: number of points in the bin
    """

    out_cols = ["grade_center", "pace_med", "pace_std", "pace_n"]
    if df.empty:
        return pd.DataFrame(columns=out_cols)

    mask_moving = (df["speed_m_s"] > MOVING_SPEED_THRESHOLD_M_S) & (df["delta_time_s"].fillna(0) > 0)
    df_filtered = df[mask_moving]
    if report is not None:
        report.add(
            "pace_vs_grade:mask_moving",
            rows_in=len(df),
            rows_out=int(mask_moving.sum()),
            reason="keep moving points (speed>threshold and dt>0)",
        )
    if df_filtered.empty:
        return pd.DataFrame(columns=out_cols)

    pace_s = pace_series.loc[df_filtered.index] if pace_series is not None else df_filtered["pace_s_per_km"]
    grade_s = grade_series.reindex(df_filtered.index) if grade_series is not None else _compute_grade_percent(df_filtered, smooth_window=5)
    grade_s = grade_s.clip(lower=-20, upper=20)

    data = (
        pd.DataFrame({"grade_percent": grade_s, "pace_min_per_km": (pace_s / 60.0)})
        .replace([np.inf, -np.inf], np.nan)
        .dropna()
    )
    if report is not None:
        report.add(
            "pace_vs_grade:dropna",
            rows_in=len(df_filtered),
            rows_out=len(data),
            reason="drop non-finite grade/pace",
        )

    pace_mean_min = pace_s.mean(skipna=True) / 60.0 if len(pace_s.dropna()) else math.nan
    if pace_mean_min == pace_mean_min and not data.empty:
        slow_mask = data["grade_percent"].between(-5.0, 5.0) & (data["pace_min_per_km"] > pace_mean_min * 1.5)
        before = len(data)
        data = data.loc[~slow_mask]
        if report is not None:
            report.add(
                "pace_vs_grade:slow_filter",
                rows_in=before,
                rows_out=len(data),
                reason="remove slow outliers near flat grade",
                details={"pace_mean_min": float(pace_mean_min), "mult": 1.5},
            )

    if data.empty:
        return pd.DataFrame(columns=out_cols)

    bins = np.arange(-20, 20.5, 0.5)
    data["grade_bin"] = pd.cut(data["grade_percent"], bins=bins, labels=False)
    grouped = data.groupby("grade_bin").agg(
        grade_center=("grade_percent", "median"),
        pace_med=("pace_min_per_km", "median"),
        pace_std=("pace_min_per_km", "std"),
        pace_n=("pace_min_per_km", "count"),
    )
    grouped = grouped.dropna(subset=["grade_center", "pace_med"]).sort_values("grade_center")
    grouped["pace_std"] = grouped["pace_std"].fillna(0.0)
    if grouped.empty:
        return pd.DataFrame(columns=out_cols)

    return grouped[out_cols].reset_index(drop=True)


def build_pace_vs_grade_plot_from_data(
    data: pd.DataFrame,
    *,
    pro_ref: pd.DataFrame | None = None,
) -> go.Figure:
    """Build the Plotly figure from compute_pace_vs_grade_data output."""

    if data is None or data.empty:
        return go.Figure()

    pace_vals = data["pace_med"]
    pace_std_upper = (data["pace_med"] + data["pace_std"]).clip(lower=0)
    pace_std_lower = (data["pace_med"] - data["pace_std"]).clip(lower=0)
    pace_custom = pace_vals.apply(lambda v: seconds_to_mmss(float(v) * 60.0) if v == v else "-")

    fig = go.Figure()
    fig.add_vline(x=0, line=dict(color="#bbbbbb", width=1), layer="below", opacity=0.7)

    if pro_ref is not None and not pro_ref.empty:
        expected_cols = {"grade_percent", "pace_s_per_km_pro"}
        if expected_cols.issubset(set(pro_ref.columns)):
            pro_line = pro_ref.sort_values("grade_percent")
            pro_line["pace_min_per_km"] = pro_line["pace_s_per_km_pro"] / 60.0
            pro_line["pace_display"] = pro_line["pace_s_per_km_pro"].apply(seconds_to_mmss)
            fig.add_trace(
                go.Scatter(
                    x=pro_line["grade_percent"],
                    y=pro_line["pace_min_per_km"],
                    mode="lines",
                    line=dict(color="#999999", dash="dash"),
                    name="Ref pro",
                    customdata=pro_line["pace_display"],
                    hovertemplate="Pente: %{x:.1f} %<br>Allure pro: %{customdata} / km<extra></extra>",
                )
            )

    fig.add_trace(
        go.Scatter(
            x=pd.concat([data["grade_center"], data["grade_center"][::-1]]),
            y=pd.concat([pace_std_upper, pace_std_lower[::-1]]),
            fill="toself",
            fillcolor="rgba(76,120,168,0.18)",
            line=dict(color="rgba(0,0,0,0)"),
            name="+/- 1 ecart-type",
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=data["grade_center"],
            y=data["pace_med"],
            mode="lines",
            line=dict(color="#4c78a8"),
            name="Allure vs pente (lissee)",
            customdata=pace_custom,
            hovertemplate="Pente: %{x:.1f} %<br>Allure mediane: %{customdata} / km<extra></extra>",
        )
    )

    pace_for_ticks = pd.concat(
        [
            pace_vals,
            pace_std_upper,
            pace_std_lower,
            (pro_ref["pace_s_per_km_pro"] / 60.0) if (pro_ref is not None and not pro_ref.empty and "pace_s_per_km_pro" in pro_ref) else pd.Series(dtype=float),
        ]
    )
    tick_start = math.floor(float(pace_for_ticks.min()) * 2) / 2.0
    tick_end = math.ceil(float(pace_for_ticks.max()) * 2) / 2.0
    tick_step = 0.5
    tick_vals = np.arange(tick_start, tick_end + tick_step, tick_step)
    tick_text = [seconds_to_mmss(float(v) * 60.0) for v in tick_vals]
    fig.update_layout(
        xaxis_title="Pente (%)",
        yaxis_title="Allure (min/km)",
        yaxis=dict(autorange=True, tickmode="array", tickvals=tick_vals, ticktext=tick_text),
        margin=dict(t=40, b=40),
    )
    return fig


def build_pace_vs_grade_plot(
    df: pd.DataFrame, pace_series: pd.Series | None = None, grade_series: pd.Series | None = None, *, pro_ref: pd.DataFrame | None = None
) -> go.Figure:
    """Courbe allure (min/km) en fonction de la pente (%) lissee par binning."""

    data = compute_pace_vs_grade_data(df, pace_series=pace_series, grade_series=grade_series)
    if pro_ref is None:
        pro_ref = get_pro_pace_vs_grade_df()
    return build_pace_vs_grade_plot_from_data(data, pro_ref=pro_ref)


def _compute_grade_percent(
    df: pd.DataFrame, smooth_window: int = 5, min_distance_m: float = MIN_GRADE_DISTANCE_M
) -> pd.Series:
    """Calcule une pente (%) par point, avec lissage optionnel de l'altitude."""
    grade_df = df[["elevation", "delta_distance_m"]].copy()
    if smooth_window and smooth_window > 1:
        grade_df["elevation"] = grade_df["elevation"].rolling(
            window=smooth_window, center=True, min_periods=1
        ).mean()
    grade_df["prev_elev"] = grade_df["elevation"].shift(1)
    grade = (grade_df["elevation"] - grade_df["prev_elev"]) / grade_df["delta_distance_m"] * 100.0
    if min_distance_m and min_distance_m > 0:
        grade = grade.where(grade_df["delta_distance_m"] >= min_distance_m)
    return grade.replace([np.inf, -np.inf], np.nan)


def compute_grade_percent_series(df: pd.DataFrame, smooth_window: int = 5) -> pd.Series:
    """Interface publique pour récupérer une série de pentes (%)."""
    return _compute_grade_percent(df, smooth_window=smooth_window)


def _estimate_flat_pace(
    df: pd.DataFrame, pace_series: pd.Series, grade_series: pd.Series | None = None
) -> float:
    """Estime l'allure de base 'plat' (s/km) en prenant la médiane sur les pentes proches de 0."""
    grade = grade_series.reindex(df.index) if grade_series is not None else _compute_grade_percent(df, smooth_window=5)
    mask_flat = grade.between(-1.0, 1.0) & (pace_series.notna())
    flat_paces = pace_series[mask_flat]
    if len(flat_paces.dropna()) >= 10:
        return float(flat_paces.median())
    valid = pace_series.dropna()
    return float(valid.median()) if len(valid) else math.nan


def compute_gap_series(
    df: pd.DataFrame, pace_series: pd.Series | None = None, grade_series: pd.Series | None = None
) -> pd.Series:
    """Calcule une allure GAP (allure équivalente plat) en s/km."""
    pace = pace_series.reindex(df.index) if pace_series is not None else df["pace_s_per_km"]
    grade = grade_series.reindex(df.index) if grade_series is not None else _compute_grade_percent(df, smooth_window=5)
    grade_arr = grade.to_numpy()
    factor = grade_factor(grade_arr)
    pace_arr = pace.to_numpy()
    gap = pace_arr / factor
    invalid = ~np.isfinite(grade_arr) | ~np.isfinite(pace_arr) | ~np.isfinite(factor) | (factor == 0)
    gap = np.where(invalid, np.nan, gap)
    return pd.Series(gap, index=df.index)


def build_pace_grade_scatter(
    df: pd.DataFrame, pace_series: pd.Series | None = None, grade_series: pd.Series | None = None
) -> go.Figure:
    """Nuage de points allure vs pente, couleur distance (ou FC si dispo)."""
    mask = (df["speed_m_s"] > MOVING_SPEED_THRESHOLD_M_S) & (df["delta_time_s"].fillna(0) > 0)
    subset = df[mask].copy()
    if subset.empty:
        return go.Figure()
    pace = (pace_series.loc[subset.index] if pace_series is not None else subset["pace_s_per_km"]) / 60.0
    grade = grade_series.reindex(subset.index) if grade_series is not None else _compute_grade_percent(subset, smooth_window=5)
    subset["grade_percent"] = grade
    subset["pace_min_per_km"] = pace

    color_series = subset["distance_m"] / 1000.0
    if "heart_rate" in subset.columns and subset["heart_rate"].notna().any():
        color_series = subset["heart_rate"]
        color_label = "FC (bpm)"
    else:
        color_label = "Distance (km)"

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=subset["grade_percent"],
            y=subset["pace_min_per_km"],
            mode="markers",
            marker=dict(
                color=color_series,
                colorscale="Turbo",
                size=6,
                colorbar=dict(title=color_label),
                opacity=0.7,
            ),
            hovertemplate="Pente: %{x:.1f} %<br>Allure: %{y:.2f} min/km<extra></extra>",
        )
    )
    fig.update_layout(
        xaxis_title="Pente (%)",
        yaxis_title="Allure (min/km)",
        yaxis=dict(autorange=True),
        margin=dict(t=40, b=40),
    )
    return fig


def build_pace_grade_heatmap(
    df: pd.DataFrame, pace_series: pd.Series | None = None, grade_series: pd.Series | None = None
) -> go.Figure:
    """Heatmap allure x pente, pondérée par le temps passé."""
    if df.empty:
        return go.Figure()
    pace = (pace_series if pace_series is not None else df["pace_s_per_km"]) / 60.0
    grade = grade_series.reindex(df.index) if grade_series is not None else _compute_grade_percent(df, smooth_window=5)
    delta_t = df["delta_time_s"].fillna(0)
    mask = (delta_t > 0) & pace.notna() & grade.notna()
    if not mask.any():
        return go.Figure()

    pace_clipped = pace.clip(lower=2.5, upper=15.0)
    grade_clipped = grade.clip(lower=-20, upper=20)
    pace_bins = np.arange(2.5, 15.1, 0.25)
    grade_bins = np.arange(-20, 20.5, 1.0)
    hist, x_edges, y_edges = np.histogram2d(
        grade_clipped[mask],
        pace_clipped[mask],
        bins=[grade_bins, pace_bins],
        weights=delta_t[mask],
    )
    fig = go.Figure(
        data=go.Heatmap(
            x=(x_edges[:-1] + x_edges[1:]) / 2,
            y=(y_edges[:-1] + y_edges[1:]) / 2,
            z=hist.T,
            colorscale="Viridis",
            colorbar=dict(title="Temps (s)"),
            hovertemplate="Pente: %{x:.1f} %<br>Allure: %{y:.2f} min/km<br>Temps: %{z:.0f} s<extra></extra>",
        )
    )
    fig.update_layout(
        xaxis_title="Pente (%)",
        yaxis_title="Allure (min/km)",
        yaxis=dict(autorange=True),
        margin=dict(t=40, b=40),
    )
    return fig


def compute_residuals_vs_grade_data(
    df: pd.DataFrame,
    *,
    pace_series: pd.Series | None = None,
    grade_series: pd.Series | None = None,
    report: TransformReport | None = None,
) -> pd.DataFrame:
    """Compute the data used by build_residuals_vs_grade.

    Returns a DataFrame with columns: grade_center, residual_med, residual_q1, residual_q3.
    """

    out_cols = ["grade_center", "residual_med", "residual_q1", "residual_q3"]
    if df.empty:
        return pd.DataFrame(columns=out_cols)

    mask = (df["speed_m_s"] > MOVING_SPEED_THRESHOLD_M_S) & (df["delta_time_s"].fillna(0) > 0)
    subset = df[mask]
    if report is not None:
        report.add(
            "residuals_vs_grade:mask_moving",
            rows_in=len(df),
            rows_out=int(mask.sum()),
            reason="keep moving points (speed>threshold and dt>0)",
        )
    if subset.empty:
        return pd.DataFrame(columns=out_cols)

    pace_used = pace_series.loc[subset.index] if pace_series is not None else subset["pace_s_per_km"]
    grade_for_subset = grade_series.reindex(subset.index) if grade_series is not None else _compute_grade_percent(subset, smooth_window=5)
    flat_pace = _estimate_flat_pace(subset, pace_used, grade_series=grade_for_subset)
    if math.isnan(flat_pace):
        return pd.DataFrame(columns=out_cols)

    expected = pd.Series(float(flat_pace) * grade_factor(grade_for_subset.to_numpy()), index=grade_for_subset.index)
    residual = (pace_used - expected) / 60.0  # min/km
    data = pd.DataFrame({"grade": grade_for_subset, "residual": residual}).dropna()
    if report is not None:
        report.add(
            "residuals_vs_grade:dropna",
            rows_in=len(subset),
            rows_out=len(data),
            reason="drop non-finite grade/residual",
        )
    if data.empty:
        return pd.DataFrame(columns=out_cols)

    bins = np.arange(-20, 20.5, 0.5)
    data["grade_bin"] = pd.cut(data["grade"], bins=bins, labels=False)
    grouped = data.groupby("grade_bin").agg(
        grade_center=("grade", "median"),
        residual_med=("residual", "median"),
        residual_q1=("residual", lambda x: x.quantile(0.25)),
        residual_q3=("residual", lambda x: x.quantile(0.75)),
    ).dropna()
    if grouped.empty:
        return pd.DataFrame(columns=out_cols)

    return grouped[out_cols].sort_values("grade_center").reset_index(drop=True)


def build_residuals_vs_grade_plot_from_data(data: pd.DataFrame) -> go.Figure:
    if data is None or data.empty:
        return go.Figure()

    fig = go.Figure()
    fig.add_vline(x=0, line=dict(color="#bbbbbb", width=1), layer="below", opacity=0.7)
    fig.add_trace(
        go.Scatter(
            x=data["grade_center"],
            y=data["residual_med"],
            mode="lines",
            name="Residu vs pente (median)",
            line=dict(color="#4c78a8"),
            hovertemplate="Pente: %{x:.1f} %<br>Residu: %{y:.2f} min/km<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=pd.concat([data["grade_center"], data["grade_center"][::-1]]),
            y=pd.concat([data["residual_q1"], data["residual_q3"][::-1]]),
            fill="toself",
            fillcolor="rgba(76,120,168,0.2)",
            line=dict(color="rgba(0,0,0,0)"),
            hoverinfo="skip",
            showlegend=True,
            name="+/- 1 ecart-type",
        )
    )
    fig.add_hline(y=0, line=dict(color="#999", dash="dash"))
    fig.update_layout(
        xaxis_title="Pente (%)",
        yaxis_title="Residu (min/km) - positif = plus lent que attendu",
        margin=dict(t=40, b=40),
        xaxis=dict(range=[-20, 20]),
    )
    return fig


def build_residuals_vs_grade(
    df: pd.DataFrame, pace_series: pd.Series | None = None, grade_series: pd.Series | None = None
) -> go.Figure:
    """Courbe des residus allure reelle - allure attendue (via grade_table) par pente."""

    data = compute_residuals_vs_grade_data(df, pace_series=pace_series, grade_series=grade_series)
    return build_residuals_vs_grade_plot_from_data(data)


def compute_climbs(
    df: pd.DataFrame,
    min_grade: float = 3.0,
    min_distance_m: float = 150.0,
    grade_series: pd.Series | None = None,
) -> List[Dict]:
    """Détecte les montées (pente >= min_grade) et retourne les 3 principales."""
    if df.empty:
        return []
    grade = grade_series.reindex(df.index) if grade_series is not None else _compute_grade_percent(df, smooth_window=5)
    dist = df["delta_distance_m"].fillna(0).to_numpy()
    elev = df["elevation"].ffill().bfill().to_numpy()
    delta_time = df["delta_time_s"].fillna(0).to_numpy()
    pace = df["pace_s_per_km"].to_numpy()

    climbs: List[Dict] = []
    in_climb = False
    start_idx = 0
    gain = 0.0
    distance = 0.0
    time_spent = 0.0
    pace_accum = []

    for i, g in enumerate(grade):
        segment_dist = dist[i] if i < len(dist) else 0.0
        if g is not None and not math.isnan(g) and g >= min_grade and segment_dist > 0:
            if not in_climb:
                start_idx = i
                gain = 0.0
                distance = 0.0
                time_spent = 0.0
                pace_accum = []
                in_climb = True
            if i > 0:
                gain += max(0.0, elev[i] - elev[i - 1])
            distance += segment_dist
            time_spent += delta_time[i]
            if i < len(pace) and pace[i] == pace[i]:
                pace_accum.append(pace[i])
        else:
            if in_climb and distance >= min_distance_m and gain > 0:
                end_idx = i - 1
                avg_grade = gain / distance * 100.0 if distance > 0 else math.nan
                vam = (gain / time_spent) * 3600 if time_spent > 0 else math.nan
                climbs.append(
                    {
                        "start_idx": start_idx,
                        "end_idx": end_idx,
                        "distance_km": distance / 1000.0,
                        "elevation_gain_m": gain,
                        "avg_grade_percent": avg_grade,
                        "vam_m_h": vam,
                        "pace_s_per_km": float(np.median(pace_accum)) if pace_accum else math.nan,
                        "distance_m_end": float(df.iloc[end_idx]["distance_m"]) if end_idx < len(df) else float("nan"),
                    }
                )
            in_climb = False
    if in_climb and distance >= min_distance_m and gain > 0:
        end_idx = len(df) - 1
        avg_grade = gain / distance * 100.0 if distance > 0 else math.nan
        vam = (gain / time_spent) * 3600 if time_spent > 0 else math.nan
        climbs.append(
            {
                "start_idx": start_idx,
                "end_idx": end_idx,
                "distance_km": distance / 1000.0,
                "elevation_gain_m": gain,
                "avg_grade_percent": avg_grade,
                "vam_m_h": vam,
                "pace_s_per_km": float(np.median(pace_accum)) if pace_accum else math.nan,
                "distance_m_end": float(df.iloc[end_idx]["distance_m"]),
            }
        )

    climbs = sorted(climbs, key=lambda c: c["elevation_gain_m"], reverse=True)[:3]
    return climbs


def compute_pause_markers(df: pd.DataFrame, moving_mask: pd.Series | None = None) -> List[Dict]:
    """Identifie les pauses (moving_mask False) et retourne des marqueurs carte."""
    if df.empty or "lat" not in df or "lon" not in df:
        return []
    moving_mask = moving_mask if moving_mask is not None else compute_moving_mask(df)
    delta_time = df["delta_time_s"].fillna(0)
    markers: List[Dict] = []
    in_pause = False
    start_idx = 0
    duration = 0.0
    for i, moving in enumerate(moving_mask):
        if not moving and delta_time.iloc[i] > 0:
            if not in_pause:
                start_idx = i
                duration = 0.0
                in_pause = True
            duration += delta_time.iloc[i]
        else:
            if in_pause and duration >= 5.0:
                markers.append(
                    {
                        "lat": df.iloc[start_idx]["lat"],
                        "lon": df.iloc[start_idx]["lon"],
                        "label": f"Pause {seconds_to_mmss(duration)}",
                    }
                )
            in_pause = False
    if in_pause and duration >= 5.0:
        markers.append(
            {
                "lat": df.iloc[start_idx]["lat"],
                "lon": df.iloc[start_idx]["lon"],
                "label": f"Pause {seconds_to_mmss(duration)}",
            }
        )
    return markers


def build_pace_elevation_plot(df: pd.DataFrame, pace_series: pd.Series | None = None) -> go.Figure:
    """Combine allure (min/km) et altitude sur une seule figure Plotly."""
    distance_km = df["distance_m"] / 1000.0
    pace_series = pace_series if pace_series is not None else df["pace_s_per_km"]
    pace_min_per_km = pace_series / 60.0
    pace_display = pace_series.apply(lambda v: seconds_to_mmss(v) if v == v else "-")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=distance_km,
            y=pace_min_per_km,
            name="Allure (min/km)",
            mode="lines",
            line=dict(color="#0066cc"),
            yaxis="y1",
            customdata=pace_display,
            hovertemplate="Distance: %{x:.2f} km<br>Allure: %{customdata} / km<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=distance_km,
            y=df["elevation"],
            name="Altitude (m)",
            mode="lines",
            line=dict(color="#f28e2b"),
            yaxis="y2",
            opacity=0.7,
            hovertemplate="Distance: %{x:.2f} km<br>Altitude: %{y:.0f} m<extra></extra>",
        )
    )

    fig.update_layout(
        xaxis=dict(
            title="Distance (km)",
            showspikes=True,
            spikemode="across",
            spikesnap="cursor",
            spikethickness=1,
            spikecolor="#999",
        ),
        yaxis=dict(title="Allure (min/km)", autorange="reversed"),
        yaxis2=dict(
            title="Altitude (m)",
            overlaying="y",
            side="right",
            showgrid=False,
        ),
        legend=dict(orientation="h", y=-0.2),
        margin=dict(t=40, b=40),
    )
    return fig
