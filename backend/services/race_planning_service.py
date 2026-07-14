"""Single theoretical race-planning calculation pipeline."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
import hashlib
import json
import math
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import numpy as np
import pandas as pd

from core.course_profile import CourseProfile, prepare_course_profile
from core.time_histograms import build_grade_histogram, build_pace_histogram
from services.weather import NullWeatherProvider, WeatherProvider


RACE_PLANNING_PIPELINE_VERSION = "race-planning-v5"
MINETTI_GRADE_LIMIT_PCT = 30.0
MINETTI_UPHILL_COMPRESSION_EXPONENT = 0.80
DOWNHILL_GRADE_POINTS_PCT = np.array([-30.0, -25.0, -18.0, -15.0, -12.0, -10.0, -8.0, -5.0, -3.0, 0.0])
DOWNHILL_PACE_RATIO_POINTS = np.array([1.20, 1.10, 1.00, 0.95, 0.90, 0.88, 0.90, 0.94, 0.97, 1.00])
PACE_SMOOTHING_WINDOW_M = 150.0


def minetti_cost_ratio(grade_pct: np.ndarray | float) -> np.ndarray:
    """Return Minetti's energetic cost relative to level running."""

    grade = np.clip(
        np.asarray(grade_pct, dtype=float),
        -MINETTI_GRADE_LIMIT_PCT,
        MINETTI_GRADE_LIMIT_PCT,
    ) / 100.0
    cost = (
        155.4 * grade**5
        - 30.4 * grade**4
        - 43.3 * grade**3
        + 46.3 * grade**2
        + 19.5 * grade
        + 3.6
    )
    return cost / 3.6


def minetti_pace_ratio(grade_pct: np.ndarray | float) -> np.ndarray:
    """Return the asymmetric race-instruction pace ratio.

    Uphill keeps Minetti's energetic shape with a 0.80 exponent to moderate
    excessive slowdowns. Downhill uses a continuous piecewise-linear empirical
    curve. Linear interpolation is stable and cannot introduce spline
    oscillations between the configured points.
    """

    grade = np.asarray(grade_pct, dtype=float)
    cost_ratio = minetti_cost_ratio(grade)
    uphill_ratio = np.power(
        np.maximum(cost_ratio, 0.0),
        MINETTI_UPHILL_COMPRESSION_EXPONENT,
    )
    downhill_ratio = np.interp(
        np.clip(grade, DOWNHILL_GRADE_POINTS_PCT[0], 0.0),
        DOWNHILL_GRADE_POINTS_PCT,
        DOWNHILL_PACE_RATIO_POINTS,
    )
    return np.where(grade < 0.0, downhill_ratio, uphill_ratio)


def _pace_for_base(base_pace_s_per_km: float, grades_pct: np.ndarray, model: str) -> np.ndarray:
    if model == "pro_ref":
        raise ValueError("The slope model 'pro_ref' was removed; use 'minetti'")
    if model != "minetti":
        raise ValueError(f"Unsupported slope model: {model}")
    return float(base_pace_s_per_km) * minetti_pace_ratio(grades_pct)


def _smooth_pace_by_distance(
    pace_s_per_km: np.ndarray,
    segment_distance_km: np.ndarray,
    *,
    window_m: float = PACE_SMOOTHING_WINDOW_M,
) -> np.ndarray:
    """Smooth segment pace on a metric window while preserving total time."""

    pace = np.asarray(pace_s_per_km, dtype=float)
    distances_m = np.asarray(segment_distance_km, dtype=float) * 1000.0
    if len(pace) < 3 or len(pace) != len(distances_m) or window_m <= 0:
        return pace.copy()
    if not np.all(np.isfinite(distances_m)) or np.any(distances_m <= 0):
        return pace.copy()
    segment_ends_m = np.cumsum(distances_m)
    segment_starts_m = segment_ends_m - distances_m
    midpoints_m = segment_starts_m + distances_m / 2.0
    total_distance_m = float(segment_ends_m[-1])
    if total_distance_m <= 0:
        return pace.copy()
    effective_window_m = min(float(window_m), total_distance_m)
    half_window_m = effective_window_m / 2.0
    weighted = pace * distances_m
    weighted_prefix = np.concatenate(([0.0], np.cumsum(weighted)))

    def integrated_pace_at(positions_m: np.ndarray) -> np.ndarray:
        positions = np.clip(np.asarray(positions_m, dtype=float), 0.0, total_distance_m)
        indices = np.searchsorted(segment_ends_m, positions, side="right")
        safe_indices = np.minimum(indices, len(pace) - 1)
        integrated = weighted_prefix[safe_indices] + pace[safe_indices] * (
            positions - segment_starts_m[safe_indices]
        )
        return np.where(indices >= len(pace), weighted_prefix[-1], integrated)

    window_starts_m = np.clip(
        midpoints_m - half_window_m,
        0.0,
        total_distance_m - effective_window_m,
    )
    window_ends_m = window_starts_m + effective_window_m
    smoothed = (
        integrated_pace_at(window_ends_m) - integrated_pace_at(window_starts_m)
    ) / effective_window_m
    original_time_s = float(np.sum(weighted) / 1000.0)
    smoothed_time_s = float(np.sum(smoothed * distances_m) / 1000.0)
    if original_time_s > 0 and smoothed_time_s > 0:
        smoothed *= original_time_s / smoothed_time_s
    return smoothed


def _running_time_for_base(
    base_pace_s_per_km: float,
    grades_pct: np.ndarray,
    segment_distance_km: np.ndarray,
    model: str,
) -> float:
    return float(np.sum(_pace_for_base(base_pace_s_per_km, grades_pct, model) * segment_distance_km))


def solve_base_pace_for_target_time(
    *,
    target_time_s: float,
    grades_pct: np.ndarray,
    segment_distance_km: np.ndarray,
    model: str = "minetti",
    tolerance_s: float = 0.25,
) -> float:
    """Solve the flat-equivalent pace so segment times match the target."""

    if not math.isfinite(target_time_s) or target_time_s <= 0:
        raise ValueError("target_time_s must be positive")
    low, high = 60.0, 3600.0
    low_time = _running_time_for_base(low, grades_pct, segment_distance_km, model)
    high_time = _running_time_for_base(high, grades_pct, segment_distance_km, model)
    if target_time_s < low_time - 1.0 or target_time_s > high_time + 1.0:
        raise ValueError("The requested target time is outside the supported pace range")
    for _ in range(80):
        middle = (low + high) / 2.0
        result = _running_time_for_base(middle, grades_pct, segment_distance_km, model)
        if abs(result - target_time_s) <= tolerance_s:
            return middle
        if result < target_time_s:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


def _objective_base_pace(
    objective_type: str,
    target_value: float,
    *,
    vma_kmh: float | None,
    grades_pct: np.ndarray,
    segment_distance_km: np.ndarray,
    model: str,
) -> float:
    if objective_type == "pace":
        if not 120.0 <= target_value <= 1800.0:
            raise ValueError("A pace objective must be expressed in seconds per kilometre")
        return float(target_value)
    if objective_type == "time":
        return solve_base_pace_for_target_time(
            target_time_s=float(target_value),
            grades_pct=grades_pct,
            segment_distance_km=segment_distance_km,
            model=model,
        )
    if objective_type == "effort":
        if vma_kmh is None or not math.isfinite(float(vma_kmh)) or float(vma_kmh) <= 0:
            raise ValueError("vma_kmh is required for an effort objective")
        effort_ratio = float(target_value)
        if not 0.30 <= effort_ratio <= 1.05:
            raise ValueError("An effort objective is a ratio between 0.30 and 1.05")
        return 3600.0 / (float(vma_kmh) * effort_ratio)
    raise ValueError(f"Unsupported objective type: {objective_type}")


def _cumulative_at(distance_m: np.ndarray, cumulative_s: np.ndarray, target_m: float) -> float:
    return float(np.interp(target_m, distance_m, cumulative_s))


def _stop_delay_at(stops: list[dict[str, object]], distance_km: float) -> float:
    return float(
        sum(
            float(stop.get("duration_s", 0.0) or 0.0)
            for stop in stops
            if float(stop.get("distance_km", 0.0) or 0.0) <= distance_km + 1e-9
        )
    )


def _iso_at(start: datetime | None, elapsed_s: float) -> str | None:
    return (start + timedelta(seconds=float(elapsed_s))).isoformat() if start is not None else None


def _resolve_start(plan: dict[str, object]) -> datetime | None:
    date_value = plan.get("race_date")
    time_value = plan.get("start_time")
    if not date_value or not time_value:
        return None
    timezone_name = str(plan.get("timezone") or "UTC")
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown timezone: {timezone_name}") from exc
    return datetime.combine(date.fromisoformat(str(date_value)), time.fromisoformat(str(time_value)), tzinfo=zone)


def _climbs(profile: pd.DataFrame, cumulative_running_s: np.ndarray) -> list[dict[str, object]]:
    grade = profile["grade_robust_pct"].to_numpy(dtype=float)
    distance = profile["distance_m"].to_numpy(dtype=float)
    elevation = profile["elevation_m"].to_numpy(dtype=float)
    active = grade >= 3.0
    climbs: list[dict[str, object]] = []
    start: int | None = None
    for index in range(len(active) + 1):
        on = bool(active[index]) if index < len(active) else False
        if on and start is None:
            start = index
        elif not on and start is not None:
            end = index - 1
            distance_m = float(distance[end] - distance[start])
            gain_m = float(np.clip(np.diff(elevation[start : end + 1]), 0.0, None).sum())
            if distance_m >= 150.0 and gain_m >= 15.0:
                duration = float(cumulative_running_s[end] - cumulative_running_s[start])
                climbs.append(
                    {
                        "id": f"climb-{len(climbs) + 1}",
                        "start_distance_km": float(distance[start] / 1000.0),
                        "end_distance_km": float(distance[end] / 1000.0),
                        "distance_km": distance_m / 1000.0,
                        "elevation_gain_m": gain_m,
                        "average_grade_pct": gain_m / distance_m * 100.0,
                        "running_time_s": duration,
                    }
                )
            start = None
    return climbs


def _display_indices(
    profile: pd.DataFrame,
    point_pace_s_per_km: np.ndarray | None = None,
    max_points: int = 1600,
) -> np.ndarray:
    size = len(profile)
    if size <= max_points:
        return np.arange(size, dtype=int)
    feature_count = 5 if point_pace_s_per_km is not None else 3
    bucket_size = max(2, int(math.ceil(size / max_points * feature_count)))
    selected = {0, size - 1}
    elevation = profile["elevation_m"].to_numpy(dtype=float)
    grade = profile["grade_robust_pct"].to_numpy(dtype=float)
    for begin in range(0, size, bucket_size):
        end = min(size, begin + bucket_size)
        local = slice(begin, end)
        selected.add(begin + int(np.argmin(elevation[local])))
        selected.add(begin + int(np.argmax(elevation[local])))
        selected.add(begin + int(np.argmax(np.abs(grade[local]))))
        if point_pace_s_per_km is not None:
            selected.add(begin + int(np.argmin(point_pace_s_per_km[local])))
            selected.add(begin + int(np.argmax(point_pace_s_per_km[local])))
    return np.array(sorted(selected), dtype=int)


def scenario_hash(scenario: dict[str, object], stops: list[dict[str, object]]) -> str:
    canonical = json.dumps({"scenario": scenario, "stops": stops}, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _weather_adjustment_factor(assumptions: dict[str, object] | None) -> float:
    if not assumptions:
        return 1.0
    temperature = float(assumptions.get("temperature_c", 15.0) or 15.0)
    humidity = float(assumptions.get("humidity_pct", 50.0) or 50.0)
    headwind = max(0.0, float(assumptions.get("headwind_m_s", 0.0) or 0.0))
    heat_penalty = max(0.0, temperature - 15.0) * 0.003
    humidity_penalty = max(0.0, humidity - 60.0) * 0.0005
    wind_penalty = headwind * 0.004
    return float(np.clip(1.0 + heat_penalty + humidity_penalty + wind_penalty, 0.95, 1.35))


def calculate_race_plan_preview(
    activity_df: pd.DataFrame,
    *,
    scenario: dict[str, object],
    stops: list[dict[str, object]] | None = None,
    plan: dict[str, object] | None = None,
    custom_points: list[dict[str, object]] | None = None,
    custom_segments: list[dict[str, object]] | None = None,
    weather_provider: WeatherProvider | None = None,
) -> dict[str, object]:
    """Calculate a complete preview without mutating persistent state."""

    prepared: CourseProfile = prepare_course_profile(activity_df)
    profile = prepared.dataframe
    plan_values = plan or {}
    start_datetime = _resolve_start(plan_values)
    weather_provider = weather_provider or NullWeatherProvider()
    manual_weather = scenario.get("weather_assumptions") if isinstance(scenario.get("weather_assumptions"), dict) else None
    provider_weather = None
    geo_rows = profile[np.isfinite(profile["lat"]) & np.isfinite(profile["lon"])]
    if not geo_rows.empty and start_datetime is not None:
        first_geo = geo_rows.iloc[0]
        provider_weather = weather_provider.get_forecast(latitude=float(first_geo["lat"]), longitude=float(first_geo["lon"]), at_iso=start_datetime.isoformat())
    effective_weather = provider_weather if isinstance(provider_weather, dict) else manual_weather
    weather_factor = _weather_adjustment_factor(effective_weather)
    segment_distance_km = np.diff(profile["distance_m"].to_numpy(dtype=float)) / 1000.0
    point_grades = profile["grade_robust_pct"].to_numpy(dtype=float)
    grades = (point_grades[:-1] + point_grades[1:]) / 2.0
    model = str(scenario.get("slope_model") or "minetti")
    objective_type = str(scenario.get("objective_type") or "pace")
    target_value = float(scenario.get("target_value") or 300.0)
    vma_raw = scenario.get("vma_kmh")
    vma_kmh = float(vma_raw) if vma_raw is not None else None
    calibration_factor = float(scenario.get("calibration_factor") or 1.0)
    if not 0.5 <= calibration_factor <= 2.0:
        raise ValueError("calibration_factor must be between 0.5 and 2.0")
    combined_adjustment = calibration_factor * weather_factor
    objective_target = target_value / combined_adjustment if objective_type == "time" else target_value
    base_pace = _objective_base_pace(
        objective_type,
        objective_target,
        vma_kmh=vma_kmh,
        grades_pct=grades,
        segment_distance_km=segment_distance_km,
        model=model,
    )
    segment_pace = _pace_for_base(base_pace, grades, model) * combined_adjustment
    segment_pace = _smooth_pace_by_distance(segment_pace, segment_distance_km)
    segment_time = segment_pace * segment_distance_km
    if objective_type == "time":
        # Keep the displayed series and every aggregate on the exact same
        # segment values while removing the floating-point residue globally.
        segment_pace *= target_value / float(np.sum(segment_time))
        segment_time = segment_pace * segment_distance_km
    cumulative_running = np.concatenate(([0.0], np.cumsum(segment_time)))

    total_distance_km = float(profile["distance_km"].iloc[-1])
    normalized_stops: list[dict[str, object]] = []
    for order, stop in enumerate(sorted(stops or [], key=lambda item: (float(item.get("distance_km", 0.0)), int(item.get("sort_order", 0) or 0)))):
        distance_km = float(stop.get("distance_km", 0.0))
        duration_s = float(stop.get("duration_s", 0.0))
        if not 0.0 <= distance_km <= total_distance_km:
            raise ValueError("A stop distance is outside the course")
        if duration_s < 0:
            raise ValueError("A stop duration cannot be negative")
        normalized_stops.append({**stop, "distance_km": distance_km, "duration_s": duration_s, "sort_order": order})

    distance_values = profile["distance_m"].to_numpy(dtype=float)
    cumulative_elapsed = np.array(
        [running + _stop_delay_at(normalized_stops, distance_m / 1000.0) for running, distance_m in zip(cumulative_running, distance_values)],
        dtype=float,
    )
    if np.any(np.diff(cumulative_elapsed) < -1e-9):
        raise RuntimeError("Calculated cumulative times are not monotone")

    passage_distances = list(np.arange(1.0, math.floor(total_distance_km) + 1.0, 1.0))
    if not passage_distances or passage_distances[-1] < total_distance_km - 1e-9:
        passage_distances.append(total_distance_km)
    for point in custom_points or []:
        value = float(point.get("distance_km", 0.0))
        if 0 <= value <= total_distance_km:
            passage_distances.append(value)
    passage_distances = sorted(set(round(value, 6) for value in passage_distances))
    passages = []
    for distance_km in passage_distances:
        running_s = _cumulative_at(distance_values, cumulative_running, distance_km * 1000.0)
        elapsed_s = running_s + _stop_delay_at(normalized_stops, distance_km)
        passages.append(
            {
                "distance_km": distance_km,
                "running_time_s": running_s,
                "stop_time_s": elapsed_s - running_s,
                "elapsed_time_s": elapsed_s,
                "passage_time_iso": _iso_at(start_datetime, elapsed_s),
                "elevation_m": float(np.interp(distance_km * 1000.0, distance_values, profile["elevation_m"])),
            }
        )

    splits = []
    previous_distance = 0.0
    previous_running = 0.0
    previous_elapsed = 0.0
    for passage in passages:
        distance_km = float(passage["distance_km"])
        running_s = float(passage["running_time_s"])
        elapsed_s = float(passage["elapsed_time_s"])
        split_distance = distance_km - previous_distance
        if split_distance > 0:
            split_running = running_s - previous_running
            splits.append(
                {
                    "index": len(splits) + 1,
                    "start_distance_km": previous_distance,
                    "end_distance_km": distance_km,
                    "distance_km": split_distance,
                    "running_time_s": split_running,
                    "stop_time_s": (elapsed_s - previous_elapsed) - split_running,
                    "elapsed_time_s": elapsed_s - previous_elapsed,
                    "pace_s_per_km": split_running / split_distance,
                }
            )
        previous_distance, previous_running, previous_elapsed = distance_km, running_s, elapsed_s

    climbs = _climbs(profile, cumulative_running)
    for climb in climbs:
        start_km = float(climb["start_distance_km"])
        end_km = float(climb["end_distance_km"])
        elapsed_s = _cumulative_at(distance_values, cumulative_running, end_km * 1000.0) + _stop_delay_at(normalized_stops, end_km)
        climb["arrival_time_iso"] = _iso_at(start_datetime, elapsed_s)
        climb["elapsed_time_s"] = elapsed_s

    segment_definitions = list(custom_segments or [])
    for point in custom_points or []:
        if point.get("point_type") == "custom_segment" and point.get("end_distance_km") is not None:
            segment_definitions.append({"name": point.get("label") or "Segment", "start_distance_km": point.get("distance_km"), "end_distance_km": point.get("end_distance_km"), "notes": point.get("notes")})
    segments = []
    elevation_values = profile["elevation_m"].to_numpy(dtype=float)
    for index, segment in enumerate(segment_definitions):
        start_km = float(segment.get("start_distance_km", 0.0) or 0.0)
        end_km = float(segment.get("end_distance_km", 0.0) or 0.0)
        if not (0.0 <= start_km < end_km <= total_distance_km):
            continue
        running_start = _cumulative_at(distance_values, cumulative_running, start_km * 1000.0)
        running_end = _cumulative_at(distance_values, cumulative_running, end_km * 1000.0)
        elapsed_start = running_start + _stop_delay_at(normalized_stops, start_km)
        elapsed_end = running_end + _stop_delay_at(normalized_stops, end_km)
        grid_mask = (distance_values >= start_km * 1000.0) & (distance_values <= end_km * 1000.0)
        segment_elevation = elevation_values[grid_mask]
        gain = float(np.clip(np.diff(segment_elevation), 0.0, None).sum()) if len(segment_elevation) > 1 else 0.0
        segments.append({"id": segment.get("id") or f"segment-{index + 1}", "name": segment.get("name") or "Segment", "start_distance_km": start_km, "end_distance_km": end_km, "distance_km": end_km - start_km, "running_time_s": running_end - running_start, "stop_time_s": (elapsed_end - elapsed_start) - (running_end - running_start), "elapsed_time_s": elapsed_end - elapsed_start, "pace_s_per_km": (running_end - running_start) / (end_km - start_km), "elevation_gain_m": gain, "notes": segment.get("notes")})

    point_pace = np.empty(len(profile), dtype=float)
    point_pace[0] = segment_pace[0]
    point_pace[-1] = segment_pace[-1]
    if len(point_pace) > 2:
        point_pace[1:-1] = (segment_pace[:-1] + segment_pace[1:]) / 2.0
    display_idx = _display_indices(profile, point_pace)
    display_profile = [
        {
            "distance_km": float(profile.iloc[index]["distance_km"]),
            "pace_s_per_km": float(point_pace[index]),
            "elevation_m": float(profile.iloc[index]["elevation_m"]),
            "grade_pct": float(profile.iloc[index]["grade_display_pct"]),
            "grade_robust_pct": float(profile.iloc[index]["grade_robust_pct"]),
            "elapsed_time_s": float(cumulative_elapsed[index]),
            "passage_time_iso": _iso_at(start_datetime, float(cumulative_elapsed[index])),
            "lat": float(profile.iloc[index]["lat"]) if math.isfinite(float(profile.iloc[index]["lat"])) else None,
            "lon": float(profile.iloc[index]["lon"]) if math.isfinite(float(profile.iloc[index]["lon"])) else None,
        }
        for index in display_idx
    ]

    running_time_s = float(np.sum(segment_time))
    stop_time_s = float(sum(float(stop["duration_s"]) for stop in normalized_stops))
    elapsed_time_s = running_time_s + stop_time_s
    elevation_diff = np.diff(profile["elevation_m"].to_numpy(dtype=float))
    gain_m = float(np.clip(elevation_diff, 0.0, None).sum())
    loss_m = float(-np.clip(elevation_diff, None, 0.0).sum())
    pace_histogram = build_pace_histogram(segment_pace, segment_time, base_pace)
    grade_histogram = build_grade_histogram(grades, segment_distance_km, segment_time)
    alerts = list(prepared.quality["warnings"])
    if np.any(np.abs(grades) >= 20.0):
        alerts.append({"code": "extreme_grade", "message": "Le parcours contient des pentes robustes superieures a 20 %."})
    if climbs:
        hardest = max(climbs, key=lambda item: float(item["elevation_gain_m"]))
        alerts.append({"code": "key_climb", "message": f"Ascension principale: {float(hardest['elevation_gain_m']):.0f} m D+."})

    weather: dict[str, object]
    if provider_weather is not None:
        weather = {"status": "available", "source": "provider", "data": provider_weather, "adjustment_factor": weather_factor}
    elif manual_weather is not None:
        weather = {"status": "assumptions", "source": "scenario", "data": manual_weather, "adjustment_factor": weather_factor}
    else:
        weather = {"status": "unavailable", "source": None, "data": None, "adjustment_factor": 1.0}

    strategy = [
        {
            "start_distance_km": split["start_distance_km"],
            "end_distance_km": split["end_distance_km"],
            "target_pace_s_per_km": split["pace_s_per_km"],
            "notes": None,
        }
        for split in splits
    ]
    return {
        "pipeline_version": RACE_PLANNING_PIPELINE_VERSION,
        "scenario_hash": scenario_hash(scenario, normalized_stops),
        "units": {"distance": "km", "internal_distance": "m", "elevation": "m", "pace": "s/km", "time": "s", "grade": "%"},
        "model": {
            "slope_model": "minetti",
            "minetti_grade_limit_pct": MINETTI_GRADE_LIMIT_PCT,
            "minetti_uphill_compression_exponent": MINETTI_UPHILL_COMPRESSION_EXPONENT,
            "downhill_model": "empirical_piecewise_linear",
            "pace_smoothing_window_m": PACE_SMOOTHING_WINDOW_M,
        },
        "totals": {
            "distance_km": total_distance_km,
            "elevation_gain_m": gain_m,
            "elevation_loss_m": loss_m,
            "base_pace_s_per_km": base_pace,
            "average_pace_s_per_km": running_time_s / total_distance_km,
            "running_time_s": running_time_s,
            "stop_time_s": stop_time_s,
            "elapsed_time_s": elapsed_time_s,
            "start_time_iso": start_datetime.isoformat() if start_datetime is not None else None,
            "arrival_time_iso": _iso_at(start_datetime, elapsed_time_s),
            "effort_distance_km": total_distance_km + gain_m / 100.0,
        },
        "profile": display_profile,
        "passages": passages,
        "splits": splits,
        "climbs": climbs,
        "segments": segments,
        "stops": normalized_stops,
        "histograms": {"pace": pace_histogram, "grade": grade_histogram},
        "alerts": alerts,
        "calculated_strategy": custom_segments or strategy,
        "weather": weather,
        "quality": prepared.quality,
    }
