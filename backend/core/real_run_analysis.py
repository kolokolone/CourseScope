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


def _effective_sample_size(weights: np.ndarray) -> float:
    w = np.asarray(weights, dtype=float)
    w = w[np.isfinite(w) & (w > 0)]
    if w.size == 0:
        return 0.0
    s1 = float(w.sum())
    s2 = float(np.square(w).sum())
    if s2 <= 0:
        return 0.0
    return (s1 * s1) / s2


def _weighted_quantile_step(values: np.ndarray, weights: np.ndarray, p: float) -> float:
    """Weighted quantile using a step-CDF definition.

    Returns the smallest value v such that cumulative_weight(v) >= p * total_weight.
    """

    x = np.asarray(values, dtype=float)
    w = np.asarray(weights, dtype=float)
    mask = np.isfinite(x) & np.isfinite(w) & (w > 0)
    x = x[mask]
    w = w[mask]
    if x.size == 0:
        return math.nan
    if x.size == 1:
        return float(x[0])

    p = float(np.clip(p, 0.0, 1.0))
    order = np.argsort(x, kind="mergesort")
    x = x[order]
    w = w[order]
    cw = np.cumsum(w)
    total = float(cw[-1])
    if total <= 0:
        return math.nan
    threshold = p * total
    idx = int(np.searchsorted(cw, threshold, side="left"))
    idx = min(max(idx, 0), int(x.size - 1))
    return float(x[idx])


def _weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    x = np.asarray(values, dtype=float)
    w = np.asarray(weights, dtype=float)
    mask = np.isfinite(x) & np.isfinite(w) & (w > 0)
    x = x[mask]
    w = w[mask]
    if x.size == 0:
        return math.nan
    total = float(w.sum())
    if total <= 0:
        return math.nan
    return float((x * w).sum() / total)


def _weighted_std(values: np.ndarray, weights: np.ndarray) -> float:
    x = np.asarray(values, dtype=float)
    w = np.asarray(weights, dtype=float)
    mask = np.isfinite(x) & np.isfinite(w) & (w > 0)
    x = x[mask]
    w = w[mask]
    if x.size == 0:
        return math.nan
    total = float(w.sum())
    if total <= 0:
        return math.nan
    mu = float((x * w).sum() / total)
    var = float((w * np.square(x - mu)).sum() / total)
    return float(math.sqrt(var))


def _winsorize_limits_iqr(
    values: np.ndarray,
    weights: np.ndarray,
    *,
    k_iqr: float,
) -> tuple[float, float]:
    q25 = _weighted_quantile_step(values, weights, 0.25)
    q75 = _weighted_quantile_step(values, weights, 0.75)
    if not (math.isfinite(q25) and math.isfinite(q75)):
        return math.nan, math.nan
    iqr = float(q75 - q25)
    if not math.isfinite(iqr) or iqr <= 1e-9:
        return math.nan, math.nan
    lo = float(q25 - float(k_iqr) * iqr)
    hi = float(q75 + float(k_iqr) * iqr)
    return lo, hi


def _winsorize_limits_mad(
    values: np.ndarray,
    weights: np.ndarray,
    *,
    k_mad_sigma: float,
) -> tuple[float, float]:
    m = _weighted_quantile_step(values, weights, 0.5)
    if not math.isfinite(m):
        return math.nan, math.nan
    abs_dev = np.abs(np.asarray(values, dtype=float) - float(m))
    mad = _weighted_quantile_step(abs_dev, weights, 0.5)
    if not math.isfinite(mad) or mad <= 1e-9:
        return math.nan, math.nan
    sigma = 1.4826 * float(mad)
    lo = float(m - float(k_mad_sigma) * sigma)
    hi = float(m + float(k_mad_sigma) * sigma)
    return lo, hi


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


def compute_pace_series(
    df: pd.DataFrame,
    *,
    moving_mask: pd.Series | None = None,
    pace_mode: str = "real_time",
    smoothing_points: int = 0,
    cap_min_per_km: float | None = None,
) -> pd.Series:
    """Compute a pace series in s/km.

    - pace_mode='real_time': uses df['pace_s_per_km'] (per-point pace).
    - pace_mode='moving_time': uses cumulative moving time / cumulative moving distance.
    - smoothing_points: if >0, applies a centered rolling mean with window=smoothing_points+1.
    - cap_min_per_km: if set, clips pace to at most cap_min_per_km*60.
    """

    if df.empty:
        return pd.Series(dtype=float)

    if pace_mode == "moving_time":
        dt = df["delta_time_s"].fillna(0)
        dd = df["delta_distance_m"].fillna(0)
        mask = moving_mask.reindex(df.index).fillna(False) if moving_mask is not None else pd.Series(True, index=df.index)

        moving_time_cum = dt.where(mask, 0).cumsum()
        moving_dist_km_cum = (dd.where(mask, 0).cumsum() / 1000.0).replace({0: float("nan")})
        pace = moving_time_cum / moving_dist_km_cum
    else:
        pace = df["pace_s_per_km"]

    if smoothing_points and int(smoothing_points) > 0:
        window = int(smoothing_points) + 1
        pace = pace.rolling(window=window, min_periods=1, center=True).mean()

    if cap_min_per_km is not None and math.isfinite(float(cap_min_per_km)):
        pace = pace.clip(upper=float(cap_min_per_km) * 60.0)

    return pace


def compute_splits(df: pd.DataFrame, split_distance_km: float = 1.0) -> pd.DataFrame:
    """Decoupe la course en splits de ~1 km.
    
    Retourne pour chaque split:
    - split_index: Numéro du split (commence à 1)
    - distance_km: Distance du split en km
    - time_s: Temps du split en secondes
    - pace_s_per_km: Allure du split (s/km)
    - elevation_gain_m: Dénivelé positif du split (m)
    - avg_hr_bpm: Fréquence cardiaque moyenne du split (bpm) si disponible
    - elev_delta_m: Variation d'altitude totale du split (m)
    """
    columns = [
        "split_index",
        "distance_km",
        "time_s",
        "pace_s_per_km",
        "elevation_gain_m",
        "avg_hr_bpm",
        "elev_delta_m",
    ]

    if df.empty:
        return pd.DataFrame(columns=columns)

    split_distance_m = float(split_distance_km) * 1000.0

    # We exclude pauses from split pace by using moving time.
    # Without a full moving-mask here, we approximate "paused" as dt>0 with no distance progress.
    # This is closer to how Strava's default pace behaves (moving time), vs elapsed time.
    base_cols = ["distance_m", "elapsed_time_s"]
    if "elevation" in df.columns:
        base_cols.append("elevation")
    working = df[base_cols].copy()
    if "heart_rate" in df.columns:
        working["heart_rate"] = df["heart_rate"]

    working = working.dropna(subset=["distance_m"]).copy()
    if working.empty:
        return pd.DataFrame(columns=columns)

    # Ensure elapsed_time_s exists.
    if "elapsed_time_s" not in working.columns or working["elapsed_time_s"].isna().all():
        if "delta_time_s" in df.columns:
            working["elapsed_time_s"] = df["delta_time_s"].fillna(0).cumsum()
        else:
            return pd.DataFrame(columns=columns)

    working["distance_m"] = pd.to_numeric(working["distance_m"], errors="coerce")
    working["elapsed_time_s"] = pd.to_numeric(working["elapsed_time_s"], errors="coerce")

    working = working.dropna(subset=["distance_m", "elapsed_time_s"]).copy()
    if working.empty:
        return pd.DataFrame(columns=columns)

    # Sort by time, enforce monotonic distance.
    working = working.sort_values("elapsed_time_s").copy()
    working["distance_m"] = working["distance_m"].cummax()

    dt = working["elapsed_time_s"].diff().fillna(0.0)
    dd = working["distance_m"].diff().fillna(0.0)
    moving = (dt > 0) & (dd > 0.5)
    working["moving_time_s"] = dt.where(moving, 0.0).cumsum()

    def _unique_xy(x: pd.Series, y: pd.Series) -> tuple[np.ndarray, np.ndarray]:
        tmp = pd.DataFrame({"x": x.to_numpy(dtype=float), "y": y.to_numpy(dtype=float)})
        tmp = tmp.dropna().groupby("x", as_index=False).last()
        return tmp["x"].to_numpy(dtype=float), tmp["y"].to_numpy(dtype=float)

    dist_x, moving_y = _unique_xy(working["distance_m"], working["moving_time_s"])
    if dist_x.size == 0:
        return pd.DataFrame(columns=columns)

    total_distance_m = float(dist_x[-1])
    if not math.isfinite(total_distance_m) or total_distance_m <= 0:
        return pd.DataFrame(columns=columns)

    # Build split boundaries at exact distances: 0, 1km, 2km, ..., last partial.
    n_full = int(total_distance_m // split_distance_m)
    boundaries: list[float] = [0.0]
    for k in range(1, n_full + 1):
        boundaries.append(float(k) * split_distance_m)
    if boundaries[-1] < total_distance_m:
        boundaries.append(total_distance_m)

    # Optional elevation interpolation for delta/gain.
    elev_x: np.ndarray | None = None
    elev_y: np.ndarray | None = None
    if "elevation" in working.columns and not working["elevation"].isna().all():
        elev_series = working["elevation"].ffill().bfill()
        elev_x, elev_y = _unique_xy(working["distance_m"], elev_series)

    splits: list[dict[str, float]] = []
    for i in range(len(boundaries) - 1):
        start_m = float(boundaries[i])
        end_m = float(boundaries[i + 1])
        if end_m <= start_m:
            continue

        distance_km = (end_m - start_m) / 1000.0
        if distance_km <= 0:
            continue

        t0 = float(np.interp(start_m, dist_x, moving_y))
        t1 = float(np.interp(end_m, dist_x, moving_y))
        time_s = t1 - t0
        pace_s_per_km = time_s / distance_km if time_s > 0 and math.isfinite(time_s) else math.nan

        elevation_gain_m = 0.0
        elev_delta_m = 0.0
        if elev_x is not None and elev_y is not None and elev_x.size:
            e0 = float(np.interp(start_m, elev_x, elev_y))
            e1 = float(np.interp(end_m, elev_x, elev_y))
            elev_delta_m = e1 - e0

            seg = working[(working["distance_m"] >= start_m) & (working["distance_m"] <= end_m)].copy()
            seg = seg.sort_values("distance_m")
            # Include boundary points for stable gain calculation.
            elevations = [e0]
            if "elevation" in seg.columns and not seg["elevation"].isna().all():
                elevations.extend(seg["elevation"].ffill().bfill().dropna().astype(float).tolist())
            elevations.append(e1)
            if len(elevations) > 1:
                elevation_gain_m = float(np.clip(np.diff(np.array(elevations, dtype=float)), 0, None).sum())

        avg_hr_bpm = math.nan
        if "heart_rate" in working.columns and not working["heart_rate"].isna().all():
            hr_seg = working[(working["distance_m"] >= start_m) & (working["distance_m"] <= end_m)]["heart_rate"].dropna()
            if not hr_seg.empty:
                avg_hr_bpm = float(hr_seg.astype(float).mean())

        splits.append(
            {
                "split_index": float(i + 1),
                "distance_km": float(distance_km),
                "time_s": float(time_s) if math.isfinite(time_s) else math.nan,
                "pace_s_per_km": float(pace_s_per_km) if math.isfinite(pace_s_per_km) else math.nan,
                "elevation_gain_m": float(elevation_gain_m),
                "avg_hr_bpm": float(avg_hr_bpm) if math.isfinite(avg_hr_bpm) else math.nan,
                "elev_delta_m": float(elev_delta_m),
            }
        )

    out = pd.DataFrame(splits)
    if out.empty:
        return pd.DataFrame(columns=columns)

    # Ensure column order and numeric types.
    out = out[columns]
    out["split_index"] = out["split_index"].astype(int)
    return out


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
    moving_mask: pd.Series | None = None,
    report: TransformReport | None = None,
) -> pd.DataFrame:
    """Compute binned pace-vs-grade metrics.

    Semantics:
    - Filters pauses using compute_moving_mask (pause>=DEFAULT_MIN_PAUSE_DURATION_S).
    - Keeps walking + running as long as points are moving.
    - Grade bins are fixed: [-20, +20] step 0.5, inclusive (include_lowest=True).
    - Aggregates are time-weighted by delta_time_s.
    """

    out_cols = [
        "grade_center",
        "pace_med_s_per_km",
        "pace_std_s_per_km",
        "pace_n",
        "time_s_bin",
        "pace_mean_w_s_per_km",
        "pace_q25_w_s_per_km",
        "pace_q50_w_s_per_km",
        "pace_q75_w_s_per_km",
        "pace_iqr_w_s_per_km",
        "pace_std_w_s_per_km",
        "pace_n_eff",
        "outlier_clip_frac",
    ]
    if df.empty:
        return pd.DataFrame(columns=out_cols)

    # Defaults: quality gating and winsorization (robust outliers) are intentionally conservative.
    min_bin_time_s = 20.0
    min_bin_n_eff = 5.0
    winsor_min_time_s = 30.0
    winsor_min_n_eff = 8.0
    winsor_k_iqr = 2.0
    winsor_k_mad_sigma = 4.0

    dt = pd.to_numeric(df.get("delta_time_s"), errors="coerce").fillna(0.0)
    moving_mask = moving_mask if moving_mask is not None else compute_moving_mask(df)
    mask = moving_mask.reindex(df.index).fillna(False) & (dt > 0)

    if report is not None:
        report.add(
            "pace_vs_grade:mask_moving",
            rows_in=len(df),
            rows_out=int(mask.sum()),
            reason="keep moving points (compute_moving_mask) and dt>0",
        )

    if not bool(mask.any()):
        return pd.DataFrame(columns=out_cols)

    pace_s = pace_series.reindex(df.index) if pace_series is not None else df["pace_s_per_km"]
    grade_s = grade_series.reindex(df.index) if grade_series is not None else _compute_grade_percent(df, smooth_window=DEFAULT_GRADE_SMOOTH_WINDOW)

    data = pd.DataFrame(
        {
            "grade_percent": grade_s,
            "pace_s_per_km": pace_s,
            "weight_s": dt,
        },
        index=df.index,
    )
    data = data.loc[mask]
    data["grade_percent"] = data["grade_percent"].clip(lower=-20, upper=20)
    data = data.replace([np.inf, -np.inf], np.nan).dropna(subset=["grade_percent", "pace_s_per_km", "weight_s"]) 
    data = data.loc[(data["weight_s"] > 0) & (data["pace_s_per_km"] > 0)]

    if report is not None:
        report.add(
            "pace_vs_grade:dropna",
            rows_in=int(mask.sum()),
            rows_out=len(data),
            reason="drop non-finite grade/pace/weights",
        )

    if data.empty:
        return pd.DataFrame(columns=out_cols)

    bins = np.arange(-20, 20.5, 0.5)
    data["grade_bin"] = pd.cut(
        data["grade_percent"],
        bins=bins,
        labels=False,
        include_lowest=True,
        right=True,
    )
    data = data.dropna(subset=["grade_bin"]).copy()
    if data.empty:
        return pd.DataFrame(columns=out_cols)

    rows: list[dict[str, float]] = []
    for _bin, g in data.groupby("grade_bin", sort=False):
        pace_vals = g["pace_s_per_km"].to_numpy(dtype=float)
        w = g["weight_s"].to_numpy(dtype=float)
        grade_vals = g["grade_percent"].to_numpy(dtype=float)

        time_s = float(np.nansum(w))
        n = int(np.isfinite(pace_vals).sum())
        n_eff = float(_effective_sample_size(w))

        lo = math.nan
        hi = math.nan
        clip_frac = 0.0
        if time_s >= winsor_min_time_s and n_eff >= winsor_min_n_eff:
            lo, hi = _winsorize_limits_iqr(pace_vals, w, k_iqr=winsor_k_iqr)
            if not (math.isfinite(lo) and math.isfinite(hi) and hi > lo):
                lo, hi = _winsorize_limits_mad(pace_vals, w, k_mad_sigma=winsor_k_mad_sigma)

        pace_used = pace_vals
        if math.isfinite(lo) and math.isfinite(hi) and hi > lo:
            o = (pace_vals < lo) | (pace_vals > hi)
            denom = float(np.nansum(w))
            clip_frac = float(np.nansum(w[o]) / denom) if denom > 0 else 0.0
            pace_used = np.clip(pace_vals, lo, hi)

        # Weighted stats (by time).
        q25_w = _weighted_quantile_step(pace_used, w, 0.25)
        q50_w = _weighted_quantile_step(pace_used, w, 0.50)
        q75_w = _weighted_quantile_step(pace_used, w, 0.75)
        iqr_w = float(q75_w - q25_w) if (math.isfinite(q25_w) and math.isfinite(q75_w)) else math.nan
        wmean = _weighted_mean(pace_used, w)
        wstd = _weighted_std(pace_used, w)

        # Backward-compat stats (unweighted, but after winsorization).
        finite_used = pace_used[np.isfinite(pace_used)]
        med = float(np.median(finite_used)) if finite_used.size else math.nan
        std = float(np.std(finite_used, ddof=1)) if finite_used.size >= 2 else 0.0

        grade_center = _weighted_quantile_step(grade_vals, w, 0.50)

        rows.append(
            {
                "grade_center": float(grade_center) if math.isfinite(grade_center) else math.nan,
                "pace_med_s_per_km": float(q50_w) if math.isfinite(q50_w) else float(med),
                "pace_std_s_per_km": float(std) if math.isfinite(std) else 0.0,
                "pace_n": float(n),
                "time_s_bin": float(time_s),
                "pace_mean_w_s_per_km": float(wmean),
                "pace_q25_w_s_per_km": float(q25_w),
                "pace_q50_w_s_per_km": float(q50_w),
                "pace_q75_w_s_per_km": float(q75_w),
                "pace_iqr_w_s_per_km": float(iqr_w) if math.isfinite(iqr_w) else math.nan,
                "pace_std_w_s_per_km": float(wstd),
                "pace_n_eff": float(n_eff),
                "outlier_clip_frac": float(clip_frac),
            }
        )

    out = pd.DataFrame(rows)
    if out.empty:
        return pd.DataFrame(columns=out_cols)

    # Gate low-quality bins to reduce noise.
    out = out.dropna(subset=["grade_center", "pace_med_s_per_km"]).copy()
    out = out.loc[(out["time_s_bin"] >= min_bin_time_s) & (out["pace_n_eff"] >= min_bin_n_eff)]
    out = out.sort_values("grade_center").reset_index(drop=True)
    if out.empty:
        return pd.DataFrame(columns=out_cols)

    # Fix dtypes and order.
    out["pace_n"] = out["pace_n"].astype(int)
    return out[out_cols]


def build_pace_vs_grade_plot_from_data(
    data: pd.DataFrame,
    *,
    pro_ref: pd.DataFrame | None = None,
) -> go.Figure:
    """Build the Plotly figure from compute_pace_vs_grade_data output."""

    if data is None or data.empty:
        return go.Figure()

    # Input data is in s/km. Convert to min/km for plotting.
    pace_s = data["pace_med_s_per_km"]
    pace_vals = pace_s / 60.0
    pace_custom = pace_s.apply(lambda v: seconds_to_mmss(float(v)) if v == v else "-")

    q25 = data["pace_q25_w_s_per_km"] if "pace_q25_w_s_per_km" in data.columns else None
    q75 = data["pace_q75_w_s_per_km"] if "pace_q75_w_s_per_km" in data.columns else None
    band_upper = None
    band_lower = None
    band_name = None
    if q25 is not None and q75 is not None and q25.notna().any() and q75.notna().any():
        band_lower = (q25 / 60.0).clip(lower=0)
        band_upper = (q75 / 60.0).clip(lower=0)
        band_name = "P25-P75"
    else:
        std_s = data["pace_std_s_per_km"] if "pace_std_s_per_km" in data.columns else None
        if std_s is not None and std_s.notna().any():
            band_upper = ((pace_s + std_s) / 60.0).clip(lower=0)
            band_lower = ((pace_s - std_s) / 60.0).clip(lower=0)
            band_name = "+/- 1 ecart-type"

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

    if band_upper is not None and band_lower is not None and band_name is not None:
        fig.add_trace(
            go.Scatter(
                x=pd.concat([data["grade_center"], data["grade_center"][::-1]]),
                y=pd.concat([band_upper, band_lower[::-1]]),
                fill="toself",
                fillcolor="rgba(76,120,168,0.18)",
                line=dict(color="rgba(0,0,0,0)"),
                name=band_name,
                hoverinfo="skip",
            )
        )
    fig.add_trace(
        go.Scatter(
            x=data["grade_center"],
            y=pace_vals,
            mode="lines",
            line=dict(color="#4c78a8"),
            name="Allure vs pente (lissee)",
            customdata=pace_custom,
            hovertemplate="Pente: %{x:.1f} %<br>Allure mediane: %{customdata} / km<extra></extra>",
        )
    )

    tick_parts: list[pd.Series] = [pace_vals]
    if band_upper is not None:
        tick_parts.append(band_upper)
    if band_lower is not None:
        tick_parts.append(band_lower)
    if pro_ref is not None and (not pro_ref.empty) and ("pace_s_per_km_pro" in pro_ref):
        tick_parts.append(pro_ref["pace_s_per_km_pro"] / 60.0)

    pace_for_ticks = pd.concat(tick_parts)
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
    df: pd.DataFrame,
    pace_series: pd.Series | None = None,
    grade_series: pd.Series | None = None,
    moving_mask: pd.Series | None = None,
    *,
    pro_ref: pd.DataFrame | None = None,
) -> go.Figure:
    """Courbe allure (min/km) en fonction de la pente (%) lissee par binning."""

    data = compute_pace_vs_grade_data(
        df,
        pace_series=pace_series,
        grade_series=grade_series,
        moving_mask=moving_mask,
    )
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
    """Détecte les montées de façon robuste (fenêtre de distance + hystérésis + gap bridging).

    Contrat (API): retourne une liste de dicts avec les mêmes champs qu'historiquement:
    - distance_km, elevation_gain_m, avg_grade_percent, pace_s_per_km, vam_m_h,
      start_idx, end_idx, distance_m_end.

    Principe:
    - On construit une grille de distance régulière (step_m) et on interpole elevation et moving_time dessus.
    - La pente est calculée sur une fenêtre de distance (grade_window_m) pour limiter le bruit.
    - Détection via machine d'état:
      - start: grade >= start_grade_percent (min_grade) sur une distance minimale (start_confirm_distance_m)
      - continue: grade >= continue_grade_percent
      - gap: tolère un replat si grade >= gap_grade_percent tant que gap <= (gap_max_distance_m / gap_max_time_s)
      - stop: gap trop long ou descente nette (grade <= stop_down_grade_percent sur stop_down_distance_m)
    - Les métriques sont calculées sur le segment complet (incluant les replats tolérés).
    """

    if df.empty:
        return []
    required = {"distance_m", "delta_distance_m", "elevation", "delta_time_s", "pace_s_per_km"}
    if not required.issubset(set(df.columns)):
        return []

    # Tunables (conservative defaults).
    step_m = 5.0
    grade_window_m = 50.0
    elev_smooth_window_m = 25.0

    start_grade_percent = float(min_grade)
    continue_grade_percent = 1.0
    gap_grade_percent = 0.2
    gap_max_distance_m = 120.0
    gap_max_time_s = 30.0
    stop_down_grade_percent = -1.0
    stop_down_distance_m = 30.0
    start_confirm_distance_m = 20.0

    min_gain_m = 15.0
    min_duration_s = 45.0
    min_distance_m = float(min_distance_m)

    # Prepare arrays on original index order (keep start_idx/end_idx semantics stable).
    distance_m = pd.to_numeric(df["distance_m"], errors="coerce").fillna(0.0).astype(float)
    distance_m = distance_m.cummax()  # ensure non-decreasing
    delta_d = pd.to_numeric(df["delta_distance_m"], errors="coerce").fillna(0.0).astype(float)
    delta_t = pd.to_numeric(df["delta_time_s"], errors="coerce").fillna(0.0).astype(float)
    elev = pd.to_numeric(df["elevation"], errors="coerce").ffill().bfill().astype(float)
    pace = pd.to_numeric(df["pace_s_per_km"], errors="coerce").astype(float)

    # Moving time as a function of distance (injective even with pauses).
    moving = (delta_t > 0) & (delta_d > 0.5)
    moving_time_s = delta_t.where(moving, 0.0).cumsum()

    # Use grade_series if provided (already in %). Else compute robust grade from elevation.
    # For the detection, we always operate on the resampled grade (distance-windowed) for stability.
    base_grade = grade_series.reindex(df.index) if grade_series is not None else None

    def _unique_xy(x: pd.Series, y: pd.Series) -> tuple[np.ndarray, np.ndarray]:
        tmp = pd.DataFrame({"x": x.to_numpy(dtype=float), "y": y.to_numpy(dtype=float)})
        tmp = tmp.dropna().groupby("x", as_index=False).last()
        return tmp["x"].to_numpy(dtype=float), tmp["y"].to_numpy(dtype=float)

    dist_x, elev_y = _unique_xy(distance_m, elev)
    if dist_x.size < 2:
        return []
    _, time_y = _unique_xy(distance_m, moving_time_s)

    d0 = float(dist_x[0])
    d1 = float(dist_x[-1])
    if not (math.isfinite(d0) and math.isfinite(d1) and d1 > d0):
        return []

    step_m = float(step_m)
    grid = np.arange(d0, d1 + step_m, step_m)
    if grid.size < 2:
        return []

    elev_grid = np.interp(grid, dist_x, elev_y)
    time_grid = np.interp(grid, dist_x, time_y)

    # Optional: if grade_series is provided, we can interpolate it to the grid and smooth similarly.
    if base_grade is not None:
        dist_g, grade_g = _unique_xy(distance_m, pd.to_numeric(base_grade, errors="coerce"))
        grade_grid_raw = np.interp(grid, dist_g, grade_g) if dist_g.size >= 2 else np.full_like(grid, np.nan)
    else:
        grade_grid_raw = np.full_like(grid, np.nan)

    # Smooth elevation on a distance window.
    smooth_pts = max(1, int(round(elev_smooth_window_m / step_m)))
    elev_smooth = pd.Series(elev_grid).rolling(window=smooth_pts, center=True, min_periods=1).mean().to_numpy(dtype=float)

    # Compute robust grade using a distance lag.
    lag_pts = max(1, int(round(grade_window_m / step_m)))
    grade_grid = np.full_like(elev_smooth, np.nan, dtype=float)
    if lag_pts < elev_smooth.size:
        de = elev_smooth[lag_pts:] - elev_smooth[:-lag_pts]
        grade_grid[lag_pts:] = (de / float(grade_window_m)) * 100.0

    # If grade_series was provided, blend it lightly only where our computed grade is NaN.
    if np.isfinite(grade_grid_raw).any():
        missing = ~np.isfinite(grade_grid)
        grade_grid = np.where(missing, grade_grid_raw, grade_grid)

    # State machine over the grid.
    segments: list[tuple[int, int]] = []
    in_seg = False
    seg_start = 0
    start_run_m = 0.0
    gap_m = 0.0
    gap_t = 0.0
    downhill_m = 0.0
    last_ok = 0
    downhill_start = 0

    for i in range(len(grid)):
        g = grade_grid[i]
        if not math.isfinite(g):
            # Treat as a gap point.
            if in_seg:
                gap_m += step_m
                gap_t += float(time_grid[i] - time_grid[i - 1]) if i > 0 else 0.0
                if gap_m > gap_max_distance_m or gap_t > gap_max_time_s:
                    end = int(last_ok)
                    if end > seg_start:
                        segments.append((seg_start, end))
                    in_seg = False
                    start_run_m = 0.0
                continue
            start_run_m = 0.0
            continue

        if not in_seg:
            if g >= start_grade_percent:
                start_run_m += step_m
                if start_run_m >= start_confirm_distance_m:
                    in_seg = True
                    # grade[i] is computed over a lag window; shift the segment start back so
                    # the returned segment covers the full climb onset.
                    raw_start = max(0, i - int(round(start_run_m / step_m)) + 1)
                    seg_start = max(0, raw_start - lag_pts)
                    last_ok = i
                    gap_m = 0.0
                    gap_t = 0.0
                    downhill_m = 0.0
                    downhill_start = i
            else:
                start_run_m = 0.0
            continue

        # in segment
        if g <= stop_down_grade_percent:
            if downhill_m == 0.0:
                downhill_start = i
            downhill_m += step_m
        else:
            downhill_m = 0.0

        if downhill_m >= stop_down_distance_m:
            end = int(downhill_start - 1)
            if end > seg_start:
                segments.append((seg_start, end))
            in_seg = False
            start_run_m = 0.0
            gap_m = 0.0
            gap_t = 0.0
            downhill_m = 0.0
            continue

        if g >= continue_grade_percent:
            gap_m = 0.0
            gap_t = 0.0
            last_ok = i
            continue

        if g >= gap_grade_percent:
            gap_m += step_m
            gap_t += float(time_grid[i] - time_grid[i - 1]) if i > 0 else 0.0
            last_ok = i
            continue

        # g < gap_grade_percent
        gap_m += step_m
        gap_t += float(time_grid[i] - time_grid[i - 1]) if i > 0 else 0.0
        if gap_m > gap_max_distance_m or gap_t > gap_max_time_s:
            end = int(last_ok)
            if end > seg_start:
                segments.append((seg_start, end))
            in_seg = False
            start_run_m = 0.0
            gap_m = 0.0
            gap_t = 0.0
            downhill_m = 0.0

    if in_seg:
        end = int(last_ok)
        if end > seg_start:
            segments.append((seg_start, end))

    if not segments:
        return []

    # Build output items from segments.
    dist_arr = distance_m.to_numpy(dtype=float)
    time_arr = moving_time_s.to_numpy(dtype=float)
    pace_arr = pace.to_numpy(dtype=float)

    climbs: list[dict[str, float | int]] = []
    for gs, ge in segments:
        seg_start_m = float(grid[gs])
        seg_end_m = float(grid[ge])
        if not (math.isfinite(seg_start_m) and math.isfinite(seg_end_m) and seg_end_m > seg_start_m):
            continue

        start_idx = int(np.searchsorted(dist_arr, seg_start_m, side="left"))
        end_idx = int(np.searchsorted(dist_arr, seg_end_m, side="right") - 1)
        start_idx = max(0, min(start_idx, len(df) - 1))
        end_idx = max(0, min(end_idx, len(df) - 1))
        if end_idx <= start_idx:
            continue

        seg_dist_m = float(dist_arr[end_idx] - dist_arr[start_idx])
        if not math.isfinite(seg_dist_m) or seg_dist_m < min_distance_m:
            continue

        seg_time_s = float(time_arr[end_idx] - time_arr[start_idx])
        if not math.isfinite(seg_time_s) or seg_time_s < min_duration_s:
            continue

        # Gain from smoothed elevation on the grid for robustness.
        seg_elev = elev_smooth[gs : ge + 1]
        if seg_elev.size < 2:
            continue
        gain_m = float(np.clip(np.diff(seg_elev), 0, None).sum())
        if not math.isfinite(gain_m) or gain_m < min_gain_m:
            continue

        avg_grade = (gain_m / seg_dist_m) * 100.0 if seg_dist_m > 0 else math.nan
        vam = (gain_m / seg_time_s) * 3600.0 if seg_time_s > 0 else math.nan

        seg_pace = pace_arr[start_idx : end_idx + 1]
        seg_pace = seg_pace[np.isfinite(seg_pace) & (seg_pace > 0)]
        pace_med = float(np.median(seg_pace)) if seg_pace.size else math.nan

        climbs.append(
            {
                "start_idx": int(start_idx),
                "end_idx": int(end_idx),
                "distance_km": float(seg_dist_m / 1000.0),
                "elevation_gain_m": float(gain_m),
                "avg_grade_percent": float(avg_grade) if math.isfinite(avg_grade) else math.nan,
                "vam_m_h": float(vam) if math.isfinite(vam) else math.nan,
                "pace_s_per_km": float(pace_med) if math.isfinite(pace_med) else math.nan,
                "distance_m_end": float(dist_arr[end_idx]) if math.isfinite(dist_arr[end_idx]) else math.nan,
            }
        )

    if not climbs:
        return []

    # Keep deterministic ordering: largest gain first, then earlier start.
    climbs = sorted(climbs, key=lambda c: (-float(c.get("elevation_gain_m", 0.0)), float(c.get("start_idx", 0.0))))
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
