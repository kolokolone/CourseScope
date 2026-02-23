from __future__ import annotations

import argparse
import json
import sys
import time

from progress.indexation_runner import (
    SLOW_STRATEGIES,
    get_indexation_state,
    start_fast_indexation_in_background,
    start_slow_indexation_in_background,
)


def _state_to_payload(state) -> dict:
    total = int(state.progress_total or 0)
    current = int(state.progress_current or 0)
    percent = 0.0
    if total > 0:
        percent = max(0.0, min(100.0, (float(current) / float(total)) * 100.0))

    return {
        "running": bool(state.running),
        "mode": state.mode,
        "phase": state.phase,
        "progress_current": current,
        "progress_total": total,
        "percent": round(percent, 2),
        "last_error": state.last_error,
        "last_started_at_utc": state.started_at_utc,
        "last_finished_at_utc": state.finished_at_utc,
        "last_result": state.last_result.to_dict() if state.last_result is not None else None,
    }


def _print_payload(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=True, indent=2))


def _wait_for_completion(*, timeout_s: float, poll_interval_s: float):
    started = time.monotonic()
    while True:
        state = get_indexation_state()
        if not bool(state.running):
            return state
        elapsed = time.monotonic() - started
        if elapsed > float(timeout_s):
            raise TimeoutError(f"indexation timed out after {timeout_s:.1f}s")
        time.sleep(max(0.05, float(poll_interval_s)))


def _exit_code_from_final_state(state) -> int:
    if state.last_error:
        return 1
    if state.last_result is not None and int(state.last_result.errors) > 0:
        return 1
    return 0


def _run_fast(args: argparse.Namespace, db_session_factory) -> int:
    state = start_fast_indexation_in_background(db_session_factory=db_session_factory, reason=str(args.reason))
    if not bool(args.wait):
        _print_payload(_state_to_payload(state))
        return 0

    final_state = _wait_for_completion(timeout_s=float(args.timeout_s), poll_interval_s=float(args.poll_interval_s))
    _print_payload(_state_to_payload(final_state))
    return _exit_code_from_final_state(final_state)


def _run_slow(args: argparse.Namespace, db_session_factory) -> int:
    strategy = str(args.strategy).strip().lower()
    if strategy not in SLOW_STRATEGIES:
        strategy = "incremental"

    state = start_slow_indexation_in_background(
        db_session_factory=db_session_factory,
        reason=str(args.reason),
        strategy=strategy,
        force=bool(args.force),
    )
    if not bool(args.wait):
        _print_payload(_state_to_payload(state))
        return 0

    final_state = _wait_for_completion(timeout_s=float(args.timeout_s), poll_interval_s=float(args.poll_interval_s))
    _print_payload(_state_to_payload(final_state))
    return _exit_code_from_final_state(final_state)


def _run_status(_args: argparse.Namespace) -> int:
    _print_payload(_state_to_payload(get_indexation_state()))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CourseScope progression indexation CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    parser_fast = sub.add_parser("fast", help="Run fast indexation")
    parser_fast.add_argument("--reason", default="cli_fast", help="Run reason label")
    parser_fast.add_argument("--wait", action="store_true", default=True, help="Wait for completion")
    parser_fast.add_argument("--no-wait", action="store_false", dest="wait", help="Return immediately")
    parser_fast.add_argument("--timeout-s", type=float, default=1800.0, help="Max wait time in seconds")
    parser_fast.add_argument("--poll-interval-s", type=float, default=0.25, help="Polling interval in seconds")

    parser_slow = sub.add_parser("slow", help="Run slow indexation")
    parser_slow.add_argument("--strategy", default="incremental", choices=sorted(SLOW_STRATEGIES), help="Slow strategy")
    parser_slow.add_argument("--force", action="store_true", help="Force complete recompute")
    parser_slow.add_argument("--reason", default="cli_slow", help="Run reason label")
    parser_slow.add_argument("--wait", action="store_true", default=True, help="Wait for completion")
    parser_slow.add_argument("--no-wait", action="store_false", dest="wait", help="Return immediately")
    parser_slow.add_argument("--timeout-s", type=float, default=1800.0, help="Max wait time in seconds")
    parser_slow.add_argument("--poll-interval-s", type=float, default=0.25, help="Polling interval in seconds")

    sub.add_parser("status", help="Print current indexation status")
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(argv) if argv is not None else sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)

    from db.session import init_db, make_engine, make_session_factory

    engine = make_engine()
    init_db(engine)
    db_session_factory = make_session_factory(engine)

    try:
        if args.command == "fast":
            return _run_fast(args, db_session_factory)
        if args.command == "slow":
            return _run_slow(args, db_session_factory)
        return _run_status(args)
    except TimeoutError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
