from __future__ import annotations

import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[1]
    sys.path.append(str(root / "backend"))

    from progress.index_cli import main as cli_main

    return int(cli_main(argv))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
