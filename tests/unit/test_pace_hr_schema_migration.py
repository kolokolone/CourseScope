from __future__ import annotations

import importlib

from sqlalchemy import create_engine, inspect, text

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


def test_pace_hr_resolution_migration_rebuilds_the_derived_table() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE progress_pace_hr_bins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    activity_id VARCHAR(36) NOT NULL,
                    activity_type VARCHAR(32) NOT NULL,
                    start_ts_utc TEXT NOT NULL,
                    pace_bin_s_per_km FLOAT NOT NULL,
                    time_s_bin FLOAT NOT NULL,
                    hr_mean_w_bpm FLOAT,
                    hr_q50_w_bpm FLOAT,
                    CONSTRAINT uq_progress_pace_hr_bin
                        UNIQUE (activity_id, pace_bin_s_per_km)
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO progress_pace_hr_bins (
                    activity_id, activity_type, start_ts_utc,
                    pace_bin_s_per_km, time_s_bin, hr_q50_w_bpm
                ) VALUES (
                    'activity', 'real', '2026-07-15T08:00:00Z', 300, 120, 140
                )
                """
            )
        )

    migration = importlib.import_module(
        "db.migrations.20260716_pace_hr_resolutions"
    )
    migration.upgrade(engine)

    inspector = inspect(engine)
    columns = {
        column["name"] for column in inspector.get_columns("progress_pace_hr_bins")
    }
    assert "bin_step_s_per_km" in columns
    unique_constraints = inspector.get_unique_constraints("progress_pace_hr_bins")
    assert any(
        constraint["column_names"]
        == ["activity_id", "bin_step_s_per_km", "pace_bin_s_per_km"]
        for constraint in unique_constraints
    )
    with engine.connect() as connection:
        count = connection.scalar(text("SELECT COUNT(*) FROM progress_pace_hr_bins"))
        assert count == 0

    # Idempotence: a second startup leaves the new schema intact.
    migration.upgrade(engine)
    assert "bin_step_s_per_km" in {
        column["name"] for column in inspect(engine).get_columns("progress_pace_hr_bins")
    }
