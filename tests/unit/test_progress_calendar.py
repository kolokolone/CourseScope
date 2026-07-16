from types import SimpleNamespace

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


def test_current_streak_accepts_yesterday_but_not_day_before() -> None:
    from core.progress_math import compute_streaks

    assert compute_streaks({"2026-07-13", "2026-07-14", "2026-07-15"}, "2026-07-16") == (3, 3)
    assert compute_streaks({"2026-07-12", "2026-07-13", "2026-07-14"}, "2026-07-16") == (3, 0)


def test_calendar_prefers_local_date_and_keeps_global_cross_year_streak() -> None:
    from services.progress_service import ProgressService

    rows = [
        SimpleNamespace(
            local_date="2025-12-31",
            start_ts_utc="2025-12-31T10:00:00Z",
            distance_m=1_000.0,
            moving_time_s=300.0,
        ),
        SimpleNamespace(
            local_date="2026-01-01",
            start_ts_utc="2025-12-31T23:30:00Z",
            distance_m=5_000.0,
            moving_time_s=1_500.0,
        ),
        SimpleNamespace(
            local_date="2026-01-01",
            start_ts_utc="2026-01-01T12:00:00Z",
            distance_m=3_000.0,
            moving_time_s=900.0,
        ),
    ]

    result = ProgressService.compute_calendar(rows, 2026, reference_date="2026-01-02")

    assert result["total_active_days"] == 1
    assert result["longest_streak"] == 1
    assert result["current_streak"] == 2
    assert result["days"] == [
        {
            "date": "2026-01-01",
            "has_activity": True,
            "distance_km": 8.0,
            "moving_time_s": 2400.0,
            "activity_count": 2,
        }
    ]
