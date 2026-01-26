import math
from datetime import datetime

import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st

from core.formatting import format_duration_clock, format_time_of_day
from core.parsing import parse_km_list
from core.utils import seconds_to_mmss
from services import theoretical_service


def _format_duration(seconds: float) -> str:
    return format_duration_clock(seconds)


def _format_time_of_day(value) -> str:
    return format_time_of_day(value)


def _parse_passage_distances(raw: str) -> list[float]:
    return parse_km_list(raw)


@st.cache_data(show_spinner=False)
def _get_cached_theoretical(df, base_pace_s_per_km: float):
    """Calcule et memoise le timing theorique de base et son resume."""
    return theoretical_service.prepare_base(df, base_pace_s_per_km)


def render(df) -> None:
    st.header("Données théoriques / Prévision")

    pace_default_s = int(st.session_state.get("theoretical_base_pace_s", 300))
    pace_values_s = list(range(150, 601, 5))  # 2:30 à 10:00 par pas de 5 s
    pace_labels = [seconds_to_mmss(v) for v in pace_values_s]
    default_label = seconds_to_mmss(pace_default_s)
    if default_label not in pace_labels:
        default_label = "5:00"

    selected_label = st.select_slider(
        "Allure de base (min/km)",
        options=pace_labels,
        value=default_label,
        help="Pas de 5 s. Exemple : 5:00/km.",
    )
    base_pace_s_per_km = pace_values_s[pace_labels.index(selected_label)]
    st.caption(f"Allure sélectionnée : {selected_label} / km")
    st.session_state["theoretical_base_pace_s"] = base_pace_s_per_km

    df_theoretical, summary_base = _get_cached_theoretical(df, base_pace_s_per_km)
    if df_theoretical.empty:
        st.warning("Tracé insuffisant pour calculer une prévision.")
        return
    col_base1, col_base2, col_base3, col_base4 = st.columns(4)
    col_base1.metric("Distance", f"{summary_base['total_distance_km']:.2f} km")
    col_base2.metric("Temps total théorique (base)", _format_duration(summary_base["total_time_s"]))
    col_base3.metric(
        "Allure moyenne équivalente",
        seconds_to_mmss(summary_base["average_pace_s_per_km"])
        if summary_base["average_pace_s_per_km"] == summary_base["average_pace_s_per_km"]
        else "-",
    )
    col_base4.metric("D+ cumulé", f"{summary_base['elevation_gain_m']:.0f} m")

    st.subheader("Carte (tracé théorique)")
    coords = df[["lon", "lat"]].dropna()
    if not coords.empty:
        view_state = pdk.ViewState(
            longitude=coords["lon"].mean(),
            latitude=coords["lat"].mean(),
            zoom=12,
            pitch=0,
        )
        path_data = [
            {
                "path": coords[["lon", "lat"]].values.tolist(),
                "name": "Tracé GPX",
                "color": [0, 102, 204],
            }
        ]
        layer = pdk.Layer(
            "PathLayer",
            path_data,
            get_path="path",
            get_color="color",
            width_scale=5,
            width_min_pixels=2,
        )
        st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state), width="stretch")
    else:
        st.info("Pas de coordonnées pour afficher la carte.")

    st.subheader("Allure théorique et profil altimétrique (base)")

    col_smooth, col_cap = st.columns(2)
    with col_smooth:
        smoothing = st.slider(
            "Lissage de l'allure théorique (nombre de segments)",
            min_value=0,
            max_value=50,
            value=20,
            step=1,
        )

    _, default_cap_min, cap_default_value = theoretical_service.compute_display_df(
        df_theoretical,
        smoothing_segments=smoothing,
        cap_min_per_km=None,
    )
    with col_cap:
        cap_min_per_km = st.slider(
            "Limiter l'allure théorique max (min/km)",
            min_value=2.0,
            max_value=15.0,
            value=float(cap_default_value),
            step=0.1,
            help="Les allures plus lentes que ce seuil sont tronquées uniquement pour l'affichage du graphique.",
        )

    df_display, _, _ = theoretical_service.compute_display_df(
        df_theoretical,
        smoothing_segments=smoothing,
        cap_min_per_km=cap_min_per_km,
    )

    graph_placeholder = st.empty()
    controls_placeholder = st.empty()
    passages_placeholder = st.empty()

    with controls_placeholder.container():
        st.subheader("Heure de départ et points de passage")
        use_start_time = st.checkbox(
            "Ajouter une heure de départ pour obtenir les heures de passage",
            value=st.session_state.get("use_start_time", False),
        )
        st.session_state["use_start_time"] = use_start_time

        start_datetime = None
        target_distances: list[float] = []
        passage_points_raw = st.session_state.get("theoretical_passage_points", "5,10,21.1")
        start_date_state = st.session_state.get("theoretical_start_date", datetime.now().date())
        start_time_state = st.session_state.get(
            "theoretical_start_time", datetime.now().replace(second=0, microsecond=0).time()
        )

        if use_start_time:
            col_date, col_time, col_passages = st.columns([1, 1, 2])
            start_date = col_date.date_input("Date de départ", value=start_date_state)
            start_time = col_time.time_input("Heure de départ", value=start_time_state)
            st.session_state["theoretical_start_date"] = start_date
            st.session_state["theoretical_start_time"] = start_time
            start_datetime = datetime.combine(start_date, start_time)

            passage_points_raw = col_passages.text_input(
                "Points de passage (km, séparés par des virgules)",
                value=passage_points_raw,
                help="Exemple : 5, 10, 21.1. Les points au-delà du tracé sont ignorés.",
            )
            st.session_state["theoretical_passage_points"] = passage_points_raw
            target_distances = _parse_passage_distances(passage_points_raw)

    passages = theoretical_service.compute_passages(
        df_theoretical,
        start_datetime=start_datetime if use_start_time else None,
        target_distances_km=target_distances if use_start_time else None,
    )
    df_calc = passages.df_calc
    passages_df = passages.passages

    fig_base = theoretical_service.build_base_figure(df_display, markers=passages.markers)
    graph_placeholder.plotly_chart(fig_base, width="stretch", key="theoretical_base_chart")

    if use_start_time:
        with passages_placeholder.container():
            st.subheader("Passages prévus")
            if not target_distances:
                st.info("Saisissez au moins une distance pour afficher les heures de passage.")
            elif passages_df.empty:
                st.info("Les points de passage fournis sont en dehors du tracé.")
            else:
                display_passages = passages_df.copy()
                display_passages["heure_passage"] = display_passages["passage_datetime"].apply(_format_time_of_day)
                st.dataframe(
                    display_passages[["distance_km", "heure_passage"]].rename(
                        columns={"distance_km": "Distance (km)", "heure_passage": "Heure de passage"}
                    ),
                    hide_index=True,
                    width="stretch",
                )

    st.subheader("Détails par segment (1 km)")
    show_splits = st.checkbox("Afficher le tableau des segments (~1 km)", value=False)
    if show_splits:
        splits_df = theoretical_service.compute_splits(
            df_calc, split_distance_km=1.0, start_datetime=start_datetime if use_start_time else None
        )
        if splits_df.empty:
            st.info("Tracé insuffisant pour afficher des segments.")
        else:
            display_df = splits_df.copy()
            display_df["segment_pace_min_per_km"] = display_df["pace_s_per_km"].apply(
                lambda v: seconds_to_mmss(v) if v == v else "-"
            )
            display_df["heure_passage"] = display_df["passage_datetime"].apply(_format_time_of_day)
            st.dataframe(
                display_df[
                    [
                        "split_index",
                        "distance_km_cumulative",
                        "distance_km",
                        "grade_percent_avg",
                        "segment_pace_min_per_km",
                        "time_s",
                        "cumulative_time_s",
                        "heure_passage",
                        "elevation_m",
                    ]
                ].rename(
                    columns={
                        "split_index": "Segment (km)",
                        "distance_km_cumulative": "Distance cumulée (km)",
                        "distance_km": "Distance segment (km)",
                        "grade_percent_avg": "Pente moyenne (%)",
                        "segment_pace_min_per_km": "Allure segment (min/km)",
                        "time_s": "Temps segment (s)",
                        "cumulative_time_s": "Temps cumulé (s)",
                        "heure_passage": "Heure de passage",
                        "elevation_m": "Altitude (m)",
                    }
                ),
                width="stretch",
            )

    # Simulation avancée (météo / split / hydratation)
    st.subheader("Simulation avancée (météo / split / hydratation)")

    weather_enabled = st.checkbox("Activer l'impact météo (température, humidité, vent)", value=False)
    temp_c = 15
    humidity = 60
    wind_ms = 0.0
    if weather_enabled:
        col_adj1, col_adj2, col_adj3 = st.columns(3)
        temp_c = col_adj1.slider("Température (°C)", min_value=-5, max_value=40, value=15, step=1)
        humidity = col_adj2.slider("Humidité (%)", min_value=10, max_value=100, value=60, step=5)
        wind_ms = col_adj3.slider("Vent (m/s, + = face)", min_value=-5.0, max_value=5.0, value=0.0, step=0.5)

    weather_factor = theoretical_service.compute_weather_factor(
        enabled=weather_enabled,
        temp_c=int(temp_c),
        humidity_pct=int(humidity),
        wind_ms=float(wind_ms),
    )

    col_split, col_cap_adv = st.columns(2)
    with col_split:
        split_bias = st.slider(
            "Profil de split (négatif/positif)",
            min_value=-10,
            max_value=10,
            value=0,
            step=1,
            help="0 = régulier. Valeur positive : finir plus vite (negative split). Valeur négative : partir plus vite.",
        )

    cap_adv_default = theoretical_service.compute_adv_cap_default(
        df_calc,
        weather_factor=weather_factor,
        split_bias=split_bias,
    )
    with col_cap_adv:
        cap_adv_per_km = st.slider(
            "Limiter l'allure (simulation avancée) (min/km)",
            min_value=2.0,
            max_value=15.0,
            value=float(min(max(cap_adv_default, 2.0), 15.0)),
            step=0.1,
            help="Clip des allures supérieures pour la simulation avancée (défaut = allure moyenne +40 %).",
        )
    advanced, _ = theoretical_service.compute_advanced(
        df_calc,
        weather_factor=weather_factor,
        split_bias=split_bias,
        smoothing_segments=smoothing,
        cap_adv_min_per_km=cap_adv_per_km,
    )
    st.plotly_chart(advanced.figure, width="stretch", key="theoretical_advanced_chart")

    summary_base_calc = summary_base
    summary_adjusted = advanced.summary_adjusted
    st.write(
        f"Temps ajusté : {_format_duration(summary_adjusted['total_time_s'])} "
        f"(vs {_format_duration(summary_base_calc['total_time_s'])} sans split/météo)."
    )

    st.subheader("Plan de pacing par terrain")
    st.dataframe(advanced.categories, width="stretch")

    st.download_button(
        "Exporter en CSV",
        data=advanced.csv_data,
        file_name="prevision_theorique.csv",
        mime="text/csv",
    )
