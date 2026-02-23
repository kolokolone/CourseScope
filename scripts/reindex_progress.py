from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Legacy wrapper for full progression reindex (compatibility alias)."
    )
    parser.add_argument("--limit", type=int, default=0, help="Deprecated and ignored")
    parser.add_argument("--commit-every", type=int, default=25, help="Deprecated and ignored")
    parser.add_argument("--reason", type=str, default="legacy_reindex_progress", help="Run reason label")
    parser.add_argument("--no-wait", action="store_true", help="Return immediately after trigger")
    args = parser.parse_args(argv)

    print(
        "[DEPRECATED] scripts/reindex_progress.py now aliases to 'index_progress.py slow --strategy backfill_full --force'.",
        file=sys.stderr,
    )
    if int(args.limit) > 0 or int(args.commit_every) != 25:
        print(
            "[DEPRECATED] --limit and --commit-every are ignored by this compatibility wrapper.",
            file=sys.stderr,
        )

    root = Path(__file__).resolve().parents[1]
    sys.path.append(str(root / "backend"))

    from progress.index_cli import main as cli_main

    delegated_argv = [
        "slow",
        "--strategy",
        "backfill_full",
        "--force",
        "--reason",
        str(args.reason),
    ]
    if bool(args.no_wait):
        delegated_argv.append("--no-wait")
    return int(cli_main(delegated_argv))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
