"""Compatibility shim — delegates to split modules."""

from core.splits import compute_splits
from core.best_efforts import prepare_effort_arrays, compute_best_efforts, compute_best_efforts_by_duration, compute_race_predictions
from core.climbs import compute_climbs
from core.pace_grade import (compute_grade_percent, compute_grade_percent_series,
                              estimate_flat_pace, compute_gap_series,
                              compute_pace_vs_grade_data, compute_residuals_vs_grade_data)
from core.plots import (build_distribution_plots, build_pace_vs_grade_plot,
                         build_pace_vs_grade_plot_from_data, build_pace_grade_scatter,
                         build_pace_grade_heatmap, build_residuals_vs_grade,
                         build_residuals_vs_grade_plot_from_data, build_pace_elevation_plot)
from core.derived import (compute_moving_mask, compute_derived_series, compute_summary_stats,
                           compute_pace_series, compute_pause_markers)
