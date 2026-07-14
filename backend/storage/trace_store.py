from __future__ import annotations

import hashlib
import json
import math
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from core._shared import compute_elevation_gain, compute_elevation_loss
from core.contracts.activity_df_contract import SCHEMA_VERSION, coerce_activity_df, validate_activity_df


@dataclass(frozen=True)
class TraceDataframeLoad:
    dataframe: pd.DataFrame
    source: str
    rebuild_reason: str | None
    parquet_path: str
    generated_at_utc: str
    source_hash_sha256: str


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

        source_hash = hashlib.sha256(raw_bytes).hexdigest()
        generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        self._write_dataframe(parquet_path, df)
        stat = original_path.stat()
        payload = dict(meta or {})
        payload.update(
            {
                "filename": filename,
                "rows": int(df.shape[0]),
                "source_sha256": source_hash,
                "source_size_bytes": int(stat.st_size),
                "source_mtime_ns": int(stat.st_mtime_ns),
                "dataframe_schema_version": SCHEMA_VERSION,
                "generated_at_utc": generated_at,
            }
        )
        self._write_meta(meta_path, payload)

        return {
            "original_path": str(original_path.resolve()),
            "parquet_path": str(parquet_path.resolve()),
            "source_sha256": source_hash,
            "dataframe_schema_version": SCHEMA_VERSION,
            "generated_at_utc": generated_at,
        }

    @staticmethod
    def _write_dataframe(parquet_path: Path, df: pd.DataFrame) -> None:
        df_to_store = coerce_activity_df(df)
        for column in df_to_store.columns:
            if isinstance(df_to_store[column].dtype, pd.DatetimeTZDtype):
                df_to_store[column] = df_to_store[column].dt.tz_convert("UTC").dt.tz_localize(None)
        df_to_store.to_parquet(parquet_path, engine="pyarrow")

    @staticmethod
    def _write_meta(meta_path: Path, payload: dict[str, object]) -> None:
        meta_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    def read_metadata(self, trace_id: str) -> dict[str, object]:
        meta_path = self._get_trace_dir(trace_id) / "meta.json"
        if not meta_path.exists():
            return {}
        try:
            value = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return value if isinstance(value, dict) else {}

    def load_or_rebuild_dataframe(
        self,
        trace_id: str,
        *,
        expected_source_hash: str,
        rebuild: Callable[[str, bytes], pd.DataFrame],
        logger=None,
    ) -> TraceDataframeLoad:
        """Load a valid parquet without parsing the original trace.

        The original is only opened when an artifact is missing, corrupt,
        schema-incompatible, or its cheap stat identity changed. In the latter
        case its SHA-256 is recomputed before deciding whether to rebuild.
        """

        trace_dir = self._get_trace_dir(trace_id)
        parquet_path = trace_dir / "df.parquet"
        meta_path = trace_dir / "meta.json"
        metadata = self.read_metadata(trace_id)
        reason: str | None = None
        if not parquet_path.exists():
            reason = "parquet_missing"
        elif not metadata:
            reason = "metadata_missing_or_invalid"
        elif metadata.get("dataframe_schema_version") != SCHEMA_VERSION:
            reason = "dataframe_schema_incompatible"
        elif metadata.get("source_sha256") != expected_source_hash:
            reason = "stored_source_hash_mismatch"
        else:
            try:
                original_path = next(path for path in trace_dir.iterdir() if path.is_file() and path.name.startswith("original"))
                stat = original_path.stat()
                stat_changed = (
                    int(metadata.get("source_size_bytes", -1)) != int(stat.st_size)
                    or int(metadata.get("source_mtime_ns", -1)) != int(stat.st_mtime_ns)
                )
                if stat_changed:
                    current_hash = hashlib.sha256(original_path.read_bytes()).hexdigest()
                    if current_hash != expected_source_hash:
                        reason = "source_file_hash_changed"
                    else:
                        metadata["source_size_bytes"] = int(stat.st_size)
                        metadata["source_mtime_ns"] = int(stat.st_mtime_ns)
                        self._write_meta(meta_path, metadata)
                if reason is None:
                    dataframe = pd.read_parquet(parquet_path)
                    report = validate_activity_df(dataframe, enforce_positive_delta_time=False)
                    if not report.ok:
                        reason = "parquet_contract_invalid"
                    else:
                        return TraceDataframeLoad(
                            dataframe=coerce_activity_df(dataframe),
                            source="parquet",
                            rebuild_reason=None,
                            parquet_path=str(parquet_path.resolve()),
                            generated_at_utc=str(metadata.get("generated_at_utc") or ""),
                            source_hash_sha256=str(metadata.get("source_sha256") or expected_source_hash),
                        )
            except StopIteration:
                reason = "original_file_missing"
            except Exception:
                reason = "parquet_unreadable"

        if logger is not None:
            logger.warning("trace_parquet_rebuild trace_id=%s reason=%s", trace_id, reason)
        filename, raw = self.load_trace_bytes(trace_id)
        current_hash = hashlib.sha256(raw).hexdigest()
        dataframe = coerce_activity_df(rebuild(filename, raw))
        report = validate_activity_df(dataframe, enforce_positive_delta_time=False)
        report.raise_for_issues()
        self._write_dataframe(parquet_path, dataframe)
        generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        original_path = next(path for path in trace_dir.iterdir() if path.is_file() and path.name.startswith("original"))
        stat = original_path.stat()
        self._write_meta(
            meta_path,
            {
                "filename": filename,
                "rows": int(len(dataframe)),
                "source_sha256": current_hash,
                "source_size_bytes": int(stat.st_size),
                "source_mtime_ns": int(stat.st_mtime_ns),
                "dataframe_schema_version": SCHEMA_VERSION,
                "generated_at_utc": generated_at,
                "last_rebuild_reason": reason,
            },
        )
        return TraceDataframeLoad(
            dataframe=dataframe,
            source="rebuilt",
            rebuild_reason=reason,
            parquet_path=str(parquet_path.resolve()),
            generated_at_utc=generated_at,
            source_hash_sha256=current_hash,
        )

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
