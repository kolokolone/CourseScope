from __future__ import annotations

import sys
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TESTS_DIR.parent
BACKEND_DIR = PROJECT_DIR / "backend"
GPX_PATH = TESTS_DIR / "course.gpx"
FIT_PATH = TESTS_DIR / "course.fit"

# Execution possible via: `python tests/smoke_test.py`
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))


def _require_file(path: Path) -> bytes:
    if not path.exists():
        raise SystemExit(f"Fichier de test requis manquant: {path}")
    return path.read_bytes()


def smoke_loaders() -> None:
    from services import activity_service

    gpx_bytes = _require_file(GPX_PATH)
    fit_bytes = _require_file(FIT_PATH)

    gpx = activity_service.load_activity_from_bytes(gpx_bytes, GPX_PATH.name)
    assert gpx.track_count >= 0
    assert gpx.name == GPX_PATH.name
    assert not gpx.df.empty, "DataFrame GPX vide"

    for col in [
        "stride_length_m",
        "vertical_oscillation_cm",
        "vertical_ratio_pct",
        "ground_contact_time_ms",
        "gct_balance_pct",
    ]:
        assert col in gpx.df.columns
        assert bool(gpx.df[col].isna().all()), f"La colonne GPX {col} devrait etre NaN"

    fit = activity_service.load_activity_from_bytes(fit_bytes, FIT_PATH.name)
    assert fit.track_count >= 0
    assert fit.name == FIT_PATH.name
    assert not fit.df.empty, "DataFrame FIT vide"

    for col in [
        "stride_length_m",
        "vertical_oscillation_cm",
        "vertical_ratio_pct",
        "ground_contact_time_ms",
        "gct_balance_pct",
    ]:
        assert col in fit.df.columns


def smoke_real_pipeline() -> None:
    from services import activity_service, real_activity_service
    from services.models import RealRunParams

    gpx_bytes = _require_file(GPX_PATH)
    loaded = activity_service.load_activity_from_bytes(gpx_bytes, GPX_PATH.name)
    df = loaded.df

    base = real_activity_service.prepare_base(df)
    assert not base.derived.moving_mask.empty

    garmin = real_activity_service.compute_garmin_stats(
        df,
        moving_mask=base.derived.moving_mask,
        gap_series=base.derived.gap_series,
        grade_series=base.derived.grade_series,
        params=RealRunParams(use_moving_time=True),
    )
    assert "summary" in garmin
    assert "training_load" in garmin

    summary = garmin["summary"]
    for key in [
        "max_speed_kmh",
        "best_pace_s_per_km",
        "elevation_min_m",
        "elevation_max_m",
        "grade_mean_pct",
        "grade_min_pct",
        "grade_max_pct",
        "vam_m_h",
        "steps_total",
        "step_length_est_m",
    ]:
        assert key in summary
    assert "running_dynamics" in garmin
    assert "power_advanced" in garmin

    result = real_activity_service.analyze_real_activity(df, base=base)
    assert result.best_efforts_time is not None
    assert isinstance(result.performance_predictions, list)

    cap = float(min(max(base.default_cap_min_per_km, 2.0), 15.0))
    pace_series = real_activity_service.compute_pace_series(
        df,
        derived=base.derived,
        pace_mode="real_time",
        smoothing_points=20,
        cap_min_per_km=cap,
    )
    assert len(pace_series) == len(df)

    _ = real_activity_service.build_figures(
        df,
        pace_series=pace_series,
        grade_series=base.derived.grade_series,
    )

    _ = real_activity_service.build_map_payload(
        df,
        derived=base.derived,
        climbs=base.climbs,
        pauses=base.pauses,
        map_color_mode="pace",
    )

    # Cas minimal FIT (verifie que les metriques FIT-only ne plantent pas)
    fit_bytes = _require_file(FIT_PATH)
    loaded_fit = activity_service.load_activity_from_bytes(fit_bytes, FIT_PATH.name)
    df_fit = loaded_fit.df
    base_fit = real_activity_service.prepare_base(df_fit)
    garmin_fit = real_activity_service.compute_garmin_stats(
        df_fit,
        moving_mask=base_fit.derived.moving_mask,
        gap_series=base_fit.derived.gap_series,
        grade_series=base_fit.derived.grade_series,
        params=RealRunParams(use_moving_time=True),
    )
    assert "summary" in garmin_fit
    assert "running_dynamics" in garmin_fit
    assert "power_advanced" in garmin_fit
    if garmin_fit.get("power_advanced") is not None:
        assert "power_duration_curve" in garmin_fit["power_advanced"]


def smoke_theoretical_pipeline() -> None:
    from services import activity_service
    from services.race_planning_service import calculate_race_plan_preview

    gpx_bytes = _require_file(GPX_PATH)
    loaded = activity_service.load_activity_from_bytes(gpx_bytes, GPX_PATH.name)
    df = loaded.df

    preview = calculate_race_plan_preview(
        df,
        scenario={"name": "smoke", "objective_type": "pace", "target_value": 300.0, "slope_model": "minetti"},
    )
    assert preview["profile"]
    assert preview["totals"]["distance_km"] > 0
    assert preview["histograms"]["pace"]["complete_classes"]


def main() -> None:
    smoke_loaders()
    smoke_real_pipeline()
    smoke_theoretical_pipeline()
    print("OK")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ECHEC: {exc}", file=sys.stderr)
        raise
