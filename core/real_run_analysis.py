import math
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from core.grade_table import grade_factor
from core.utils import seconds_to_mmss

DEFAULT_PRO_PACE_PATH = Path(__file__).resolve().parents[1] / "pro_pace_vs_grade.csv"
MIN_GRADE_DISTANCE_M = 1.0


def _load_pro_pace_vs_grade(csv_path: str | Path = DEFAULT_PRO_PACE_PATH) -> pd.DataFrame:
    """Charge une table de reference allure vs pente si disponible."""
    try:
        df = pd.read_csv(Path(csv_path))
    except FileNotFoundError:
        return pd.DataFrame(columns=["grade_percent", "pace_s_per_km_pro"])
    expected_cols = {"grade_percent", "pace_s_per_km_pro"}
    if not expected_cols.issubset(df.columns):
        return pd.DataFrame(columns=["grade_percent", "pace_s_per_km_pro"])
    df = df.dropna(subset=["grade_percent", "pace_s_per_km_pro"])
    return df


def compute_moving_mask(
    df: pd.DataFrame, pause_threshold_m_s: float = 0.5, min_pause_duration_s: float = 5.0
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

    moving = np.ones(len(df), dtype=bool)
    low_start = None
    low_accum = 0.0

    for i, (dt, sp) in enumerate(zip(delta_time, speed_med)):
        if dt <= 0:
            continue
        if sp < pause_threshold_m_s:
            if low_start is None:
                low_start = i
                low_accum = 0.0
            low_accum += dt
        else:
            if low_start is not None and low_accum >= min_pause_duration_s:
                moving[low_start : i + 1] = False
            low_start = None
            low_accum = 0.0

    if low_start is not None and low_accum >= min_pause_duration_s:
        moving[low_start:] = False

    return pd.Series(moving, index=df.index)


def compute_derived_series(
    df: pd.DataFrame,
    pace_series: pd.Series | None = None,
    grade_smooth_window: int = 5,
    pause_threshold_m_s: float = 0.5,
    min_pause_duration_s: float = 5.0,
) -> Dict[str, pd.Series]:
    """Calcule un ensemble de derives reutilisables (pente, moving mask, GAP)."""
    grade_series = compute_grade_percent_series(df, smooth_window=grade_smooth_window)
    moving_mask = compute_moving_mask(
        df, pause_threshold_m_s=pause_threshold_m_s, min_pause_duration_s=min_pause_duration_s
    )
    pace_series = pace_series if pace_series is not None else df["pace_s_per_km"]
    gap_series = compute_gap_series(df, pace_series=pace_series, grade_series=grade_series)
    return {
        "grade_series": grade_series,
        "moving_mask": moving_mask,
        "gap_series": gap_series,
    }


def compute_summary_stats(df: pd.DataFrame, moving_mask: pd.Series | None = None) -> Dict[str, float]:
    """Calcule les statistiques principales d'une sortie reelle."""
    distance_m_series = df["distance_m"].dropna()
    total_distance_m = distance_m_series.max() if not distance_m_series.empty else 0.0
    total_distance_km = total_distance_m / 1000.0

    times = df["time"].dropna()
    if len(times) >= 2:
        total_time_s = (times.iloc[-1] - times.iloc[0]).total_seconds()
    else:
        elapsed = df["elapsed_time_s"].dropna()
        total_time_s = elapsed.max() if not elapsed.empty else 0.0

    moving_mask = moving_mask if moving_mask is not None else compute_moving_mask(df)
    moving_time_s = float(df.loc[moving_mask, "delta_time_s"].fillna(0).sum()) if not df.empty else 0.0

    average_pace_s_per_km = total_time_s / total_distance_km if total_distance_km > 0 else math.nan
    average_speed_kmh = (total_distance_km) / (total_time_s / 3600.0) if total_time_s > 0 else math.nan

    elevation = df["elevation"].dropna().to_numpy()
    elevation_gain_m = float(np.clip(np.diff(elevation), 0, None).sum()) if len(elevation) > 1 else 0.0

    return {
        "distance_km": total_distance_km,
        "total_time_s": total_time_s,
        "moving_time_s": moving_time_s,
        "average_pace_s_per_km": average_pace_s_per_km,
        "average_speed_kmh": average_speed_kmh,
        "elevation_gain_m": elevation_gain_m,
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


def compute_best_efforts(df: pd.DataFrame) -> pd.DataFrame:
    """Detecte les meilleurs temps sur des distances cibles (1k, 5k, 10k, semi, marathon)."""
    if df.empty:
        return pd.DataFrame(columns=["distance_km", "time_s", "pace_s_per_km"])

    working = df[["distance_m", "elapsed_time_s", "delta_time_s"]].copy()
    if working["elapsed_time_s"].isna().all():
        working["elapsed_time_s"] = working["delta_time_s"].fillna(0).cumsum()
    working = working.dropna(subset=["distance_m", "elapsed_time_s"])
    if working.empty:
        return pd.DataFrame(columns=["distance_km", "time_s", "pace_s_per_km"])

    distances_m = working["distance_m"].to_numpy()
    times_s = working["elapsed_time_s"].to_numpy()

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


def build_pace_vs_grade_plot(
    df: pd.DataFrame, pace_series: pd.Series | None = None, grade_series: pd.Series | None = None
) -> go.Figure:
    """Courbe allure (min/km) en fonction de la pente (%) lissée par binning."""
    mask_moving = (df["speed_m_s"] > 0.5) & (df["delta_time_s"].fillna(0) > 0)
    df_filtered = df[mask_moving]
    pace_series = pace_series.loc[df_filtered.index] if pace_series is not None else df_filtered["pace_s_per_km"]

    if grade_series is not None:
        grade = grade_series.reindex(df_filtered.index)
    else:
        grade = _compute_grade_percent(df_filtered, smooth_window=5)
    grade = grade.clip(lower=-20, upper=20)

    data = pd.DataFrame(
        {
            "grade_percent": grade,
            "pace_min_per_km": (pace_series / 60.0),
        }
    ).replace([np.inf, -np.inf], np.nan).dropna()

    pace_mean_min = pace_series.mean(skipna=True) / 60.0 if len(pace_series.dropna()) else math.nan
    if not math.isnan(pace_mean_min):
        slow_mask = data["grade_percent"].between(-5.0, 5.0) & (data["pace_min_per_km"] > pace_mean_min * 1.5)
        data = data.loc[~slow_mask]

    if data.empty:
        return go.Figure()

    bins = np.arange(-20, 20.5, 0.5)
    data["grade_bin"] = pd.cut(data["grade_percent"], bins=bins, labels=False)

    grouped = data.groupby("grade_bin").agg(
        grade_center=("grade_percent", "median"),
        pace_med=("pace_min_per_km", "median"),
        pace_std=("pace_min_per_km", "std"),
    )
    grouped = grouped.dropna(subset=["grade_center", "pace_med"]).sort_values("grade_center")
    grouped["pace_std"] = grouped["pace_std"].fillna(0.0)
    if grouped.empty:
        return go.Figure()

    pace_vals = grouped["pace_med"]
    pace_std_upper = (grouped["pace_med"] + grouped["pace_std"]).clip(lower=0)
    pace_std_lower = (grouped["pace_med"] - grouped["pace_std"]).clip(lower=0)
    pace_custom = pace_vals.apply(lambda v: seconds_to_mmss(v * 60.0) if v == v else "-")

    fig = go.Figure()
    fig.add_vline(x=0, line=dict(color="#bbbbbb", width=1), layer="below", opacity=0.7)
    pro_ref = _load_pro_pace_vs_grade()
    if not pro_ref.empty:
        pro_ref = pro_ref.sort_values("grade_percent")
        pro_ref["pace_min_per_km"] = pro_ref["pace_s_per_km_pro"] / 60.0
        pro_ref["pace_display"] = pro_ref["pace_s_per_km_pro"].apply(seconds_to_mmss)
        fig.add_trace(
            go.Scatter(
                x=pro_ref["grade_percent"],
                y=pro_ref["pace_min_per_km"],
                mode="lines",
                line=dict(color="#999999", dash="dash"),
                name="Ref pro",
                customdata=pro_ref["pace_display"],
                hovertemplate="Pente: %{x:.1f} %<br>Allure pro: %{customdata} / km<extra></extra>",
            )
        )
    fig.add_trace(
        go.Scatter(
            x=pd.concat([grouped["grade_center"], grouped["grade_center"][::-1]]),
            y=pd.concat([pace_std_upper, pace_std_lower[::-1]]),
            fill="toself",
            fillcolor="rgba(76,120,168,0.18)",
            line=dict(color="rgba(0,0,0,0)"),
            name="+/- 1 écart-type",
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=grouped["grade_center"],
            y=grouped["pace_med"],
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
            pro_ref["pace_min_per_km"] if not pro_ref.empty else pd.Series(dtype=float),
        ]
    )
    tick_start = math.floor(pace_for_ticks.min() * 2) / 2.0
    tick_end = math.ceil(pace_for_ticks.max() * 2) / 2.0
    tick_step = 0.5
    tick_vals = np.arange(tick_start, tick_end + tick_step, tick_step)
    tick_text = [seconds_to_mmss(v * 60.0) for v in tick_vals]
    fig.update_layout(
        xaxis_title="Pente (%)",
        yaxis_title="Allure (min/km)",
        yaxis=dict(autorange=True, tickmode="array", tickvals=tick_vals, ticktext=tick_text),
        margin=dict(t=40, b=40),
    )
    return fig


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
    mask = (df["speed_m_s"] > 0.5) & (df["delta_time_s"].fillna(0) > 0)
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


def build_residuals_vs_grade(
    df: pd.DataFrame, pace_series: pd.Series | None = None, grade_series: pd.Series | None = None
) -> go.Figure:
    """Courbe des résidus allure réelle - allure attendue (via grade_table) par pente."""
    mask = (df["speed_m_s"] > 0.5) & (df["delta_time_s"].fillna(0) > 0)
    subset = df[mask]
    if subset.empty:
        return go.Figure()
    pace_used = pace_series.loc[subset.index] if pace_series is not None else subset["pace_s_per_km"]
    grade_for_subset = grade_series.reindex(subset.index) if grade_series is not None else _compute_grade_percent(subset, smooth_window=5)
    flat_pace = _estimate_flat_pace(subset, pace_used, grade_series=grade_for_subset)
    if math.isnan(flat_pace):
        return go.Figure()

    expected = pd.Series(flat_pace * grade_factor(grade_for_subset.to_numpy()), index=grade_for_subset.index)
    residual = (pace_used - expected) / 60.0  # min/km

    data = pd.DataFrame({"grade": grade_for_subset, "residual": residual}).dropna()
    if data.empty:
        return go.Figure()

    bins = np.arange(-20, 20.5, 0.5)
    data["grade_bin"] = pd.cut(data["grade"], bins=bins, labels=False)
    grouped = data.groupby("grade_bin").agg(
        grade_center=("grade", "median"),
        residual_med=("residual", "median"),
        residual_q1=("residual", lambda x: x.quantile(0.25)),
        residual_q3=("residual", lambda x: x.quantile(0.75)),
    ).dropna()
    if grouped.empty:
        return go.Figure()

    fig = go.Figure()
    fig.add_vline(x=0, line=dict(color="#bbbbbb", width=1), layer="below", opacity=0.7)
    fig.add_trace(
        go.Scatter(
            x=grouped["grade_center"],
            y=grouped["residual_med"],
            mode="lines",
            name="Résidu vs pente (médian)",
            line=dict(color="#4c78a8"),
            hovertemplate="Pente: %{x:.1f} %<br>Résidu: %{y:.2f} min/km<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=pd.concat([grouped["grade_center"], grouped["grade_center"][::-1]]),
            y=pd.concat([grouped["residual_q1"], grouped["residual_q3"][::-1]]),
            fill="toself",
            fillcolor="rgba(76,120,168,0.2)",
            line=dict(color="rgba(0,0,0,0)"),
            hoverinfo="skip",
            showlegend=True,
            name="+/- 1 écart-type",
        )
    )
    fig.add_hline(y=0, line=dict(color="#999", dash="dash"))
    fig.update_layout(
        xaxis_title="Pente (%)",
        yaxis_title="Résidu (min/km) — positif = plus lent que attendu",
        margin=dict(t=40, b=40),
        xaxis=dict(range=[-20, 20]),
    )
    return fig


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
