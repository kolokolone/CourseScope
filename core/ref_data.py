from __future__ import annotations

import hashlib
import io
import os
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from pathlib import Path

import pandas as pd


PRO_PACE_VS_GRADE_ENV_VAR = "COURSESCOPE_PRO_PACE_VS_GRADE_PATH"
PRO_PACE_VS_GRADE_RESOURCE_PACKAGE = "core.resources"
PRO_PACE_VS_GRADE_RESOURCE_NAME = "pro_pace_vs_grade.csv"


@dataclass(frozen=True)
class ProPaceVsGradeInfo:
    source: str  # "file" | "package" | "missing"
    path: str | None
    mtime_ns: int | None
    sha256: str | None
    rows: int


def _empty_pro_pace_vs_grade_df() -> pd.DataFrame:
    return pd.DataFrame(columns=["grade_percent", "pace_s_per_km_pro"])


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _parse_pro_pace_vs_grade_csv_bytes(data: bytes) -> pd.DataFrame:
    try:
        df = pd.read_csv(io.BytesIO(data))
    except Exception:
        return _empty_pro_pace_vs_grade_df()

    expected_cols = {"grade_percent", "pace_s_per_km_pro"}
    if not expected_cols.issubset(df.columns):
        return _empty_pro_pace_vs_grade_df()
    return df.dropna(subset=["grade_percent", "pace_s_per_km_pro"])


def _resolve_csv_path(path: str | Path) -> tuple[str, int | None]:
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = (Path.cwd() / p)
    try:
        resolved = p.resolve()
    except Exception:
        resolved = p
    try:
        mtime_ns = resolved.stat().st_mtime_ns
    except OSError:
        mtime_ns = None
    return str(resolved), mtime_ns


@lru_cache(maxsize=8)
def _load_pro_pace_vs_grade_from_file(csv_path: str, mtime_ns: int | None) -> tuple[pd.DataFrame, ProPaceVsGradeInfo]:
    _ = mtime_ns  # part of the cache key
    try:
        data = Path(csv_path).read_bytes()
    except FileNotFoundError:
        info = ProPaceVsGradeInfo(source="missing", path=str(csv_path), mtime_ns=mtime_ns, sha256=None, rows=0)
        return _empty_pro_pace_vs_grade_df(), info
    except Exception:
        info = ProPaceVsGradeInfo(source="file", path=str(csv_path), mtime_ns=mtime_ns, sha256=None, rows=0)
        return _empty_pro_pace_vs_grade_df(), info

    sha = _sha256_hex(data)
    df = _parse_pro_pace_vs_grade_csv_bytes(data)
    info = ProPaceVsGradeInfo(source="file", path=str(csv_path), mtime_ns=mtime_ns, sha256=sha, rows=int(len(df)))
    return df, info


@lru_cache(maxsize=1)
def _load_pro_pace_vs_grade_from_package() -> tuple[pd.DataFrame, ProPaceVsGradeInfo]:
    try:
        file = resources.files(PRO_PACE_VS_GRADE_RESOURCE_PACKAGE).joinpath(PRO_PACE_VS_GRADE_RESOURCE_NAME)
        with file.open("rb") as f:
            data = f.read()
    except (FileNotFoundError, ModuleNotFoundError):
        info = ProPaceVsGradeInfo(source="missing", path=None, mtime_ns=None, sha256=None, rows=0)
        return _empty_pro_pace_vs_grade_df(), info
    except Exception:
        info = ProPaceVsGradeInfo(source="package", path=None, mtime_ns=None, sha256=None, rows=0)
        return _empty_pro_pace_vs_grade_df(), info

    sha = _sha256_hex(data)
    df = _parse_pro_pace_vs_grade_csv_bytes(data)
    info = ProPaceVsGradeInfo(source="package", path=None, mtime_ns=None, sha256=sha, rows=int(len(df)))
    return df, info


def load_pro_pace_vs_grade(csv_path: str | Path | None = None) -> tuple[pd.DataFrame, ProPaceVsGradeInfo]:
    """Load the pro pace-vs-grade reference table.

    Source selection order:
    - csv_path arg (if provided)
    - env var COURSESCOPE_PRO_PACE_VS_GRADE_PATH (if set and file exists)
    - packaged resource core/resources/pro_pace_vs_grade.csv
    """

    if csv_path is not None:
        resolved, mtime_ns = _resolve_csv_path(csv_path)
        return _load_pro_pace_vs_grade_from_file(resolved, mtime_ns)

    override = os.environ.get(PRO_PACE_VS_GRADE_ENV_VAR)
    if override:
        resolved, mtime_ns = _resolve_csv_path(override)
        if Path(resolved).exists():
            return _load_pro_pace_vs_grade_from_file(resolved, mtime_ns)

    return _load_pro_pace_vs_grade_from_package()


def get_pro_pace_vs_grade_df(csv_path: str | Path | None = None) -> pd.DataFrame:
    df, _info = load_pro_pace_vs_grade(csv_path)
    return df


def get_pro_pace_vs_grade_info(csv_path: str | Path | None = None) -> ProPaceVsGradeInfo:
    _df, info = load_pro_pace_vs_grade(csv_path)
    return info
