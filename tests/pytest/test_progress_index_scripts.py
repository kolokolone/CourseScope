from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


def test_reindex_progress_legacy_alias_delegates_to_new_cli(monkeypatch):
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "reindex_progress.py"

    spec = importlib.util.spec_from_file_location("legacy_reindex_progress", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    captured: dict[str, list[str]] = {}
    fake_pkg = types.ModuleType("progress")
    fake_cli = types.ModuleType("progress.index_cli")

    def _fake_main(argv: list[str]) -> int:
        captured["argv"] = list(argv)
        return 0

    fake_cli.main = _fake_main
    fake_pkg.index_cli = fake_cli
    monkeypatch.setitem(sys.modules, "progress", fake_pkg)
    monkeypatch.setitem(sys.modules, "progress.index_cli", fake_cli)

    code = module.main(["--reason", "legacy", "--no-wait", "--limit", "5"])
    assert code == 0
    assert captured["argv"] == [
        "slow",
        "--strategy",
        "backfill_full",
        "--force",
        "--reason",
        "legacy",
        "--no-wait",
    ]
