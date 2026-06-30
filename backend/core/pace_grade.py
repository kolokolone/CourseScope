import math

import numpy as np
import pandas as pd

from core._shared import _weighted_mean
from core.grade_table import grade_factor
from core.transform_report import TransformReport

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


def compute_grade_percent(
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
    return compute_grade_percent(df, smooth_window=smooth_window)


def estimate_flat_pace(
    df: pd.DataFrame, pace_series: pd.Series, grade_series: pd.Series | None = None
) -> float:
    """Estime l'allure de base 'plat' (s/km) en prenant la médiane sur les pentes proches de 0."""
    grade = grade_series.reindex(df.index) if grade_series is not None else compute_grade_percent(df, smooth_window=5)
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
    grade = grade_series.reindex(df.index) if grade_series is not None else compute_grade_percent(df, smooth_window=5)
    grade_arr = grade.to_numpy()
    factor = grade_factor(grade_arr)
    pace_arr = pace.to_numpy()
    gap = pace_arr / factor
    invalid = ~np.isfinite(grade_arr) | ~np.isfinite(pace_arr) | ~np.isfinite(factor) | (factor == 0)
    gap = np.where(invalid, np.nan, gap)
    return pd.Series(gap, index=df.index)


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

    from core.derived import compute_moving_mask  # Lazy import to avoid circular dependency
    from core.constants import DEFAULT_GRADE_SMOOTH_WINDOW

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
    grade_s = grade_series.reindex(df.index) if grade_series is not None else compute_grade_percent(df, smooth_window=DEFAULT_GRADE_SMOOTH_WINDOW)

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

    from core.constants import MOVING_SPEED_THRESHOLD_M_S

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
    grade_for_subset = grade_series.reindex(subset.index) if grade_series is not None else compute_grade_percent(subset, smooth_window=5)
    flat_pace = estimate_flat_pace(subset, pace_used, grade_series=grade_for_subset)
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
