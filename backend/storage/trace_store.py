from __future__ import annotations

import hashlib
import json
import math
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from core._shared import compute_elevation_gain, compute_elevation_loss


def compute_route_fingerprint(df: pd.DataFrame, *, sample_points: int = 200, decimals: int = 5) -> str | None:
    if df.empty or "lat" not in df.columns or "lon" not in df.columns:
        return None

    coords = df[["lat", "lon"]].dropna()
    if coords.empty:
        return None

    points = coords.to_numpy(dtype=float)
    if len(points) > sample_points:
        idx = np.linspace(0, len(points) - 1, sample_points).astype(int)
        points = points[idx]

    rounded = np.round(points, decimals=decimals)
    payload = "|".join(f"{lat:.{decimals}f},{lon:.{decimals}f}" for lat, lon in rounded)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compute_trace_metrics(df: pd.DataFrame) -> dict[str, float | None]:
    if df.empty:
        return {
            "distance_km": 0.0,
            "elevation_gain_m": 0.0,
            "elevation_loss_m": 0.0,
            "elevation_min_m": None,
            "elevation_max_m": None,
        }

    distance_km = 0.0
    if "distance_m" in df.columns:
        vals = pd.to_numeric(df["distance_m"], errors="coerce").dropna()
        if not vals.empty:
            distance_km = float(vals.iloc[-1]) / 1000.0

    elevation_gain_m = 0.0
    elevation_loss_m = 0.0
    elevation_min_m: float | None = None
    elevation_max_m: float | None = None

    if "elevation" in df.columns:
        elev = pd.to_numeric(df["elevation"], errors="coerce").dropna().to_numpy(dtype=float)
        if elev.size > 0:
            elevation_min_m = float(np.min(elev))
            elevation_max_m = float(np.max(elev))
        if elev.size > 1:
            elevation_gain_m = compute_elevation_gain(elev)
            elevation_loss_m = compute_elevation_loss(elev)

    return {
        "distance_km": distance_km,
        "elevation_gain_m": elevation_gain_m,
        "elevation_loss_m": elevation_loss_m,
        "elevation_min_m": elevation_min_m,
        "elevation_max_m": elevation_max_m,
    }


class TraceStore:
    def __init__(self, traces_dir: str | Path = "./data/traces"):
        self.traces_dir = Path(traces_dir)
        self.traces_dir.mkdir(parents=True, exist_ok=True)

    def _get_trace_dir(self, trace_id: str) -> Path:
        return self.traces_dir / trace_id

    def _get_original_path(self, trace_id: str, filename: str) -> Path:
        suffix = Path(filename).suffix.lower() or ".gpx"
        return self._get_trace_dir(trace_id) / f"original{suffix}"

    def save_trace(
        self,
        *,
        trace_id: str,
        filename: str,
        raw_bytes: bytes,
        df: pd.DataFrame,
        meta: dict[str, object] | None = None,
    ) -> dict[str, str]:
        trace_dir = self._get_trace_dir(trace_id)
        trace_dir.mkdir(parents=True, exist_ok=True)

        original_path = self._get_original_path(trace_id, filename)
        parquet_path = trace_dir / "df.parquet"
        meta_path = trace_dir / "meta.json"

        with original_path.open("wb") as f:
            f.write(raw_bytes)

        df_to_store = df.copy()
        for column in df_to_store.columns:
            if isinstance(df_to_store[column].dtype, pd.DatetimeTZDtype):
                df_to_store[column] = df_to_store[column].dt.tz_convert("UTC").dt.tz_localize(None)
        df_to_store.to_parquet(parquet_path, engine="pyarrow")

        payload = dict(meta or {})
        payload.setdefault("filename", filename)
        payload.setdefault("rows", int(df_to_store.shape[0]))
        meta_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

        return {
            "original_path": str(original_path.resolve()),
            "parquet_path": str(parquet_path.resolve()),
        }

    def load_trace_dataframe(self, trace_id: str) -> pd.DataFrame:
        parquet_path = self._get_trace_dir(trace_id) / "df.parquet"
        if not parquet_path.exists():
            raise FileNotFoundError(f"Trace parquet missing for {trace_id}")
        return pd.read_parquet(parquet_path)

    def load_trace_bytes(self, trace_id: str) -> tuple[str, bytes]:
        trace_dir = self._get_trace_dir(trace_id)
        if not trace_dir.exists():
            raise FileNotFoundError(f"Trace {trace_id} not found")

        for candidate in trace_dir.iterdir():
            if candidate.is_file() and candidate.name.startswith("original"):
                return candidate.name, candidate.read_bytes()
        raise FileNotFoundError(f"Original file missing for trace {trace_id}")

    def delete_trace(self, trace_id: str) -> bool:
        trace_dir = self._get_trace_dir(trace_id)
        if not trace_dir.exists():
            return False
        shutil.rmtree(trace_dir, ignore_errors=True)
        return True

    def list_trace_dirs(self) -> list[Path]:
        if not self.traces_dir.exists():
            return []
        return [p for p in self.traces_dir.iterdir() if p.is_dir()]


def format_trace_name(name: str | None, fallback: str) -> str:
    if name is None:
        return fallback
    cleaned = str(name).strip()
    if cleaned == "":
        return fallback
    return cleaned


def safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        out = float(value)
    except Exception:
        return None
    if not math.isfinite(out):
        return None
    return out
