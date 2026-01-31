from __future__ import annotations

import argparse
import sys
import time

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(description="Wait until an HTTP endpoint returns 200.")
    parser.add_argument("url")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--interval", type=float, default=0.5)
    args = parser.parse_args()

    deadline = time.time() + args.timeout
    last: str | None = None

    while time.time() < deadline:
        try:
            r = httpx.get(args.url, timeout=2.0)
            if r.status_code == 200:
                return 0
            last = f"HTTP {r.status_code}"
        except Exception as e:
            last = str(e)

        time.sleep(args.interval)

    print(f"Timeout waiting for {args.url}: {last}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
