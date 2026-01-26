"""Contrat DataFrame activite canonique (sans Streamlit).

Ce projet utilise un DataFrame canonique "par point" (sortie des loaders GPX/FIT).
Objectifs :
- definir un schema stable + invariants
- valider les entrees aux frontieres service/API
- proposer des coercions "sans danger" (sans masquer les problemes de donnees)

Ce module ne doit pas importer Streamlit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


SCHEMA_VERSION = "v1"


# Schema stable (les colonnes doivent exister ; les valeurs peuvent etre NaN/NaT pour les capteurs optionnels).
CANONICAL_COLUMNS: tuple[str, ...] = (
    "lat",
    "lon",
    "elevation",
    "time",
    "distance_m",
    "delta_distance_m",
    "elapsed_time_s",
    "delta_time_s",
    "speed_m_s",
    "pace_s_per_km",
    "heart_rate",
    "cadence",
    "power",
    "stride_length_m",
    "vertical_oscillation_cm",
    "vertical_ratio_pct",
    "ground_contact_time_ms",
    "gct_balance_pct",
)


# Ensemble minimal requis par la plupart des analyses.
REQUIRED_COLUMNS: tuple[str, ...] = (
    "distance_m",
    "delta_distance_m",
    "delta_time_s",
    "elapsed_time_s",
    "speed_m_s",
    "pace_s_per_km",
    "elevation",
)


RUNNING_DYNAMICS_COLUMNS: tuple[str, ...] = (
    "stride_length_m",
    "vertical_oscillation_cm",
    "vertical_ratio_pct",
    "ground_contact_time_ms",
    "gct_balance_pct",
)


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    details: dict[str, Any] | None = None


@dataclass(frozen=True)
class ValidationReport:
    ok: bool
    issues: list[ValidationIssue]

    def raise_for_issues(self) -> None:
        if self.ok:
            return
        lines = ["Echec de validation du contrat DataFrame activite:"]
        for issue in self.issues:
            lines.append(f"- {issue.code}: {issue.message}")
        raise ValueError("\n".join(lines))


def coerce_activity_df(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce les colonnes vers les dtypes canoniques quand c'est sans risque.

    Ne tente PAS de corriger les problemes semantiques (ex: distance non monotone).
    """

    if not isinstance(df, pd.DataFrame):
        raise TypeError("df doit etre un pandas.DataFrame")

    out = df.copy()

    # S'assure que toutes les colonnes canoniques existent.
    for col in CANONICAL_COLUMNS:
        if col not in out.columns:
            out[col] = np.nan

    # Convertit time.
    out["time"] = pd.to_datetime(out["time"], errors="coerce")

    # Coerce colonnes numeriques.
    for col in CANONICAL_COLUMNS:
        if col == "time":
            continue
        out[col] = pd.to_numeric(out[col], errors="coerce")

    return out


def validate_activity_df(
    df: pd.DataFrame,
    *,
    require_columns: tuple[str, ...] = REQUIRED_COLUMNS,
    enforce_distance_monotone: bool = True,
    enforce_positive_delta_time: bool = True,
    expect_running_dynamics_all_nan: bool | None = None,
) -> ValidationReport:
    issues: list[ValidationIssue] = []

    if not isinstance(df, pd.DataFrame):
        return ValidationReport(
            ok=False,
            issues=[ValidationIssue(code="type", message="df doit etre un pandas.DataFrame")],
        )

    missing = [c for c in require_columns if c not in df.columns]
    if missing:
        issues.append(
            ValidationIssue(
                code="missing_columns",
                message=f"Colonnes requises manquantes: {', '.join(missing)}",
                details={"missing": missing},
            )
        )
        return ValidationReport(ok=False, issues=issues)

    # Monotonie de la distance.
    if enforce_distance_monotone and "distance_m" in df.columns:
        dist = pd.to_numeric(df["distance_m"], errors="coerce").to_numpy(dtype=float)
        dist = dist[np.isfinite(dist)]
        if dist.size >= 2:
            diffs = np.diff(dist)
            # Autorise un bruit numerique minime.
            if np.any(diffs < -1e-6):
                issues.append(
                    ValidationIssue(
                        code="distance_non_monotone",
                        message="distance_m doit etre non-decroissante (monotone)",
                    )
                )

    # delta_time_s > 0.
    if enforce_positive_delta_time and "delta_time_s" in df.columns:
        dt = pd.to_numeric(df["delta_time_s"], errors="coerce").to_numpy(dtype=float)
        dt = dt[np.isfinite(dt)]
        if dt.size and np.any(dt <= 0):
            issues.append(
                ValidationIssue(
                    code="delta_time_non_positive",
                    message="delta_time_s doit etre strictement > 0 pour les valeurs finies (utiliser NaN pour invalide)",
                )
            )

    # Optionnel: running dynamics toutes a NaN (typique pour GPX).
    if expect_running_dynamics_all_nan is not None:
        missing_rd = [c for c in RUNNING_DYNAMICS_COLUMNS if c not in df.columns]
        if missing_rd:
            issues.append(
                ValidationIssue(
                    code="missing_running_dynamics_columns",
                    message=f"Colonnes running dynamics manquantes: {', '.join(missing_rd)}",
                    details={"missing": missing_rd},
                )
            )
        else:
            any_present = False
            for c in RUNNING_DYNAMICS_COLUMNS:
                values = pd.to_numeric(df[c], errors="coerce")
                if values.notna().any():
                    any_present = True
                    break
            if expect_running_dynamics_all_nan and any_present:
                issues.append(
                    ValidationIssue(
                        code="running_dynamics_unexpected_values",
                        message="Valeurs running dynamics inattendues (attendu: toutes a NaN pour cette entree)",
                    )
                )
            if (not expect_running_dynamics_all_nan) and (not any_present):
                issues.append(
                    ValidationIssue(
                        code="running_dynamics_missing_values",
                        message="Valeurs running dynamics attendues mais toutes a NaN",
                    )
                )

    return ValidationReport(ok=(len(issues) == 0), issues=issues)


def assert_activity_df_contract(df: pd.DataFrame, **kwargs: Any) -> None:
    """Valide et leve ValueError en cas d'echec."""

    validate_activity_df(df, **kwargs).raise_for_issues()
