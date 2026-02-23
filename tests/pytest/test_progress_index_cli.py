from __future__ import annotations

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


def test_index_cli_status_outputs_payload(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("COURSESCOPE_DATA_DIR", str(tmp_path))

    from backend.progress import index_cli
    from backend.progress.indexation_runner import IndexationResult, IndexationState

    monkeypatch.setattr(
        index_cli,
        "get_indexation_state",
        lambda: IndexationState(
            running=False,
            mode=None,
            phase=None,
            started_at_utc="2026-02-23T08:00:00Z",
            finished_at_utc="2026-02-23T08:00:10Z",
            progress_current=10,
            progress_total=20,
            last_error=None,
            last_result=IndexationResult(scanned=4, added=1, deleted=0, indexed=2, up_to_date=2, errors=0, skipped=0),
        ),
    )

    code = index_cli.main(["status"])
    assert code == 0
    out = capsys.readouterr().out
    assert '"progress_current": 10' in out
    assert '"progress_total": 20' in out
    assert '"indexed": 2' in out


def test_index_cli_slow_returns_error_code_on_failed_state(tmp_path, monkeypatch):
    monkeypatch.setenv("COURSESCOPE_DATA_DIR", str(tmp_path))

    from backend.progress import index_cli
    from backend.progress.indexation_runner import IndexationResult, IndexationState

    monkeypatch.setattr(
        index_cli,
        "start_slow_indexation_in_background",
        lambda db_session_factory, reason, strategy, force: IndexationState(running=True, mode="slow", phase="prepare"),
    )
    monkeypatch.setattr(
        index_cli,
        "_wait_for_completion",
        lambda timeout_s, poll_interval_s: IndexationState(
            running=False,
            mode=None,
            phase=None,
            last_error="run_failed",
            last_result=IndexationResult(scanned=1, indexed=0, errors=1),
        ),
    )

    code = index_cli.main(["slow", "--strategy", "backfill_full", "--force", "--reason", "test"])
    assert code == 1
