import pandas as pd
import streamlit as st

from core.formatting import format_duration_compact
from services import activity_service
from services import history_service
from ui import real_run_view, theoretical_view


MAX_HISTORY = 0  # 0 = illimite; changer si besoin de borner la memoire


@st.cache_data(show_spinner=False)
def _load_activity_from_bytes(data: bytes, name: str):
    """Wrapper UI autour du backend (services.activity_service)."""

    loaded = activity_service.load_activity_from_bytes(data=data, name=name)
    return {
        "df": loaded.df,
        "gpx_type": {"type": loaded.gpx_type.type, "confidence": loaded.gpx_type.confidence},
        "name": loaded.name,
        "track_count": loaded.track_count,
    }


def _add_to_history(history: list, name: str, data: bytes, gpx_type: dict, points: int, tracks: int) -> None:
    """Wrapper UI autour du backend (services.history_service)."""

    entry = {
        "name": name,
        "data": data,
        "type": gpx_type["type"],
        "confidence": gpx_type["confidence"],
        "points": points,
        "tracks": tracks,
    }
    history_service.upsert_history(history, entry, max_items=MAX_HISTORY)


def _compute_sidebar_stats(df: pd.DataFrame) -> dict:
    """
    Calcule quelques stats simples pour affichage rapide dans la barre laterale.
    """
    stats = activity_service.compute_sidebar_stats(df)
    return {
        "distance_km": stats.distance_km,
        "elev_gain_m": stats.elev_gain_m,
        "duration_s": stats.duration_s,
        "start_time": stats.start_time,
    }


def _format_duration(seconds: float | None) -> str:
    return format_duration_compact(seconds)


def render_app() -> None:
    """Point d'entree UI principal."""
    st.set_page_config(page_title="Analyse GPX Running", layout="wide")
    st.title("Analyse et prevision GPX/FIT")
    st.write(
        "Chargez un fichier GPX ou FIT pour visualiser une course realisee ou prevoir un temps "
        "sur un trace a partir d'une allure de base."
    )

    if "gpx_history" not in st.session_state:
        st.session_state["gpx_history"] = []
    gpx_history = st.session_state["gpx_history"]

    selected_history_entry = None
    with st.sidebar:
        st.subheader("Historique fichiers (session)")
        cache_info = (
            f"Cache: {len(gpx_history)}/{MAX_HISTORY}" if MAX_HISTORY else f"Cache: {len(gpx_history)} (illimite)"
        )
        st.caption(cache_info)
        if gpx_history and st.button("Vider l'historique"):
            gpx_history.clear()
            # Compat rerun (Streamlit >=1.26 : st.rerun)
            if hasattr(st, "rerun"):
                st.rerun()
            else:
                rerun = getattr(st, "experimental_rerun", None)
                if callable(rerun):
                    rerun()
        real_hist = [h for h in gpx_history if h["type"] == "real_run"]
        theo_hist = [h for h in gpx_history if h["type"] == "theoretical_route"]
        if not gpx_history:
            st.caption("Aucun fichier recent. Les fichiers charges seront listes ici.")
        else:
            st.markdown("**Reels**")
            if real_hist:
                for idx, entry in enumerate(real_hist):
                    label = f"> {entry['name']} ({entry['points']} pts, {entry['tracks']} pistes)"
                    if st.button(label, key=f"hist_real_{idx}"):
                        selected_history_entry = entry
            else:
                st.caption("Pas encore de parcours reels.")

            st.markdown("**Theoriques**")
            if theo_hist:
                for idx, entry in enumerate(theo_hist):
                    label = f"> {entry['name']} ({entry['points']} pts, {entry['tracks']} pistes)"
                    if st.button(label, key=f"hist_theo_{idx}"):
                        selected_history_entry = entry
            else:
                st.caption("Pas encore de traces theoriques.")

    uploaded_file = st.file_uploader("Fichier GPX/FIT", type=["gpx", "fit"])

    selected_name: str | None = None
    selected_bytes: bytes | None = None
    source: str | None = None

    if selected_history_entry:
        selected_name = str(selected_history_entry["name"])
        selected_bytes = selected_history_entry["data"]
        source = "history"
    elif uploaded_file:
        selected_name = str(uploaded_file.name)
        selected_bytes = uploaded_file.getvalue()
        source = "upload"

    if not selected_bytes:
        st.info(
            "Deposez un fichier GPX ou FIT exporte de Strava/Garmin, "
            "ou rechargez un fichier depuis l'historique dans la barre laterale. "
            "Les donnees d'allure sont affichees en min/km."
        )
        return

    if selected_name is None:
        st.error("Fichier invalide: nom manquant")
        return

    try:
        loaded = _load_activity_from_bytes(selected_bytes, selected_name)
    except Exception as e:
        st.error(f"Erreur lors du chargement/analyse du fichier: {e}")
        return
    df = loaded["df"]
    gpx_type = loaded["gpx_type"]
    track_count = loaded["track_count"]

    if source == "upload":
        _add_to_history(
            gpx_history,
            name=selected_name,
            data=selected_bytes,
            gpx_type=gpx_type,
            points=len(df),
            tracks=track_count,
        )

    st.session_state["gpx_df"] = df
    st.session_state["gpx_type"] = gpx_type
    sidebar_stats = _compute_sidebar_stats(df)

    with st.sidebar:
        st.subheader("Fichier charge")
        st.caption(selected_name)
        st.text(f"Points trace : {len(df)}")
        st.text(f"Pistes : {track_count}")
        st.text(f"Type detecte : {gpx_type['type']} ({int(gpx_type['confidence']*100)} %)")
        st.text(f"Source : {'historique' if source == 'history' else 'upload'}")
        if sidebar_stats["distance_km"] is not None:
            st.text(f"Distance approx : {sidebar_stats['distance_km']:.2f} km")
        if sidebar_stats["elev_gain_m"] is not None:
            st.text(f"D+ approx : {sidebar_stats['elev_gain_m']:.0f} m")
        if sidebar_stats["duration_s"] is not None:
            st.text(f"Duree approx : {_format_duration(sidebar_stats['duration_s'])}")
        if sidebar_stats["start_time"] is not None:
            st.text(f"Depart detecte : {sidebar_stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        if gpx_type["confidence"] < 0.55:
            st.warning("Detection incertaine : verifiez l'onglet choisi.")

    default_view = (
        "Donnees de la course realisee"
        if gpx_type["type"] == "real_run"
        else "Donnees theoriques (prevision)"
    )
    choice = st.radio(
        "Choisissez la vue",
        options=["Donnees de la course realisee", "Donnees theoriques (prevision)"],
        index=0 if default_view == "Donnees de la course realisee" else 1,
        horizontal=True,
    )

    if choice == "Donnees de la course realisee":
        real_run_view.render(df)
    else:
        theoretical_view.render(df)
