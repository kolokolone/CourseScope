from __future__ import annotations

import argparse
import json
import sys
import time
import tracemalloc
from dataclasses import asdict
from pathlib import Path
from typing import Any


def _ensure_project_on_path() -> Path:
    project_dir = Path(__file__).resolve().parents[1]
    if str(project_dir) not in sys.path:
        sys.path.insert(0, str(project_dir))
    return project_dir


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    # Nearest-rank p95.
    idx = int((0.95 * len(ordered)) + 0.999999) - 1
    idx = max(0, min(idx, len(ordered) - 1))
    return float(ordered[idx])


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[mid])
    return float((ordered[mid - 1] + ordered[mid]) / 2.0)


def _stage(
    name: str,
    func,
    *,
    tracemalloc_enabled: bool,
) -> tuple[Any, dict[str, Any]]:
    if tracemalloc_enabled:
        before_current, before_peak = tracemalloc.get_traced_memory()
        tracemalloc.reset_peak()
    else:
        before_current, before_peak = 0, 0

    t0 = time.perf_counter()
    out = func()
    t1 = time.perf_counter()

    if tracemalloc_enabled:
        after_current, after_peak = tracemalloc.get_traced_memory()
    else:
        after_current, after_peak = 0, 0

    meta = {
        "stage": name,
        "time_s": float(t1 - t0),
        "tracemalloc": {
            "before_current_bytes": int(before_current),
            "before_peak_bytes": int(before_peak),
            "after_current_bytes": int(after_current),
            "after_peak_bytes": int(after_peak),
        }
        if tracemalloc_enabled
        else None,
    }
    return out, meta


def _run_once(
    *,
    data: bytes,
    name: str,
    mode: str,
    cache: Any | None,
    tracemalloc_enabled: bool,
) -> dict[str, Any]:
    from services.analysis_service import analyze_real, analyze_theoretical, load_activity
    from services.models import TheoreticalParams

    results: dict[str, Any] = {
        "input": {
            "name": str(name),
            "bytes": int(len(data)),
        },
        "mode": str(mode),
        "warm_cache": bool(cache is not None),
        "stages": [],
    }

    loaded, meta_load = _stage(
        "load_activity",
        lambda: load_activity(data=data, name=name, cache=cache),
        tracemalloc_enabled=tracemalloc_enabled,
    )
    results["stages"].append(meta_load)

    if mode in {"real", "all"}:
        _real, meta_real = _stage(
            "analyze_real",
            lambda: analyze_real(loaded=loaded, params=None, view=None, cache=cache),
            tracemalloc_enabled=tracemalloc_enabled,
        )
        results["stages"].append(meta_real)

    if mode in {"theoretical", "all"}:
        params = TheoreticalParams(
            base_pace_s_per_km=300.0,
            start_datetime=None,
            passage_distances_km=None,
            smoothing_segments=20,
            cap_min_per_km=None,
            weather_factor=1.0,
            split_bias_pct=0.0,
            cap_adv_min_per_km=None,
        )
        _theo, meta_theo = _stage(
            "analyze_theoretical",
            lambda: analyze_theoretical(loaded=loaded, params=params, cache=cache),
            tracemalloc_enabled=tracemalloc_enabled,
        )
        results["stages"].append(meta_theo)
        results["theoretical_params"] = asdict(params)

    return results


def main() -> int:
    _ensure_project_on_path()

    parser = argparse.ArgumentParser(description="CourseScope profiling harness (no Streamlit)")
    parser.add_argument("--input", required=True, help="Path to GPX/FIT file")
    parser.add_argument(
        "--mode",
        default="all",
        choices=["load", "real", "theoretical", "all"],
        help="Which pipeline to run",
    )
    parser.add_argument("--repeat", type=int, default=3, help="Number of measured runs")
    parser.add_argument(
        "--warm-cache",
        action="store_true",
        help="Warm up an in-memory cache before measuring",
    )
    parser.add_argument(
        "--tracemalloc",
        action="store_true",
        help="Enable tracemalloc and record peak bytes per stage",
    )
    parser.add_argument(
        "--json-out",
        default=None,
        help="Write results to a JSON file (path). If omitted, no file is written.",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    data = input_path.read_bytes()
    name = input_path.name
    mode = str(args.mode)
    repeats = int(args.repeat)
    repeats = max(1, repeats)

    if args.tracemalloc:
        tracemalloc.start()

    cache = None
    if args.warm_cache:
        from services.cache import InMemoryCache

        cache = InMemoryCache(max_items=32)

    # Optional warmup.
    if args.warm_cache:
        _ = _run_once(
            data=data,
            name=name,
            mode=mode,
            cache=cache,
            tracemalloc_enabled=bool(args.tracemalloc),
        )

    runs: list[dict[str, Any]] = []
    for _i in range(repeats):
        runs.append(
            _run_once(
                data=data,
                name=name,
                mode=mode,
                cache=cache,
                tracemalloc_enabled=bool(args.tracemalloc),
            )
        )

    # Summaries per stage.
    by_stage: dict[str, list[float]] = {}
    by_stage_peak: dict[str, list[int]] = {}
    for r in runs:
        for s in r.get("stages", []):
            stage = str(s.get("stage"))
            by_stage.setdefault(stage, []).append(float(s.get("time_s", 0.0)))
            if args.tracemalloc and s.get("tracemalloc"):
                peak = int(s["tracemalloc"].get("after_peak_bytes", 0))
                by_stage_peak.setdefault(stage, []).append(peak)

    summary: dict[str, Any] = {
        "input": {
            "path": str(input_path),
            "name": str(name),
            "bytes": int(len(data)),
        },
        "mode": mode,
        "repeat": repeats,
        "warm_cache": bool(args.warm_cache),
        "tracemalloc": bool(args.tracemalloc),
        "stages": {},
    }
    for stage, times_s in by_stage.items():
        stage_summary: dict[str, Any] = {
            "median_s": _median(times_s),
            "p95_s": _p95(times_s),
            "runs": len(times_s),
        }
        if args.tracemalloc:
            peaks = by_stage_peak.get(stage, [])
            stage_summary["peak_bytes_median"] = int(_median([float(p) for p in peaks])) if peaks else 0
            stage_summary["peak_bytes_p95"] = int(_p95([float(p) for p in peaks])) if peaks else 0
        summary["stages"][stage] = stage_summary

    out = {
        "summary": summary,
        "runs": runs,
    }

    # Human-readable output.
    print("CourseScope profile")
    print(f"- input: {summary['input']['path']} ({summary['input']['bytes']} bytes)")
    print(f"- mode: {mode} | repeat: {repeats} | warm_cache: {bool(args.warm_cache)}")
    for stage, s in summary["stages"].items():
        line = f"- {stage}: median {s['median_s']:.4f}s | p95 {s['p95_s']:.4f}s"
        if args.tracemalloc:
            line += f" | peak(median) {s.get('peak_bytes_median', 0)} bytes"
        print(line)

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
        print(f"Wrote JSON: {out_path}")

    if args.tracemalloc:
        tracemalloc.stop()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
