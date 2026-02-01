from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]


def wait_http_ok(url: str, *, timeout_s: float) -> None:
    deadline = time.time() + timeout_s
    last_err: str | None = None
    while time.time() < deadline:
        try:
            r = httpx.get(url, timeout=2.0)
            if r.status_code == 200:
                return
            last_err = f"HTTP {r.status_code}"
        except Exception as e:
            last_err = str(e)
        time.sleep(0.4)
    raise RuntimeError(f"Timeout waiting for {url}: {last_err}")


def main() -> int:
    gpx = ROOT / "tests" / "course.gpx"
    if not gpx.exists():
        print(f"Missing file: {gpx}", file=sys.stderr)
        return 2

    api_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.api.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ]

    proc: subprocess.Popen[object] | None = None
    try:
        proc = subprocess.Popen(api_cmd, cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        wait_http_ok("http://127.0.0.1:8000/health", timeout_s=10)

        with gpx.open("rb") as f:
            r = httpx.post(
                "http://127.0.0.1:8000/activity/load",
                files={"file": ("course.gpx", f, "application/gpx+xml")},
                data={"name": "smoke"},
                timeout=30.0,
            )

        print("UPLOAD_STATUS", r.status_code)
        print(r.text)
        return 0 if r.status_code == 200 else 1
    finally:
        if proc is not None and proc.poll() is None:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
