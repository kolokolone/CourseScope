"""Canonical, distance-based preparation of a theoretical course profile.

All public distances produced by the planning API are expressed in kilometres.
This module deliberately keeps metres internally so that smoothing and grade
windows do not depend on the sampling density of the imported GPX/FIT file.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
import pandas as pd


COURSE_PROFILE_VERSION = "course-profile-v2"


@dataclass(frozen=True)
class CourseProfileThresholds:
    grid_step_m: float = 10.0
    elevation_smoothing_window_m: float = 50.0
    robust_grade_window_m: float = 50.0
    display_grade_window_m: float = 30.0
    elevation_outlier_window_m: float = 50.0
    elevation_outlier_mad_factor: float = 6.0
    minimum_elevation_outlier_m: float = 12.0
    signal_gap_warning_m: float = 100.0
    low_density_points_per_km: float = 20.0
    max_grade_for_display_pct: float = 40.0

    def validate(self) -> None:
        if not 5.0 <= self.grid_step_m <= 10.0:
            raise ValueError("grid_step_m must be between 5 and 10 metres")
        if self.robust_grade_window_m < 2.0 * self.grid_step_m:
            raise ValueError("robust_grade_window_m is too small for the selected grid")


DEFAULT_COURSE_PROFILE_THRESHOLDS = CourseProfileThresholds()


@dataclass(frozen=True)
class CourseProfile:
    dataframe: pd.DataFrame
    quality: dict[str, object]


def _haversine_segment_metres(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    radius_m = 6_371_008.8
    lat0 = np.radians(lat[:-1])
    lat1 = np.radians(lat[1:])
    dlat = lat1 - lat0
    dlon = np.radians(lon[1:] - lon[:-1])
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat0) * np.cos(lat1) * np.sin(dlon / 2.0) ** 2
    return 2.0 * radius_m * np.arcsin(np.minimum(1.0, np.sqrt(a)))


def _odd_window(window_m: float, step_m: float) -> int:
    points = max(1, int(round(window_m / step_m)))
    return points if points % 2 == 1 else points + 1


def _to_numeric(df: pd.DataFrame, column: str) -> np.ndarray:
    if column not in df.columns:
        return np.full(len(df), np.nan, dtype=float)
    return pd.to_numeric(df[column], errors="coerce").to_numpy(dtype=float)


def prepare_course_profile(
    activity_df: pd.DataFrame,
    *,
    thresholds: CourseProfileThresholds = DEFAULT_COURSE_PROFILE_THRESHOLDS,
) -> CourseProfile:
    """Build a stable metric profile from an imported canonical dataframe."""

    thresholds.validate()
    if not isinstance(activity_df, pd.DataFrame) or len(activity_df) < 2:
        raise ValueError("A course profile requires at least two points")

    source_count = len(activity_df)
    source_distance = _to_numeric(activity_df, "distance_m")
    elevation = _to_numeric(activity_df, "elevation")
    lat = _to_numeric(activity_df, "lat")
    lon = _to_numeric(activity_df, "lon")

    coordinate_valid = np.isfinite(lat) & np.isfinite(lon)
    use_coordinates = bool(coordinate_valid.all() and coordinate_valid.sum() >= 2)
    if use_coordinates:
        horizontal_segments = _haversine_segment_metres(lat, lon)
        horizontal_segments = np.where(np.isfinite(horizontal_segments), horizontal_segments, 0.0)
        distance = np.concatenate(([0.0], np.cumsum(np.maximum(horizontal_segments, 0.0))))
        distance_source = "coordinates_haversine"
    else:
        finite_distance = np.isfinite(source_distance)
        if finite_distance.sum() < 2:
            raise ValueError("The course has neither valid coordinates nor a usable distance")
        first_distance = float(source_distance[finite_distance][0])
        distance = source_distance - first_distance
        distance_source = "source_distance_m"

    finite_distance = np.isfinite(distance)
    rejected_mask = ~finite_distance
    distance = distance[finite_distance]
    elevation = elevation[finite_distance]
    lat = lat[finite_distance]
    lon = lon[finite_distance]

    # Never reorder a route. Backward distances are corrected to the latest
    # travelled distance, then exact duplicates are collapsed deterministically.
    monotonic_corrections = int(np.sum(np.diff(distance) < -1e-6))
    distance = np.maximum.accumulate(distance)
    keep = np.concatenate(([True], np.diff(distance) > 1e-6))
    duplicate_count = int((~keep).sum())
    distance = distance[keep]
    elevation = elevation[keep]
    lat = lat[keep]
    lon = lon[keep]
    if len(distance) < 2 or not math.isfinite(float(distance[-1])) or distance[-1] <= 0:
        raise ValueError("The course distance is empty after deduplication")
    distance = distance - distance[0]

    source_gaps = np.diff(distance)
    gap_count = int(np.sum(source_gaps > thresholds.signal_gap_warning_m))
    max_gap_m = float(np.max(source_gaps)) if source_gaps.size else 0.0

    missing_elevation = ~np.isfinite(elevation)
    known_elevation = ~missing_elevation
    if known_elevation.sum() < 2:
        raise ValueError("The course must contain at least two valid elevations")
    elevation_interpolated = np.interp(distance, distance[known_elevation], elevation[known_elevation])

    step_m = float(thresholds.grid_step_m)
    grid = np.arange(0.0, float(distance[-1]), step_m, dtype=float)
    if grid.size == 0 or grid[-1] < distance[-1]:
        grid = np.append(grid, float(distance[-1]))
    if grid.size < 2:
        raise ValueError("The course is shorter than the selected resampling grid")

    elevation_grid_raw = np.interp(grid, distance, elevation_interpolated)
    known_indicator = np.interp(grid, distance, known_elevation.astype(float))
    interpolated_grid = known_indicator < 0.999

    # Correct isolated altitude spikes on a distance-defined window.
    outlier_window = _odd_window(thresholds.elevation_outlier_window_m, step_m)
    elevation_series = pd.Series(elevation_grid_raw)
    local_median = elevation_series.rolling(outlier_window, center=True, min_periods=1).median()
    deviation = (elevation_series - local_median).abs()
    local_mad = deviation.rolling(outlier_window, center=True, min_periods=1).median()
    outlier_limit = np.maximum(
        thresholds.minimum_elevation_outlier_m,
        thresholds.elevation_outlier_mad_factor * 1.4826 * local_mad.to_numpy(dtype=float),
    )
    altitude_outlier = deviation.to_numpy(dtype=float) > outlier_limit
    corrected_elevation = np.where(altitude_outlier, local_median.to_numpy(dtype=float), elevation_grid_raw)

    smooth_window = _odd_window(thresholds.elevation_smoothing_window_m, step_m)
    smooth_elevation = (
        pd.Series(corrected_elevation)
        .rolling(smooth_window, center=True, min_periods=1)
        .mean()
        .to_numpy(dtype=float)
    )

    ds = np.diff(grid, prepend=grid[0])
    de = np.diff(smooth_elevation, prepend=smooth_elevation[0])
    raw_grade = np.divide(de, ds, out=np.zeros_like(de), where=ds > 0) * 100.0

    robust_lag = max(1, int(round(thresholds.robust_grade_window_m / step_m)))
    robust_grade = np.zeros_like(smooth_elevation)
    for index in range(len(grid)):
        left = max(0, index - robust_lag // 2)
        right = min(len(grid) - 1, index + robust_lag // 2)
        x_window = grid[left : right + 1]
        y_window = smooth_elevation[left : right + 1]
        robust_grade[index] = float(np.polyfit(x_window, y_window, 1)[0] * 100.0) if len(x_window) >= 2 else 0.0
    display_window = _odd_window(thresholds.display_grade_window_m, step_m)
    display_grade = (
        pd.Series(robust_grade)
        .rolling(display_window, center=True, min_periods=1)
        .median()
        .clip(-thresholds.max_grade_for_display_pct, thresholds.max_grade_for_display_pct)
        .to_numpy(dtype=float)
    )

    geo_valid = np.isfinite(lat) & np.isfinite(lon)
    if geo_valid.sum() >= 2:
        lat_grid = np.interp(grid, distance[geo_valid], lat[geo_valid])
        lon_grid = np.interp(grid, distance[geo_valid], lon[geo_valid])
    else:
        lat_grid = np.full(len(grid), np.nan)
        lon_grid = np.full(len(grid), np.nan)

    profile = pd.DataFrame(
        {
            "distance_m": grid,
            "distance_km": grid / 1000.0,
            "elevation_raw_m": elevation_grid_raw,
            "elevation_m": smooth_elevation,
            "grade_raw_pct": raw_grade,
            "grade_robust_pct": robust_grade,
            "grade_display_pct": display_grade,
            "lat": lat_grid,
            "lon": lon_grid,
            "elevation_interpolated": interpolated_grid,
            "elevation_corrected": altitude_outlier,
        }
    )

    distance_km = float(grid[-1] / 1000.0)
    density = float(source_count / distance_km) if distance_km > 0 else 0.0
    interpolation_ratio = float(np.mean(interpolated_grid))
    correction_ratio = float((int(rejected_mask.sum()) + duplicate_count + monotonic_corrections) / source_count)
    altitude_correction_ratio = float(np.mean(altitude_outlier))
    warnings: list[dict[str, str]] = []
    if interpolation_ratio > 0.05:
        warnings.append({"code": "elevation_interpolated", "message": "Plus de 5 % du profil altimetrique a ete interpole."})
    if altitude_correction_ratio > 0.02:
        warnings.append({"code": "elevation_outliers", "message": "Des anomalies altimetriques ont ete corrigees."})
    if gap_count:
        warnings.append({"code": "signal_gaps", "message": f"{gap_count} trou(s) de plus de {thresholds.signal_gap_warning_m:.0f} m ont ete detectes."})
    if density < thresholds.low_density_points_per_km:
        warnings.append({"code": "low_sampling_density", "message": "La densite de points source est faible."})

    quality_score = 1.0 - min(0.55, interpolation_ratio) - min(0.25, altitude_correction_ratio * 2.0)
    quality_score -= min(0.20, gap_count * 0.03)
    quality_label = "high" if quality_score >= 0.9 else "medium" if quality_score >= 0.7 else "low"
    quality = {
        "profile_version": COURSE_PROFILE_VERSION,
        "distance_source": distance_source,
        "distance_unit": "km",
        "internal_distance_unit": "m",
        "grid_step_m": step_m,
        "elevation_smoothing_window_m": thresholds.elevation_smoothing_window_m,
        "robust_grade_window_m": thresholds.robust_grade_window_m,
        "interpolated_elevation_ratio": interpolation_ratio,
        "corrected_or_rejected_source_ratio": correction_ratio,
        "corrected_elevation_ratio": altitude_correction_ratio,
        "sampling_density_points_per_km": density,
        "signal_gap_count": gap_count,
        "maximum_signal_gap_m": max_gap_m,
        "altimetry_quality": quality_label,
        "warnings": warnings,
    }
    return CourseProfile(dataframe=profile, quality=quality)
