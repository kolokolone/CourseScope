import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from core.utils import seconds_to_mmss
from core.ref_data import get_pro_pace_vs_grade_df
from core.constants import MOVING_SPEED_THRESHOLD_M_S
from core.pace_grade import compute_grade_percent, compute_pace_vs_grade_data, compute_residuals_vs_grade_data


def build_distribution_plots(
    df: pd.DataFrame, pace_series: pd.Series | None = None, grade_series: pd.Series | None = None
) -> dict[str, go.Figure]:
    """Construit des histogrammes pour l'allure et la pente."""
    figs: dict[str, go.Figure] = {}

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
        grade = compute_grade_percent(df, smooth_window=5)

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


def build_pace_grade_scatter(
    df: pd.DataFrame, pace_series: pd.Series | None = None, grade_series: pd.Series | None = None
) -> go.Figure:
    """Nuage de points allure vs pente, couleur distance (ou FC si dispo)."""
    mask = (df["speed_m_s"] > MOVING_SPEED_THRESHOLD_M_S) & (df["delta_time_s"].fillna(0) > 0)
    subset = df[mask].copy()
    if subset.empty:
        return go.Figure()
    pace = (pace_series.loc[subset.index] if pace_series is not None else subset["pace_s_per_km"]) / 60.0
    grade = grade_series.reindex(subset.index) if grade_series is not None else compute_grade_percent(subset, smooth_window=5)
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
    grade = grade_series.reindex(df.index) if grade_series is not None else compute_grade_percent(df, smooth_window=5)
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
