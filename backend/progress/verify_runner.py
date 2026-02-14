from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from config import get_activities_dir
from progress.verify_index import verify_progress_index, VerifyProgressResult


@dataclass
class VerifyState:
    running: bool = False
    last_started_at_utc: str | None = None
    last_finished_at_utc: str | None = None
    last_result: VerifyProgressResult | None = None
    last_error: str | None = None


_lock = threading.Lock()
_thread: threading.Thread | None = None
_state = VerifyState()


def get_verify_state() -> VerifyState:
    with _lock:
        return VerifyState(
            running=_state.running,
            last_started_at_utc=_state.last_started_at_utc,
            last_finished_at_utc=_state.last_finished_at_utc,
            last_result=_state.last_result,
            last_error=_state.last_error,
        )


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def start_verify_in_background(
    *,
    db_session_factory,
    activities_dir: Path | None = None,
) -> VerifyState:
    global _thread

    base_dir = (activities_dir or get_activities_dir()).resolve()

    with _lock:
        if _thread is not None and _thread.is_alive():
            return get_verify_state()

        _state.running = True
        _state.last_started_at_utc = _now_utc_iso()
        _state.last_finished_at_utc = None
        _state.last_error = None
        _state.last_result = None

        def _run() -> None:
            global _thread
            try:
                session = db_session_factory()
                try:
                    result = verify_progress_index(session, activities_dir=base_dir)
                finally:
                    session.close()
                with _lock:
                    _state.last_result = result
            except Exception as exc:
                with _lock:
                    _state.last_error = str(exc)
            finally:
                with _lock:
                    _state.running = False
                    _state.last_finished_at_utc = _now_utc_iso()

        _thread = threading.Thread(target=_run, name="progress-verify", daemon=True)
        _thread.start()
        return get_verify_state()
