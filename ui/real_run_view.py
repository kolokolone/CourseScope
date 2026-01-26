import pydeck as pdk
import streamlit as st

from core.formatting import format_duration_clock
from core.metrics import format_zone_table
from core.utils import mmss_to_seconds, seconds_to_mmss
from services import real_activity_service
from services.models import RealRunParams


def _format_duration(seconds: float) -> str:
    return format_duration_clock(seconds)


@st.cache_data(show_spinner=False)
def _get_cached_base(df):
    return real_activity_service.prepare_base(df)


@st.cache_data(show_spinner=False)
def _get_garmin_stats(
    df,
    moving_mask,
    gap_series,
    grade_series,
    hr_max,
    hr_rest,
    use_hrr,
    pace_threshold_s_per_km,
    ftp_w,
    cadence_target,
    use_moving_time,
):
    params = RealRunParams(
        use_moving_time=bool(use_moving_time),
        hr_max=float(hr_max) if hr_max is not None else None,
        hr_rest=float(hr_rest) if hr_rest is not None else None,
        use_hrr=bool(use_hrr),
        pace_threshold_s_per_km=float(pace_threshold_s_per_km) if pace_threshold_s_per_km is not None else None,
        ftp_w=float(ftp_w) if ftp_w is not None else None,
        cadence_target=float(cadence_target) if cadence_target is not None else None,
    )
    return real_activity_service.compute_garmin_stats(
        df,
        moving_mask=moving_mask,
        gap_series=gap_series,
        grade_series=grade_series,
        params=params,
    )


def render(df) -> None:
    st.header("Donnees de la course realisee")

    base = _get_cached_base(df)
    grade_series = base.derived.grade_series
    moving_mask = base.derived.moving_mask
    gap_series = base.derived.gap_series

    stats = base.summary
    col1, col2, col3 = st.columns(3)
    col1.metric("Distance", f"{stats['distance_km']:.2f} km")
    col2.metric("Temps total", _format_duration(stats["total_time_s"]))
    col3.metric("Temps en mouvement", _format_duration(stats["moving_time_s"]))

    col4, col5, col6 = st.columns(3)
    avg_pace = (
        seconds_to_mmss(stats["average_pace_s_per_km"])
        if stats["average_pace_s_per_km"] == stats["average_pace_s_per_km"]
        else "-"
    )
    avg_speed = (
        f"{stats['average_speed_kmh']:.1f} km/h"
        if stats["average_speed_kmh"] == stats["average_speed_kmh"]
        else "-"
    )
    col4.metric("Allure moyenne", avg_pace)
    col5.metric("Vitesse moyenne", avg_speed)
    col6.metric("D+ cumule", f"{stats['elevation_gain_m']:.0f} m")

    st.subheader("Résumé Garmin")
    use_moving_time = st.toggle(
        "Stats en temps de mouvement",
        value=True,
        help="Par defaut, les stats utilisent uniquement le temps en mouvement.",
    )

    defaults = base.zone_defaults
    hr_max = None
    hr_rest = None
    use_hrr = False
    pace_threshold_s_per_km = None
    ftp_w = None
    cadence_target = None

    with st.expander("Paramètres zones", expanded=False):
        col_z1, col_z2, col_z3 = st.columns(3)
        if defaults["hr_available"]:
            hr_default = defaults["hr_max"] if defaults["hr_max"] == defaults["hr_max"] else 190.0
            hr_max = col_z1.number_input(
                "FC max (bpm)",
                min_value=100,
                max_value=230,
                value=int(hr_default),
            )
            hr_rest = col_z1.number_input(
                "FC repos (bpm)",
                min_value=30,
                max_value=100,
                value=60,
            )
            use_hrr = col_z1.checkbox("Utiliser la réserve FC (HRR)", value=False)
        else:
            col_z1.caption("FC non disponible dans ce GPX.")

        default_pace = (
            seconds_to_mmss(defaults["pace_threshold_s_per_km"])
            if defaults["pace_threshold_s_per_km"] == defaults["pace_threshold_s_per_km"]
            else ""
        )
        pace_input = col_z2.text_input("Allure seuil (mm:ss/km)", value=default_pace)
        if pace_input:
            try:
                pace_threshold_s_per_km = float(mmss_to_seconds(pace_input))
            except ValueError:
                col_z2.warning("Format attendu M:SS (ex: 4:30).")
                pace_threshold_s_per_km = (
                    defaults["pace_threshold_s_per_km"]
                    if defaults["pace_threshold_s_per_km"] == defaults["pace_threshold_s_per_km"]
                    else None
                )
        else:
            pace_threshold_s_per_km = (
                defaults["pace_threshold_s_per_km"]
                if defaults["pace_threshold_s_per_km"] == defaults["pace_threshold_s_per_km"]
                else None
            )

        if defaults["power_available"]:
            ftp_default = defaults["ftp_w"] if defaults["ftp_w"] == defaults["ftp_w"] else 250.0
            ftp_w = col_z3.number_input(
                "FTP (W)",
                min_value=100,
                max_value=600,
                value=int(ftp_default),
            )
            if defaults["ftp_estimated"]:
                col_z3.caption("FTP estime a partir des donnees.")
        else:
            col_z3.caption("Puissance non disponible dans ce GPX.")

        if defaults["cadence_available"]:
            cad_default = defaults["cadence_target"] if defaults["cadence_target"] == defaults["cadence_target"] else 170.0
            cadence_target = col_z3.number_input(
                "Cadence cible (spm)",
                min_value=120,
                max_value=220,
                value=int(cad_default),
            )

    garmin_stats = _get_garmin_stats(
        df,
        moving_mask,
        gap_series,
        grade_series,
        hr_max,
        hr_rest if use_hrr else None,
        use_hrr,
        pace_threshold_s_per_km,
        ftp_w,
        cadence_target,
        use_moving_time,
    )

    summary = garmin_stats["summary"]
    time_used = summary.get("moving_time_s") if use_moving_time else summary.get("total_time_s")
    distance_used = summary.get("moving_distance_km") if use_moving_time else summary.get("distance_km")
    pace_used = summary.get("average_pace_s_per_km")
    speed_used = summary.get("average_speed_kmh")

    col_g1, col_g2, col_g3, col_g4 = st.columns(4)
    col_g1.metric("Temps utilise", _format_duration(time_used) if time_used == time_used else "-")
    col_g2.metric("Distance", f"{distance_used:.2f} km" if distance_used == distance_used else "-")
    col_g3.metric("Allure moyenne", seconds_to_mmss(pace_used) if pace_used == pace_used else "-")
    col_g4.metric("Vitesse moyenne", f"{speed_used:.1f} km/h" if speed_used == speed_used else "-")

    extra_metrics = []
    if summary.get("max_speed_kmh") == summary.get("max_speed_kmh"):
        extra_metrics.append(("Vitesse max", f"{summary['max_speed_kmh']:.1f} km/h"))
    if summary.get("best_pace_s_per_km") == summary.get("best_pace_s_per_km"):
        extra_metrics.append(("Best pace", seconds_to_mmss(summary["best_pace_s_per_km"])))

    if summary.get("pace_median_s_per_km") == summary.get("pace_median_s_per_km"):
        extra_metrics.append(("Allure mediane", seconds_to_mmss(summary["pace_median_s_per_km"])))
    if summary.get("pace_p10_s_per_km") == summary.get("pace_p10_s_per_km"):
        extra_metrics.append(("Allure p10", seconds_to_mmss(summary["pace_p10_s_per_km"])))
    if summary.get("pace_p90_s_per_km") == summary.get("pace_p90_s_per_km"):
        extra_metrics.append(("Allure p90", seconds_to_mmss(summary["pace_p90_s_per_km"])))

    if summary.get("gap_mean_s_per_km") == summary.get("gap_mean_s_per_km"):
        extra_metrics.append(("GAP moyen", seconds_to_mmss(summary["gap_mean_s_per_km"])))
    if summary.get("elevation_gain_m") == summary.get("elevation_gain_m"):
        extra_metrics.append(("D+", f"{summary['elevation_gain_m']:.0f} m"))
    if summary.get("elevation_loss_m") == summary.get("elevation_loss_m"):
        extra_metrics.append(("D-", f"{summary['elevation_loss_m']:.0f} m"))

    elev_min = summary.get("elevation_min_m")
    elev_max = summary.get("elevation_max_m")
    if elev_min == elev_min and elev_max == elev_max:
        extra_metrics.append(("Altitude min/max", f"{elev_min:.0f} / {elev_max:.0f} m"))
    elif elev_min == elev_min:
        extra_metrics.append(("Altitude min", f"{elev_min:.0f} m"))
    elif elev_max == elev_max:
        extra_metrics.append(("Altitude max", f"{elev_max:.0f} m"))

    grade_mean = summary.get("grade_mean_pct")
    grade_min = summary.get("grade_min_pct")
    grade_max = summary.get("grade_max_pct")
    if grade_mean == grade_mean:
        extra_metrics.append(("Pente moyenne", f"{grade_mean:.1f} %"))
    if grade_min == grade_min and grade_max == grade_max:
        extra_metrics.append(("Pente min/max", f"{grade_min:.1f} / {grade_max:.1f} %"))

    if summary.get("vam_m_h") == summary.get("vam_m_h"):
        extra_metrics.append(("VAM", f"{summary['vam_m_h']:.0f} m/h"))

    if summary.get("steps_total") == summary.get("steps_total"):
        extra_metrics.append(("Pas totaux", f"{summary['steps_total']:.0f}"))
    if summary.get("step_length_est_m") == summary.get("step_length_est_m"):
        extra_metrics.append(("Longueur pas (est.)", f"{summary['step_length_est_m']:.2f} m"))

    hr_stats = garmin_stats.get("heart_rate")
    if hr_stats:
        if hr_stats["mean_bpm"] == hr_stats["mean_bpm"]:
            extra_metrics.append(("FC moyenne", f"{hr_stats['mean_bpm']:.0f} bpm"))
        if hr_stats["max_bpm"] == hr_stats["max_bpm"]:
            extra_metrics.append(("FC max", f"{hr_stats['max_bpm']:.0f} bpm"))

    cad_stats = garmin_stats.get("cadence")
    if cad_stats:
        if cad_stats["mean_spm"] == cad_stats["mean_spm"]:
            extra_metrics.append(("Cadence moyenne", f"{cad_stats['mean_spm']:.0f} spm"))
        if cad_stats["max_spm"] == cad_stats["max_spm"]:
            extra_metrics.append(("Cadence max", f"{cad_stats['max_spm']:.0f} spm"))

    power_stats = garmin_stats.get("power")
    if power_stats:
        if power_stats["mean_w"] == power_stats["mean_w"]:
            extra_metrics.append(("Puissance moyenne", f"{power_stats['mean_w']:.0f} W"))
        if power_stats["max_w"] == power_stats["max_w"]:
            extra_metrics.append(("Puissance max", f"{power_stats['max_w']:.0f} W"))

    for i in range(0, len(extra_metrics), 4):
        cols = st.columns(min(4, len(extra_metrics) - i))
        for col, (label, value) in zip(cols, extra_metrics[i : i + 4]):
            col.metric(label, value)

    pacing = garmin_stats.get("pacing", {})
    pace_delta = pacing.get("pace_delta_s_per_km")
    negative_split = "Oui" if pace_delta == pace_delta and pace_delta < 0 else "Non"
    pace_delta_display = f"{pace_delta:+.0f} s/km" if pace_delta == pace_delta else "-"
    drift_display = (
        f"{pacing.get('drift_s_per_km_per_km'):+.1f} s/km/km"
        if pacing.get("drift_s_per_km_per_km") == pacing.get("drift_s_per_km_per_km")
        else "-"
    )
    stability_display = "-"
    if pacing.get("stability_cv") == pacing.get("stability_cv"):
        stability_display = f"CV {pacing['stability_cv']*100:.1f}%"
        if pacing.get("stability_iqr_ratio") == pacing.get("stability_iqr_ratio"):
            stability_display += f" | IQR {pacing['stability_iqr_ratio']*100:.1f}%"

    def _drift_label(value: float) -> str:
        if value != value:
            return "-"
        abs_val = abs(value)
        if abs_val < 5:
            return "stable"
        if abs_val < 10:
            return "modéré"
        return "élevé"

    cardiac_drift_split = pacing.get("cardiac_drift_pct")
    cardiac_drift_slope = pacing.get("cardiac_drift_slope_pct")
    cardiac_split_display = (
        f"{cardiac_drift_split:+.1f}% ({_drift_label(cardiac_drift_split)})"
        if cardiac_drift_split == cardiac_drift_split
        else "-"
    )
    cardiac_slope_display = (
        f"{cardiac_drift_slope:+.1f}% ({_drift_label(cardiac_drift_slope)})"
        if cardiac_drift_slope == cardiac_drift_slope
        else "-"
    )

    col_p1, col_p2, col_p3 = st.columns(3)
    col_p1.metric("Negative split", f"{negative_split} ({pace_delta_display})")
    col_p2.metric("Dérive allure", drift_display)
    col_p3.metric("Stabilité allure", stability_display)

    col_c1, col_c2 = st.columns(2)
    col_c1.metric("Dérive cardiaque (split)", cardiac_split_display)
    col_c2.metric("Dérive cardiaque (pente)", cardiac_slope_display)

    zone_pace = garmin_stats.get("pace_zones")
    if hr_stats and hr_stats.get("zones") is not None:
        with st.expander("Zones FC", expanded=False):
            st.dataframe(format_zone_table(hr_stats["zones"]), width="stretch", hide_index=True)
    if zone_pace is not None:
        with st.expander("Zones allure", expanded=False):
            threshold = pacing.get("pace_threshold_s_per_km")
            if threshold == threshold:
                st.caption(f"Seuil utilise : {seconds_to_mmss(threshold)} / km")
            st.dataframe(format_zone_table(zone_pace), width="stretch", hide_index=True)
    if power_stats and power_stats.get("zones") is not None:
        with st.expander("Zones puissance", expanded=False):
            if power_stats.get("ftp_w") == power_stats.get("ftp_w"):
                ftp_note = " (estime)" if power_stats.get("ftp_estimated") else ""
                st.caption(f"FTP utilise : {power_stats['ftp_w']:.0f} W{ftp_note}")
            st.dataframe(format_zone_table(power_stats["zones"]), width="stretch", hide_index=True)

    running_dynamics = garmin_stats.get("running_dynamics")
    if running_dynamics and any(
        running_dynamics.get(k) == running_dynamics.get(k)
        for k in [
            "stride_length_mean_m",
            "vertical_oscillation_mean_cm",
            "vertical_ratio_mean_pct",
            "ground_contact_time_mean_ms",
            "gct_balance_mean_pct",
        ]
    ):
        with st.expander("Running dynamics", expanded=False):
            cols_rd1, cols_rd2, cols_rd3 = st.columns(3)
            sl = running_dynamics.get("stride_length_mean_m")
            vo = running_dynamics.get("vertical_oscillation_mean_cm")
            vr = running_dynamics.get("vertical_ratio_mean_pct")
            cols_rd1.metric("Stride length", f"{sl:.2f} m" if sl == sl else "-")
            cols_rd2.metric("Vertical oscillation", f"{vo:.1f} cm" if vo == vo else "-")
            cols_rd3.metric("Vertical ratio", f"{vr:.1f} %" if vr == vr else "-")

            cols_rd4, cols_rd5 = st.columns(2)
            gct = running_dynamics.get("ground_contact_time_mean_ms")
            bal = running_dynamics.get("gct_balance_mean_pct")
            cols_rd4.metric("Ground contact time", f"{gct:.0f} ms" if gct == gct else "-")
            cols_rd5.metric("GCT balance", f"{bal:.1f} %" if bal == bal else "-")

    power_adv = garmin_stats.get("power_advanced")
    if power_adv and any(power_adv.get(k) == power_adv.get(k) for k in ["normalized_power_w", "tss"]):
        with st.expander("Puissance avancée", expanded=False):
            np_w = power_adv.get("normalized_power_w")
            if_val = power_adv.get("intensity_factor")
            tss = power_adv.get("tss")
            col_pa1, col_pa2, col_pa3 = st.columns(3)
            col_pa1.metric("NP", f"{np_w:.0f} W" if np_w == np_w else "-")
            col_pa2.metric("IF", f"{if_val:.2f}" if if_val == if_val else "-")
            col_pa3.metric("TSS", f"{tss:.0f}" if tss == tss else "-")

    best_df = base.best_efforts
    climb_markers = base.climbs
    highlights = real_activity_service.build_highlights(best_df, climb_markers, summary)
    if highlights:
        st.subheader("Highlights")
        st.markdown("\n".join(f"- {item}" for item in highlights))

    # Carte enrichie juste apres les metriques
    st.subheader("Carte enrichie (allure/pente/GAP)")
    map_df = df[["lat", "lon", "distance_m"]].dropna().copy()
    if map_df.empty:
        st.info("Pas de coordonnees pour afficher la carte.")
    else:
        color_mode_top = st.radio(
            "Colorer la trace par",
            options=["Allure (min/km)", "Pente (%)", "GAP (min/km equiv. plat)"],
            horizontal=True,
            key="color_mode_top",
        )

        map_color_mode = "pace"
        if color_mode_top == "Pente (%)":
            map_color_mode = "grade"
        elif color_mode_top == "GAP (min/km equiv. plat)":
            map_color_mode = "gap"

        map_payload = real_activity_service.build_map_payload(
            df,
            derived=base.derived,
            climbs=climb_markers,
            pauses=base.pauses,
            map_color_mode=map_color_mode,
        )
        map_df = map_payload.map_df

        base_layer = pdk.Layer(
            "PathLayer",
            [
                {
                    "path": map_df[["lon", "lat"]].values.tolist(),
                    "name": "Trace GPX",
                    "color": [180, 180, 180],
                }
            ],
            get_path="path",
            get_color="color",
            width_scale=3,
            width_min_pixels=1,
        )

        color_layer = pdk.Layer(
            "ScatterplotLayer",
            data=map_df,
            get_position="[lon, lat]",
            get_fill_color="color",
            get_radius=8,
            pickable=True,
        )

        climb_layer = (
            pdk.Layer(
                "ScatterplotLayer",
                data=map_payload.climb_points,
                get_position="[lon, lat]",
                get_fill_color=[200, 60, 60, 200],
                get_radius=30,
                pickable=True,
            )
            if map_payload.climb_points
            else None
        )

        pause_markers = map_payload.pause_points
        pause_layer = (
            pdk.Layer(
                "ScatterplotLayer",
                data=pause_markers,
                get_position="[lon, lat]",
                get_fill_color=[255, 200, 0, 200],
                get_radius=25,
                pickable=True,
            )
            if pause_markers
            else None
        )

        layers = [base_layer, color_layer]
        if climb_layer:
            layers.append(climb_layer)
        if pause_layer:
            layers.append(pause_layer)

        tooltip = {"html": "{label}", "style": {"fontSize": "12px"}}

        st.pydeck_chart(
            pdk.Deck(
                layers=layers,
                initial_view_state=pdk.ViewState(
                    longitude=map_df["lon"].mean(),
                    latitude=map_df["lat"].mean(),
                    zoom=12,
                    pitch=0,
                ),
                tooltip=tooltip,
            ),
            width="stretch",
        )

    # Reglages allure (temps reel vs mouvement, lissage, cap)
    st.subheader("Allure et altitude")
    pace_mode = st.radio(
        "Source du temps pour l'allure",
        options=["Temps reel (inclut pauses)", "Temps en mouvement (pauses exclues)"],
        index=0,
        horizontal=True,
        help="Temps reel = utilise tous les ecarts de temps. Temps en mouvement = ignore les pauses (vitesse < 0.5 m/s).",
    )

    pace_mode_key = "real_time" if pace_mode == "Temps reel (inclut pauses)" else "moving_time"

    col_smooth, col_cap = st.columns(2)
    with col_smooth:
        smoothing = st.slider(
            "Lissage de l'allure (nombre de points GPS)", min_value=0, max_value=50, value=20, step=1
        )

    default_cap_min = base.default_cap_min_per_km
    with col_cap:
        cap_min_per_km = st.slider(
            "Limiter l'allure max (min/km)",
            min_value=2.0,
            max_value=15.0,
            value=float(min(max(default_cap_min, 2.0), 15.0)),
            step=0.1,
            help="Les allures plus lentes que ce seuil seront tronquees pour lisser le graphique.",
        )

    pace_series = real_activity_service.compute_pace_series(
        df,
        derived=base.derived,
        pace_mode=pace_mode_key,
        smoothing_points=smoothing,
        cap_min_per_km=cap_min_per_km,
    )

    figures = real_activity_service.build_figures(
        df,
        pace_series=pace_series,
        grade_series=grade_series,
    )

    st.subheader("Allure et altitude (graphique)")
    st.plotly_chart(figures.pace_elevation, width="stretch")

    st.subheader("Splits (~1 km)")
    show_splits = st.checkbox("Afficher le tableau des splits (~1 km)", value=False)
    if show_splits:
        splits_df = base.splits
        if splits_df.empty:
            st.info("Splits indisponibles (temps manquants ou distance trop courte).")
        else:
            display_df = splits_df.copy()
            display_df["pace_min_per_km"] = display_df["pace_s_per_km"].apply(
                lambda v: seconds_to_mmss(v) if v == v else "-"
            )
            st.dataframe(
                display_df[
                    ["split_index", "distance_km", "time_s", "pace_min_per_km", "elevation_gain_m"]
                ].rename(
                    columns={
                        "split_index": "Split",
                        "distance_km": "Distance (km)",
                        "time_s": "Temps (s)",
                        "pace_min_per_km": "Allure (min/km)",
                        "elevation_gain_m": "D+ (m)",
                    }
                ),
                hide_index=True,
                width="stretch",
            )

    st.subheader("Meilleurs temps (1k, 5k, 10k, semi, marathon)")
    if best_df.empty:
        st.info("Donnees insuffisantes pour calculer les meilleurs temps.")
    else:
        display_df = best_df.copy()
        display_df["time_mmss"] = display_df["time_s"].apply(lambda v: _format_duration(v) if v == v else "-")
        display_df["pace_mmss"] = display_df["pace_s_per_km"].apply(
            lambda v: seconds_to_mmss(v) if v == v else "-"
        )
        st.dataframe(
            display_df[["distance_km", "time_mmss", "pace_mmss"]].rename(
                columns={
                    "distance_km": "Distance (km)",
                    "time_mmss": "Temps",
                    "pace_mmss": "Allure (min/km)",
                }
            ),
            hide_index=True,
            width="stretch",
        )

    st.subheader("Distributions (allure, pente)")
    figs = figures.distributions
    col_a, col_b = st.columns(2)
    if "pace" in figs:
        col_a.plotly_chart(figs["pace"], width="stretch")
    else:
        col_a.info("Pas assez de donnees d'allure pour l'histogramme.")
    if "grade" in figs:
        col_b.plotly_chart(figs["grade"], width="stretch")
    else:
        col_b.info("Pas assez de donnees de pente pour l'histogramme.")

    st.subheader("Allure en fonction de la pente")
    st.plotly_chart(figures.pace_vs_grade, width="stretch")

    st.subheader("Analyse avancee pente/allure")
    if figures.residuals_vs_grade and figures.residuals_vs_grade.data:
        st.plotly_chart(figures.residuals_vs_grade, width="stretch")
    else:
        st.info("Pas assez de donnees pour la courbe des residus.")

    col_pg1, col_pg2 = st.columns(2)
    if figures.pace_grade_scatter and figures.pace_grade_scatter.data:
        col_pg1.plotly_chart(figures.pace_grade_scatter, width="stretch")
    else:
        col_pg1.info("Pas assez de donnees pour le nuage de points.")

    if figures.pace_grade_heatmap and figures.pace_grade_heatmap.data:
        col_pg2.plotly_chart(figures.pace_grade_heatmap, width="stretch")
    else:
        col_pg2.info("Pas assez de donnees pour la heatmap.")
