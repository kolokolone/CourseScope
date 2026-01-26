from __future__ import annotations

import math
from datetime import datetime
from typing import Dict, Iterable

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from core.grade_table import grade_factor
from core.utils import seconds_to_mmss


def compute_theoretical_timing(
    df: pd.DataFrame, base_pace_s_per_km: float, start_datetime: datetime | None = None
) -> pd.DataFrame:
    """
    Calcule les temps théoriques sur un tracé GPX selon l'allure de base.
    Si start_datetime est fourni, ajoute une colonne d'heure de passage.
    """
    columns = [
        "distance_km_cumulative",
        "segment_distance_km",
        "segment_grade_percent",
        "segment_pace_s_per_km",
        "segment_time_s",
        "cumulative_time_s",
        "elevation_m",
    ]
    if len(df) < 2:
        result = pd.DataFrame(columns=columns)
        if not result.empty and start_datetime is not None:
            start_ts = pd.to_datetime(start_datetime)
            result["passage_datetime"] = start_ts + pd.to_timedelta(result["cumulative_time_s"], unit="s")
        return result

    dist = df["distance_m"].to_numpy()
    elev = df["elevation"].to_numpy()
    dist_current = dist[:-1]
    dist_next = dist[1:]
    segment_distance_m = dist_next - dist_current

    valid = np.isfinite(dist_current) & np.isfinite(dist_next) & (segment_distance_m > 0)
    if not valid.any():
        result = pd.DataFrame(columns=columns)
        if not result.empty and start_datetime is not None:
            start_ts = pd.to_datetime(start_datetime)
            result["passage_datetime"] = start_ts + pd.to_timedelta(result["cumulative_time_s"], unit="s")
        return result

    segment_distance_m = segment_distance_m[valid]
    segment_distance_km = segment_distance_m / 1000.0

    elev_current = elev[:-1][valid]
    elev_next = elev[1:][valid]
    delta_elev = np.where(np.isnan(elev_current) | np.isnan(elev_next), 0.0, elev_next - elev_current)

    grade_percent = (delta_elev / segment_distance_m) * 100.0
    pace_factor = grade_factor(grade_percent)
    segment_pace_s_per_km = base_pace_s_per_km * pace_factor
    segment_time_s = segment_pace_s_per_km * segment_distance_km
    cumulative_time_s = np.cumsum(segment_time_s)

    result = pd.DataFrame(
        {
            "distance_km_cumulative": dist_next[valid] / 1000.0,
            "segment_distance_km": segment_distance_km,
            "segment_grade_percent": grade_percent,
            "segment_pace_s_per_km": segment_pace_s_per_km,
            "segment_time_s": segment_time_s,
            "cumulative_time_s": cumulative_time_s,
            "elevation_m": elev_next,
        },
        columns=columns,
    )
    if not result.empty and start_datetime is not None:
        start_ts = pd.to_datetime(start_datetime)
        result["passage_datetime"] = start_ts + pd.to_timedelta(result["cumulative_time_s"], unit="s")
    return result


def compute_theoretical_splits(
    df_theoretical: pd.DataFrame, split_distance_km: float = 1.0, start_datetime: datetime | None = None
) -> pd.DataFrame:
    """
    Agrège les segments théoriques par tranches de split_distance_km (~1 km par défaut).
    """
    if df_theoretical.empty:
        return pd.DataFrame(
            columns=[
                "split_index",
                "distance_km",
                "time_s",
                "pace_s_per_km",
                "grade_percent_avg",
                "distance_km_cumulative",
                "cumulative_time_s",
                "elevation_m",
            ]
        )

    df = df_theoretical.copy()
    df["split_index"] = (df["distance_km_cumulative"] // split_distance_km).astype(int)

    splits = []
    cumulative_time_tracker = 0.0
    start_ts = pd.to_datetime(start_datetime) if start_datetime is not None else None
    for idx, group in df.groupby("split_index"):
        group = group.sort_values("distance_km_cumulative")
        distance_km = group["segment_distance_km"].sum()
        time_s = group["segment_time_s"].sum()
        pace_s_per_km = time_s / distance_km if distance_km > 0 else math.nan

        grade_percent_avg = (
            (group["segment_grade_percent"] * group["segment_distance_km"]).sum() / distance_km
            if distance_km > 0
            else math.nan
        )

        cumulative_time_tracker += time_s
        splits.append(
            {
                "split_index": int(idx + 1),
                "distance_km": distance_km,
                "time_s": time_s,
                "pace_s_per_km": pace_s_per_km,
                "grade_percent_avg": grade_percent_avg,
                "distance_km_cumulative": group["distance_km_cumulative"].iloc[-1],
                "cumulative_time_s": cumulative_time_tracker,
                "elevation_m": group["elevation_m"].iloc[-1],
                "passage_datetime": (
                    start_ts + pd.to_timedelta(cumulative_time_tracker, unit="s") if start_ts is not None else pd.NaT
                ),
            }
        )

    return pd.DataFrame(splits)


def compute_theoretical_summary(df_theoretical: pd.DataFrame) -> Dict[str, float]:
    """
    Résumé global à partir du DataFrame théorique.
    """
    if df_theoretical.empty:
        return {
            "total_time_s": 0.0,
            "total_distance_km": 0.0,
            "average_pace_s_per_km": math.nan,
            "elevation_gain_m": 0.0,
        }

    total_time_s = float(df_theoretical["cumulative_time_s"].iloc[-1])
    total_distance_km = float(df_theoretical["distance_km_cumulative"].iloc[-1])
    average_pace_s_per_km = total_time_s / total_distance_km if total_distance_km > 0 else math.nan

    elevation = df_theoretical["elevation_m"].dropna().to_numpy()
    elevation_gain_m = float(np.clip(np.diff(elevation), 0, None).sum()) if len(elevation) > 1 else 0.0

    return {
        "total_time_s": total_time_s,
        "total_distance_km": total_distance_km,
        "average_pace_s_per_km": average_pace_s_per_km,
        "elevation_gain_m": elevation_gain_m,
    }


def compute_passage_at_distances(
    df_theoretical: pd.DataFrame, distances_km: Iterable[float], start_datetime: datetime | None = None
) -> pd.DataFrame:
    """
    Interpole les temps cumulés pour une liste de distances cibles (km) et calcule l'heure de passage.
    """
    distances = [float(d) for d in distances_km if d is not None]
    if df_theoretical.empty or not distances:
        return pd.DataFrame(columns=["distance_km", "cumulative_time_s", "passage_datetime"])

    max_distance = float(df_theoretical["distance_km_cumulative"].iloc[-1])
    cleaned = [d for d in distances if d >= 0 and d <= max_distance]
    if not cleaned:
        return pd.DataFrame(columns=["distance_km", "cumulative_time_s", "passage_datetime"])

    sorted_distances = sorted(cleaned)
    interp_times = np.interp(
        sorted_distances, df_theoretical["distance_km_cumulative"], df_theoretical["cumulative_time_s"]
    )
    time_by_distance = dict(zip(sorted_distances, interp_times))

    start_ts = pd.to_datetime(start_datetime) if start_datetime is not None else None
    records = []
    for d in cleaned:
        t = float(time_by_distance[d])
        records.append(
            {
                "distance_km": float(d),
                "cumulative_time_s": t,
                "passage_datetime": start_ts + pd.to_timedelta(t, unit="s") if start_ts is not None else pd.NaT,
            }
        )

    return pd.DataFrame(records)


def build_theoretical_plot(df_theoretical: pd.DataFrame, markers=None) -> go.Figure:
    """
    Graphique allure théorique + profil altimétrique.
    """
    pace_min = df_theoretical["segment_pace_s_per_km"] / 60.0
    pace_min_clean = pace_min.dropna()
    pace_display = df_theoretical["segment_pace_s_per_km"].apply(lambda v: seconds_to_mmss(v) if v == v else "-")
    fig = go.Figure()
    # Trace baseline pour permettre un remplissage sous la courbe (axes inversés)
    fill_args = {}
    if not pace_min_clean.empty:
        y_fill_base = np.full_like(pace_min, pace_min_clean.max())
        fig.add_trace(
            go.Scatter(
                x=df_theoretical["distance_km_cumulative"],
                y=y_fill_base,
                mode="lines",
                line=dict(color="rgba(0,0,0,0)", width=0),
                showlegend=False,
                hoverinfo="skip",
            )
        )
        fill_args = dict(fill="tonexty", fillcolor="rgba(76,120,168,0.12)")

    fig.add_trace(
        go.Scatter(
            x=df_theoretical["distance_km_cumulative"],
            y=pace_min,
            mode="lines",
            name="Allure théorique (min/km)",
            line=dict(color="#4c78a8"),
            yaxis="y1",
            customdata=pace_display,
            hovertemplate="Distance: %{x:.2f} km<br>Allure: %{customdata} / km<extra></extra>",
            **fill_args,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df_theoretical["distance_km_cumulative"],
            y=df_theoretical["elevation_m"],
            mode="lines",
            name="Altitude (m)",
            line=dict(color="#f58518"),
            opacity=0.7,
            yaxis="y2",
            hovertemplate="Distance: %{x:.2f} km<br>Altitude: %{y:.0f} m<extra></extra>",
        )
    )

    pace_min = df_theoretical["segment_pace_s_per_km"] / 60.0
    pace_min_clean = pace_min.dropna()
    if not pace_min_clean.empty:
        tick_start = math.floor(pace_min_clean.min() * 2) / 2.0
        tick_end = math.ceil(pace_min_clean.max() * 2) / 2.0
        tick_step = 0.5
        tick_vals = np.arange(tick_start, tick_end + tick_step, tick_step)
        tick_text = [seconds_to_mmss(v * 60.0) for v in tick_vals]
        yaxis_cfg = dict(
            title="Allure (min/km)",
            autorange="reversed",
            tickmode="array",
            tickvals=tick_vals,
            ticktext=tick_text,
        )
    else:
        yaxis_cfg = dict(title="Allure (min/km)", autorange="reversed")

    fig.update_layout(
        xaxis=dict(
            title="Distance (km)",
            showspikes=True,
            spikemode="across",
            spikesnap="cursor",
            spikethickness=1,
            spikecolor="#999",
        ),
        yaxis=yaxis_cfg,
        yaxis2=dict(
            title="Altitude (m)",
            overlaying="y",
            side="right",
            showgrid=False,
        ),
        legend=dict(orientation="h", y=-0.2),
        margin=dict(t=40, b=40),
    )

    if markers:
        marker_x = [m["distance_km"] for m in markers]
        marker_y = [m["elevation_m"] for m in markers]
        marker_text = [m["label"] for m in markers]
        fig.add_trace(
            go.Scatter(
                x=marker_x,
                y=marker_y,
                yaxis="y2",
                mode="text",
                text=marker_text,
                textposition="top center",
                showlegend=False,
                hoverinfo="skip",
            )
        )
    return fig
