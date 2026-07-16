from __future__ import annotations

import importlib

from sqlalchemy import create_engine, inspect, text

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


def test_race_stop_label_migration_is_additive_and_idempotent() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE race_stops (
                    id VARCHAR(36) PRIMARY KEY,
                    scenario_id VARCHAR(36) NOT NULL,
                    distance_km FLOAT NOT NULL,
                    stop_type VARCHAR(24) NOT NULL,
                    duration_s FLOAT NOT NULL,
                    notes TEXT,
                    sort_order INTEGER NOT NULL,
                    created_at_utc TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO race_stops (
                    id, scenario_id, distance_km, stop_type, duration_s,
                    notes, sort_order, created_at_utc, updated_at_utc
                ) VALUES (
                    'stop', 'scenario', 5.0, 'water', 60.0,
                    NULL, 0, '2026-07-16T00:00:00Z', '2026-07-16T00:00:00Z'
                )
                """
            )
        )

    migration = importlib.import_module("db.migrations.20260716_race_stop_label")
    migration.upgrade(engine)
    migration.upgrade(engine)

    columns = {column["name"] for column in inspect(engine).get_columns("race_stops")}
    assert "label" in columns
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT id, label FROM race_stops WHERE id = 'stop'")
        ).one()
        assert row.id == "stop"
        assert row.label is None
        applied = connection.scalar(
            text("SELECT COUNT(*) FROM schema_migrations WHERE id = :id"),
            {"id": migration.MIGRATION_ID},
        )
        assert applied == 1
